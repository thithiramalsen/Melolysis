"""Lazy optional estimators on an explicit source-aligned frame lattice."""
from dataclasses import asdict, replace
from importlib.metadata import version
from typing import Protocol
import numpy as np
from .schema import PitchTrack


class EstimatorUnavailable(RuntimeError):
    pass


class PitchEstimator(Protocol):
    def estimate(self, audio, sr, config) -> PitchTrack: ...


def frame_rms(y, frame, hop, count):
    padded = np.pad(np.square(y.astype(float)), (frame // 2, frame // 2))
    sums = np.r_[0., np.cumsum(padded)]
    starts = np.arange(count) * hop
    ends = np.minimum(starts + frame, len(padded))
    return np.sqrt(np.maximum(0, sums[ends] - sums[starts]) / frame)


class PyinEstimator:
    def estimate(self, audio, sr, config):
        import librosa
        f0, voiced, confidence = librosa.pyin(audio, sr=sr, fmin=config.fmin, fmax=config.fmax,
            frame_length=config.frame_length, hop_length=config.hop_length, center=True, fill_na=np.nan)
        return make_track(audio, sr, f0, voiced, confidence, config, "librosa-pyin/" + version("librosa"))


class TorchCrepeEstimator:
    def estimate(self, audio, sr, config):
        if sr != 16000:
            raise ValueError('TorchCREPE input must be normalized through estimate_chunked at 16 kHz')
        try:
            import torch
            import torchcrepe
        except (ImportError, OSError) as exc:
            raise EstimatorUnavailable("Install optional PyTorch and torchcrepe in a compatible environment") from exc
        if config.fmax > 2006:
            raise ValueError("TorchCREPE requires fmax <= 2006 Hz")
        device = config.device
        if device == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"
        if device.startswith("cuda") and not torch.cuda.is_available():
            raise EstimatorUnavailable("CUDA unavailable; select cpu or auto")
        def deterministic_viterbi(probabilities):
            # Upstream bins_to_frequency adds random +/-20-cent triangular dither.
            # Keep the actual decoded bin centers instead of inventing pitch motion.
            bins,_=torchcrepe.decode.viterbi(probabilities)
            cents=torchcrepe.CENTS_PER_BIN*bins+1997.3794084376191
            return bins,torchcrepe.convert.cents_to_frequency(cents)
        with torch.inference_mode():
            f0, periodicity = torchcrepe.predict(torch.as_tensor(audio, dtype=torch.float32).unsqueeze(0), sr,
                config.hop_length, config.fmin, config.fmax, config.pitch_model_capacity, batch_size=config.pitch_batch_size,
                device=device, return_periodicity=True, pad=True,decoder=deterministic_viterbi)
        f0, c = f0[0].cpu().numpy(), periodicity[0].cpu().numpy()
        return make_track(audio, sr, f0, c >= config.confidence, c, config,
                          'torchcrepe-'+config.pitch_model_capacity+'-viterbi-no-dither/' + version("torchcrepe"))


def make_track(y, sr, f0, voiced, confidence, config, model):
    count = min(len(f0), int(np.ceil(len(y) / config.hop_length)))
    # Energy attacks need a short window; the F0 window would smear repeated syllables.
    energy_frame = max(2, int(sr * .02) // 2 * 2)
    rms = frame_rms(y, energy_frame, config.hop_length, count)
    return PitchTrack((np.arange(count) * config.hop_length / sr).tolist(),
        [float(f) if np.isfinite(f) and f > 0 else None for f in f0[:count]],
        [bool(v) for v in voiced[:count]], np.nan_to_num(np.clip(confidence[:count], 0, 1)).tolist(),
        rms.tolist(), model, config.hop_length / sr,
        timebase={'sample_rate':sr,'hop_length':config.hop_length,'center_offset_samples':0,
                  'model_frame_length':1024 if model.startswith('torchcrepe') else config.frame_length})


ESTIMATORS = {"pyin": PyinEstimator, "torchcrepe": TorchCrepeEstimator}


def estimate_chunked(y, sr, config):
    """Context windows start at integral hops. Each core frame is retained once."""
    if config.estimator == 'torchcrepe':
        # Upstream floors hop*16000/sr when resampling internally, causing drift.
        # Choose one explicit native lattice before chunking instead.
        native_hop = max(1, int(round(config.hop_length*16000/sr)))
        if sr != 16000:
            import librosa
            y = librosa.resample(y, orig_sr=sr, target_sr=16000, res_type='soxr_hq')
        sr = 16000
        config = replace(config, sample_rate=sr, hop_length=native_hop)
    if config.estimator not in ESTIMATORS:
        raise EstimatorUnavailable(f"Unknown estimator {config.estimator}; choose {list(ESTIMATORS)}")
    estimator = ESTIMATORS[config.estimator]()
    total = int(np.ceil(len(y) / config.hop_length))
    if total == 0:
        return PitchTrack([],[],[],[],[],config.estimator+'/empty',config.hop_length/sr,
                          timebase={'sample_rate':sr,'hop_length':config.hop_length})
    core = max(1, int(config.chunk_seconds * sr / config.hop_length))
    context = int(config.context_seconds * sr / config.hop_length)
    out = {key: [] for key in ("times", "f0_hz", "voiced", "confidence", "rms")}
    model = ""
    for first in range(0, total, core):
        last = min(total, first + core)
        left, right = max(0, first - context), min(total, last + context)
        track = estimator.estimate(y[left * config.hop_length:right * config.hop_length], sr, config)
        a, b = first - left, last - left
        out["times"].extend((np.arange(first, last) * config.hop_length / sr).tolist())
        for key in ("f0_hz", "voiced", "confidence", "rms"):
            out[key].extend(getattr(track, key)[a:b])
        model = track.model
    return PitchTrack(**out, model=model, hop_seconds=config.hop_length / sr, timebase=track.timebase)


def postprocess(raw, config):
    """Gate confidence/energy; repair isolated uncertain spikes. Never smooth raw F0."""
    data = asdict(raw)
    f = np.array([v if v is not None else np.nan for v in raw.f0_hz])
    midi = np.full(len(f), np.nan)
    valid = np.isfinite(f)
    midi[valid] = 69 + 12 * np.log2(f[valid] / 440)
    c, rms = np.array(raw.confidence), np.array(raw.rms)
    threshold = max(10 ** (config.silence_db / 20), float(np.max(rms, initial=0)) * 0.01)
    voiced = np.array(raw.voiced, dtype=bool) & valid & (c >= config.confidence) & (rms > threshold)
    spikes, octaves = [], []
    for i in range(1, len(f) - 1):
        if voiced[i-1:i+2].all() and abs(midi[i-1] - midi[i+1]) < .4:
            delta = abs(midi[i] - (midi[i-1] + midi[i+1]) / 2)
            if 11 < delta < 13:
                octaves.append(i)
            if delta > 3 and c[i] < .5:
                f[i] = np.sqrt(f[i-1] * f[i+1])
                spikes.append(i)
    data.update(f0_hz=[float(x) if np.isfinite(x) else None for x in f], voiced=voiced.tolist(),
                flags={"repaired_spikes": spikes, "suspect_octaves": octaves,
                "low_confidence": np.flatnonzero(valid & (c < config.confidence)).tolist()})
    return PitchTrack(**data)
