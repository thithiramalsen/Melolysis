"""Optional note-model adapters. External repositories run in isolated interpreters."""
from functools import lru_cache
from pathlib import Path
import subprocess
import tempfile
from typing import Protocol
import numpy as np
from .pitch import EstimatorUnavailable
from .schema import NoteEvent, notes_from_dicts
from .storage import content_hash
from .transcription import assign_phrases


class NoteTranscriber(Protocol):
    def transcribe(self, audio_path, track) -> list[NoteEvent]: ...


def attach_frames(notes, track):
    from dataclasses import replace
    return [replace(n, frame_start=int(np.searchsorted(track.times, n.start)),
                    frame_end=int(np.searchsorted(track.times, n.end))) for n in notes]


def import_midi(path, model="imported", offset_seconds=0.):
    """MIDI confidence is unavailable: zero plus an explicit review flag."""
    import pretty_midi
    midi = pretty_midi.PrettyMIDI(str(path))
    rows = [NoteEvent(f"{model}-{i}", n.start + offset_seconds, n.end + offset_seconds,
                     float(n.pitch), 0., flags=["confidence_unavailable", model]).to_dict()
            for i, n in enumerate(sorted((n for inst in midi.instruments if not inst.is_drum
                                          for n in inst.notes), key=lambda n: n.start))]
    return assign_phrases(notes_from_dicts(rows))


@lru_cache(maxsize=2)
def basic_pitch_model(path):
    from basic_pitch.inference import Model
    return Model(path)


def transcribe_basic_pitch(audio_path, track, config=None, work_root='outputs/work'):
    from .schema import AnalysisConfig
    config = config or AnalysisConfig()
    try:
        from basic_pitch import ICASSP_2022_MODEL_PATH
        from basic_pitch.inference import predict
    except (ImportError, OSError) as exc:
        raise EstimatorUnavailable("Basic Pitch is optional; use its supported isolated Python environment") from exc
    from .audio_processor import ingest
    import soundfile as sf
    y, meta = ingest(audio_path, config)
    Path(work_root).mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=work_root, prefix='basic-pitch-') as tmp:
        wav = Path(tmp)/'input.wav'
        sf.write(wav, y, meta.sample_rate, subtype='FLOAT')
        _, _, events = predict(str(wav), basic_pitch_model(str(ICASSP_2022_MODEL_PATH)),
            onset_threshold=config.model_boundary_threshold, frame_threshold=config.model_presence_threshold,
            minimum_note_length=config.min_note_seconds*1000,
            minimum_frequency=config.fmin, maximum_frequency=config.fmax)
    # The fourth tuple value is amplitude/velocity, NOT correctness confidence.
    rows = [NoteEvent(f"bp-{i}", float(a), float(b), float(p), 0.,
                     flags=["basic_pitch_review", "confidence_unavailable"]).to_dict()
            for i, (a, b, p, c, *_) in enumerate(events)]
    # Never silently choose the highest voice when the model returns polyphony.
    return attach_frames(assign_phrases(notes_from_dicts(rows)), track)


def transcribe_external(kind, audio_path, track, python, repository, weights, work_root, config=None):
    from .schema import AnalysisConfig
    config = config or AnalysisConfig()
    if kind not in {"game", "some"}:
        raise ValueError("External model must be game or some")
    python, repo, weights = Path(python).resolve(), Path(repository).resolve(), Path(weights).resolve()
    if not python.is_file() or not (repo / "infer.py").is_file() or not weights.is_file():
        raise EstimatorUnavailable("Provide an existing model interpreter, repository/infer.py and weights")
    Path(work_root).mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=work_root, prefix=kind + "-") as tmp:
        # Protect the original even if upstream writes beside its input.
        from .audio_processor import ingest
        import soundfile as sf
        y, meta = ingest(audio_path, config)
        wav = Path(tmp).resolve() / "input.wav"
        sf.write(wav, y, meta.sample_rate, subtype="FLOAT")
        launcher = ("import sys,runpy,random; import numpy as np; import torch; "
                    f"random.seed({config.model_seed}); np.random.seed({config.model_seed}); torch.manual_seed({config.model_seed}); "
                    "script=sys.argv[1]; sys.argv=sys.argv[1:]; "
                    "sys.path.insert(0,str(__import__('pathlib').Path(script).parent)); "
                    "runpy.run_path(script,run_name='__main__')")
        args = [str(python), "-c", launcher, str(repo / "infer.py")]
        if kind == "game":
            args += ["extract", str(wav), "-m", str(weights), "--output-formats", "mid",
                     "--output-dir", str(Path(tmp).resolve()),
                     "--seg-threshold", str(config.model_boundary_threshold),
                     "--est-threshold", str(config.model_presence_threshold)]
            if config.model_language:
                args += ["--language", config.model_language]
        else:
            args += ["--model", str(weights), "--wav", str(wav)]
        try:
            result = subprocess.run(args, cwd=repo, capture_output=True, text=True,
                                    timeout=900, check=True)
        except (OSError, subprocess.SubprocessError) as exc:
            detail = getattr(exc, "stderr", "") or str(exc)
            raise EstimatorUnavailable(f"{kind} inference failed: {detail[-3000:]}") from exc
        mids = list(Path(tmp).rglob("*.mid"))
        if len(mids) != 1:
            raise EstimatorUnavailable(f"Expected one MIDI from {kind}; found {len(mids)}. {result.stdout[-1000:]}")
        return attach_frames(import_midi(mids[0], kind), track)


def model_identity(kind, python=None, repository=None, weights=None):
    from importlib.metadata import version, PackageNotFoundError
    if kind in {"game", "some"}:
        if not all((python, repository, weights)):
            raise EstimatorUnavailable("External models require --model-python, --model-repo, --weights")
        repo = Path(repository).resolve()
        try:
            commit = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
        except (OSError, subprocess.SubprocessError):
            commit = "unknown"
        return {"name": kind, "weights_sha256": content_hash(weights), "repo": str(repo),
                "commit": commit, "infer_sha256": content_hash(repo / "infer.py"),
                "sidecars_sha256": {name: content_hash(Path(weights).parent/name)
                    for name in ('config.yaml', 'lang_map.json') if (Path(weights).parent/name).is_file()},
                "python": str(Path(python).resolve())}
    try:
        runtime = version("basic-pitch") if kind == "basic-pitch" else "builtin-v2.1"
    except PackageNotFoundError as exc:
        raise EstimatorUnavailable("Basic Pitch is not installed") from exc
    return {"name": kind, "runtime": runtime}
