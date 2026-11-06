"""Reproducible orchestration; predictions and human editions have separate lifecycles."""
from dataclasses import asdict, replace
from importlib.metadata import version, PackageNotFoundError
from pathlib import Path
import csv
import json
import logging
import platform
import time
import numpy as np
from .audio_processor import ingest
from .features import analyze_notes
from .motifs import discover_motifs
from .note_models import attach_frames, import_midi, model_identity, transcribe_basic_pitch, transcribe_external
from .pitch import EstimatorUnavailable, estimate_chunked, postprocess
from .schema import AnalysisConfig, PitchTrack, SCHEMA_VERSION, PIPELINE_VERSION, notes_from_dicts
from .storage import StageCache, content_hash, key_for, latest_correction, write_json
from .transcription import assign_phrases, segment_notes

log = logging.getLogger(__name__)


def analyze_file(path, output_root="outputs", config=AnalysisConfig(), metadata=None,
                 note_model="heuristic", model_python=None, model_repo=None, weights=None,
                 imported_midi=None, timestamp_offset=0., beat_grid=None, chords=None,use_cache=True):
    start = time.perf_counter()
    root = Path(output_root)
    cache = StageCache(root / "cache")
    y, audio = ingest(path, config)
    code_hashes = {p.name: content_hash(p) for p in Path(__file__).parent.glob('*.py')}
    packages = {name: version(name) for name in ("librosa", "numpy", "scipy", "soundfile", "soxr")}
    if config.estimator == "torchcrepe":
        try:
            packages.update({name: version(name) for name in ("torch", "torchcrepe")})
        except PackageNotFoundError as exc:
            raise EstimatorUnavailable("Install optional PyTorch and TorchCREPE to select this estimator") from exc
    pitch_keys = ("estimator", "sample_rate", "hop_length", "frame_length", "fmin", "fmax",
                  "chunk_seconds", "context_seconds", "channel", "device",'pitch_batch_size','pitch_model_capacity')
    identity = {"source": audio.content_sha256, "config": {k: asdict(config)[k] for k in pitch_keys}, "packages": packages,
        'code': {k:code_hashes[k] for k in ('audio_processor.py','pitch.py','schema.py')}}
    pitch_data = cache.get("pitch", identity) if use_cache else None
    pitch_hit = pitch_data is not None
    if pitch_data is None:
        log.info("Estimating %s: %s", config.estimator, path)
        raw = estimate_chunked(y, audio.sample_rate, config)
        pitch_data = asdict(raw)
        cache.put("pitch", identity, pitch_data)
    raw = PitchTrack(**pitch_data)
    processed = postprocess(raw, config)
    if imported_midi:
        model = {"name": "imported-midi", "sha256": content_hash(imported_midi), "declared_model": note_model}
    else:
        model = model_identity(note_model, model_python, model_repo, weights)
    note_identity = {"pitch": identity, "segmentation_config": asdict(config), "model": model, "offset_seconds": timestamp_offset,
        'code': {k:code_hashes[k] for k in ('transcription.py','note_models.py','pipeline.py')}}
    rows = cache.get("notes", note_identity) if use_cache else None
    note_hit = rows is not None
    if rows is None:
        if imported_midi:
            notes = attach_frames(import_midi(imported_midi, str(note_model), timestamp_offset), raw)
        elif note_model == "heuristic":
            notes = segment_notes(processed, audio.duration, config)
        elif note_model == "basic-pitch":
            notes = transcribe_basic_pitch(path, raw, config, root/'work')
        else:
            notes = transcribe_external(note_model, path, raw, model_python, model_repo, weights, root / "work", config)
        if timestamp_offset and not imported_midi:
            notes = attach_frames([replace(n, start=n.start+timestamp_offset, end=n.end+timestamp_offset) for n in notes], raw)
        if any(n.end > audio.duration + .05 for n in notes):
            raise ValueError("Predicted notes exceed the source duration; check timestamp convention/offset")
        rows = [n.to_dict() for n in notes]
        cache.put("notes", note_identity, rows)
    prediction_id = key_for(note_identity)
    correction = latest_correction(root / "corrections", audio.content_sha256)
    active = correction["notes"] if correction else rows
    notes = assign_phrases(attach_frames(notes_from_dicts(active), raw), config.phrase_rest_seconds)
    if any(n.end > audio.duration + .05 for n in notes):
        raise ValueError("Active correction exceeds source duration")
    report = {"schema_version": SCHEMA_VERSION, "pipeline_version": PIPELINE_VERSION,
        "prediction_id": prediction_id, "audio": asdict(audio), "metadata": metadata or {},
        "provenance": {"config": asdict(config), "packages": packages, "python": platform.python_version(), 'code_sha256':code_hashes,
            "note_model": model, "timestamp_convention": "centered F0 frames at sample index k*hop; event spans [start,end)",
            "model_timestamp_offset_seconds": timestamp_offset, "separation": "none",
            "correction_revision": correction["revision"] if correction else None,
            "correction_base_prediction": correction["base_prediction"] if correction else None},
        "context": {"beat_grid": beat_grid, "chords": chords, "tonal_context": (metadata or {}).get("tonal_context")},
        "raw_pitch": pitch_data, "processed_pitch": asdict(processed),
        "predicted_notes": rows, "notes": [n.to_dict() for n in notes],
        "features": analyze_notes(notes, raw, beat_grid, chords, (metadata or {}).get("tonal_context")), "motifs": discover_motifs(notes),
        "warnings": ["Main melody assumes one predominant vocal; harmonies, doubling and leakage require review",
            "Confidence values are estimator scores, not calibrated probabilities of correctness",
            "Heuristic segmentation cannot resolve every repeated syllable or short ornament"],
        "runtime": {"seconds": time.perf_counter()-start, "pitch_cache_hit": pitch_hit, "note_cache_hit": note_hit}}
    if config.input_kind == "mix":
        report["warnings"].append("Input declared as a mix: no source separation or lead-voice selection is performed")
    report['audio_quality'] = {'analysis_peak': float(np.max(abs(y))),
        'analysis_rms': float(np.sqrt(np.mean(y.astype(float)**2))),
        'processed_voiced_frames': sum(processed.voiced), 'frame_count': len(processed.times)}
    if not any(processed.voiced):
        report['warnings'].append('No accepted voiced frames: verify vocal range, recording level and confidence/silence thresholds')
    # Downsample waveform with min/max envelope; source samples are never trimmed.
    block = max(1, int(np.ceil(len(y) / 2400)))
    report["waveform"] = {"hop_seconds": block/audio.sample_rate,
        "min": [float(np.min(y[i:i+block])) for i in range(0, len(y), block)],
        "max": [float(np.max(y[i:i+block])) for i in range(0, len(y), block)]}
    directory = root / "analyses" / audio.content_sha256 / prediction_id
    directory.mkdir(parents=True, exist_ok=True)
    # Immutable model prediction, independent of any existing human revision.
    prediction_provenance = {**report["provenance"], "correction_revision": None, "correction_base_prediction": None}
    if not (directory / "prediction.json").exists():
        write_json(directory / "prediction.json", {"prediction_id": prediction_id, "audio": asdict(audio),
            "provenance": prediction_provenance, "raw_pitch": pitch_data, "notes": rows})
    write_json(directory / "report.json", report)
    export_notes(notes, directory / "notes.csv", directory / "notes.mid")
    # Browser-playable reference preserves time; it is not a synthesized performance.
    import soundfile as sf
    if not (directory / "playback.wav").exists():
        # Playback-only gain prevents float input above full scale from clipping.
        gain = 1/max(1., float(np.max(abs(y))))
        sf.write(directory / "playback.wav", y*gain, audio.sample_rate, subtype="PCM_16")
    report['provenance']['playback_only_gain'] = 1/max(1., float(np.max(abs(y))))
    report["report_path"] = str((directory / "report.json").resolve())
    write_json(directory / "report.json", report)
    return report


def export_notes(notes, csv_path=None, midi_path=None, tempo=120, meter=None):
    if csv_path:
        Path(csv_path).parent.mkdir(parents=True, exist_ok=True)
        with open(csv_path, "w", newline="", encoding="utf-8") as stream:
            fields = ["id", "start", "end", "duration", "pitch", "confidence", "phrase", "frame_start", "frame_end", "flags"]
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(n.to_dict() for n in notes)
    if midi_path:
        import pretty_midi
        midi = pretty_midi.PrettyMIDI(initial_tempo=tempo)
        if meter is not None:
            midi.time_signature_changes.append(pretty_midi.TimeSignature(meter[0],meter[1],0))
        inst = pretty_midi.Instrument(program=0, name="Melody reference")
        inst.notes = [pretty_midi.Note(velocity=85, pitch=int(round(n.pitch)), start=n.start, end=n.end) for n in notes]
        midi.instruments.append(inst)
        Path(midi_path).parent.mkdir(parents=True, exist_ok=True)
        midi.write(str(midi_path))


def load_report(path):
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    notes_from_dicts(value["notes"])
    return value
