"""Decoding and compatibility entry points; no automatic source separation."""
from pathlib import Path
import numpy as np
from .schema import AnalysisConfig, AudioMetadata
from .storage import content_hash

SUPPORTED_AUDIO_EXTENSIONS = (".wav", ".mp3", ".flac", ".m4a", ".ogg", ".aac")


def ingest(filepath, config=AnalysisConfig()):
    import librosa
    import soundfile as sf
    path = Path(filepath).resolve()
    if not path.is_file():
        raise FileNotFoundError(path)
    if path.suffix.lower() not in SUPPORTED_AUDIO_EXTENSIONS:
        raise ValueError(f"Unsupported audio extension: {path.suffix}")
    decoder = "soundfile/" + sf.__version__
    try:
        audio, original_sr = sf.read(path, always_2d=True, dtype="float32")
    except (sf.LibsndfileError, RuntimeError):
        try:
            audio, original_sr = librosa.load(str(path), sr=None, mono=False)
            audio = audio[:, None] if audio.ndim == 1 else audio.T
            decoder = "librosa/" + librosa.__version__
        except Exception as exc:
            raise ValueError(f"Cannot decode {path.name}; install FFmpeg for this codec: {exc}") from exc
    if not len(audio) or not np.isfinite(audio).all():
        raise ValueError("Audio is empty or contains non-finite samples")
    channels, samples = audio.shape[1], len(audio)
    if config.channel == "mean":
        y = audio.mean(axis=1)
    else:
        channel = {"left": 0, "right": min(1, channels-1)}.get(config.channel)
        if channel is None:
            channel = int(np.argmax(np.mean(audio.astype(float) ** 2, axis=0)))
        y = audio[:, channel]
    if original_sr != config.sample_rate:
        y = librosa.resample(y, orig_sr=original_sr, target_sr=config.sample_rate, res_type="soxr_hq")
    metadata = AudioMetadata(str(path), content_hash(path), int(original_sr), samples,
        channels, config.sample_rate, len(y), samples / original_sr, decoder,
        config.channel, config.input_kind)
    return y, metadata


def load_audio(filepath, sr=22050):
    """Compatibility API returns mono samples and explicit analysis sample rate."""
    y, metadata = ingest(filepath, AnalysisConfig(sample_rate=sr))
    return y, metadata.sample_rate


def extract_pitch(y, sr):
    from .pitch import estimate_chunked
    track = estimate_chunked(y, sr, AnalysisConfig(sample_rate=sr, hop_length=512))
    return np.array([f if v and f is not None else np.nan for f, v in zip(track.f0_hz, track.voiced)])


def midi_conversion(f0, sr=22050, hop_length=512):
    """Legacy dict API; durations are now seconds and rests retain timestamps."""
    from .schema import PitchTrack
    from .transcription import segment_notes
    count = len(f0)
    valid = np.isfinite(f0) & (np.asarray(f0) > 0)
    track = PitchTrack((np.arange(count) * hop_length / sr).tolist(),
        [float(f) if v else None for f, v in zip(f0, valid)], valid.tolist(),
        valid.astype(float).tolist(), valid.astype(float).tolist(), "external-f0", hop_length/sr)
    return [n.to_dict() for n in segment_notes(track, count * hop_length / sr,
        AnalysisConfig(sample_rate=sr, hop_length=hop_length))]
