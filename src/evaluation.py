"""Objective metrics and a reproducible, explicitly synthetic benchmark."""
from dataclasses import asdict, replace
from pathlib import Path
import json
import time
import tracemalloc
import warnings
import numpy as np
from scipy.optimize import linear_sum_assignment
from .schema import AnalysisConfig, NoteEvent, PitchTrack, notes_from_dicts
from .storage import content_hash, write_json


def match_notes(reference, estimate, onset=.05, pitch_cents=50., offsets=False):
    """Maximum one-to-one matches. Offset tolerance max(50 ms, 20% reference duration)."""
    if not reference or not estimate:
        return []
    valid = np.array([[abs(r.start-e.start) <= onset + 1e-9
        and abs(r.pitch-e.pitch)*100 <= pitch_cents + 1e-9
        and (not offsets or abs(r.end-e.end) <= max(.05, .2*r.duration)+1e-9)
        for e in estimate] for r in reference])
    a, b = linear_sum_assignment(-valid.astype(int))
    return [(int(i), int(j)) for i, j in zip(a, b) if valid[i, j]]


def note_metrics(reference, estimate):
    def score(matches):
        p = len(matches)/len(estimate) if estimate else 0.
        r = len(matches)/len(reference) if reference else 0.
        return {"precision": p, "recall": r, "f1": 2*p*r/(p+r) if p+r else 0., "matches": len(matches)}
    onset_pitch = match_notes(reference, estimate)
    full = match_notes(reference, estimate, offsets=True)
    # Onset-only matching is independent of pitch correctness.
    if reference and estimate:
        valid = np.array([[abs(r.start-e.start) <= .05+1e-9 for e in estimate] for r in reference])
        a, b = linear_sum_assignment(-valid.astype(int))
        onset_only = [(int(i), int(j)) for i, j in zip(a, b) if valid[i, j]]
    else:
        onset_only = []
    out = {"reference_notes": len(reference), "estimated_notes": len(estimate),
        "onset_only": score(onset_only), "onset_pitch": score(onset_pitch), "onset_pitch_offset": score(full),
        "onset_mae_seconds": float(np.mean([abs(reference[i].start-estimate[j].start) for i, j in onset_pitch])) if onset_pitch else None,
        "offset_mae_seconds": float(np.mean([abs(reference[i].end-estimate[j].end) for i, j in onset_pitch])) if onset_pitch else None,
        "tolerances": {"onset_seconds": .05, "pitch_cents": 50, "offset_seconds_min": .05, "offset_ratio": .2}}
    try:
        import mir_eval
        if reference and estimate:
            intervals = lambda ns: np.array([[n.start, n.end] for n in ns])
            pitches = lambda ns: 440*2**((np.array([n.pitch for n in ns])-69)/12)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                m = mir_eval.transcription.precision_recall_f1_overlap(intervals(reference), pitches(reference), intervals(estimate), pitches(estimate))
            out["mir_eval"] = {"version": mir_eval.__version__, "precision": float(m[0]), "recall": float(m[1]), "f1": float(m[2]), "overlap": float(m[3])}
    except ImportError:
        out["mir_eval"] = {"status": "unavailable; install requirements-eval.txt"}
    return out


def frame_metrics(reference, estimate):
    """Nearest frame alignment, never interpolate voiced F0 through rests."""
    t = np.array(reference.times)
    et = np.array(estimate.times)
    if not len(t) or not len(et):
        return {"status": "empty contour"}
    idx = np.searchsorted(et, t).clip(0, len(et)-1)
    left = np.maximum(0, idx-1)
    idx = np.where(abs(et[left]-t) <= abs(et[idx]-t), left, idx)
    in_bounds = abs(et[idx]-t) <= estimate.hop_seconds/2 + 1e-6
    rv = np.array(reference.voiced)
    ev = np.array(estimate.voiced)[idx] & in_bounds
    rf = np.array([v or np.nan for v in reference.f0_hz])
    ef = np.array([v or np.nan for v in estimate.f0_hz])[idx]
    both = rv & ev & np.isfinite(rf) & np.isfinite(ef)
    errors = 1200*np.log2(ef[both]/rf[both])
    voiced_count = int(rv.sum())
    precision = float(np.sum(rv & ev)/ev.sum()) if ev.sum() else 0.
    recall = float(np.sum(rv & ev)/voiced_count) if voiced_count else 0.
    return {"voicing_precision": precision, "voicing_recall": recall,
        "raw_pitch_accuracy_50c": float(np.sum(abs(errors) <= 50)/voiced_count) if voiced_count else None,
        "median_absolute_cents_on_joint_voiced": float(np.median(abs(errors))) if len(errors) else None,
        "mean_absolute_cents_on_joint_voiced": float(np.mean(abs(errors))) if len(errors) else None,
        "octave_error_rate_on_joint_voiced": float(np.mean((abs(errors) > 1150) & (abs(errors) < 1250))) if len(errors) else None,
        "reference_voiced_frames": voiced_count, "joint_voiced_frames": int(both.sum())}


def legacy_segment(f0, hop_seconds):
    """Frozen original algorithm including its compressed timebase (audit baseline)."""
    valid = np.array([f for f in f0 if f is not None and np.isfinite(f) and f > 0])
    if not len(valid):
        return []
    pitches = np.round(69+12*np.log2(valid/440)).astype(int)
    boundaries = np.r_[0, np.flatnonzero(np.diff(pitches))+1, len(pitches)]
    return [NoteEvent(f"legacy-{i}", float(a*hop_seconds), float(b*hop_seconds), float(pitches[a]), 0.)
            for i, (a, b) in enumerate(zip(boundaries, boundaries[1:]))]


def frame_rounding_timed(track, duration):
    """Ablation: original rounding, but retain every frame's correct source time."""
    events, a, pitch = [], None, None
    values = [round(69+12*np.log2(f/440)) if f is not None and v else None
              for f, v in zip(track.f0_hz, track.voiced)]
    for i, value in enumerate(values+[None]):
        if value != pitch:
            if a is not None:
                end = min(duration, track.times[i] if i < len(values) else track.times[-1]+track.hop_seconds)
                if end > track.times[a]:
                    events.append(NoteEvent(f'round-{len(events)}',track.times[a],end,float(pitch),0.))
            a, pitch = (i if value is not None else None), value
    return events


def synthetic_cases():
    # (pitch, seconds, preceding rest). Labels refer to intended stable note centers.
    return {
        "sustain_vibrato": {"sequence": [(69, 1.8, .2)], "vibrato": .65},
        "stepwise": {"sequence": [(p, .4, .0 if i else .2) for i, p in enumerate([60, 62, 64, 65, 64])]},
        "large_jumps": {"sequence": [(p, .5, .1) for p in [60, 72, 55, 67]]},
        "repeated_attacks": {"sequence": [(67, .55, 0 if i else .2) for i in range(4)]},
        "melisma": {"sequence": [(p, .14, 0 if i else .2) for i, p in enumerate([64, 65, 67, 65, 64, 62])]},
        "slide": {"sequence": [(67, 1.5, .2)], "slide": True},
        "rests": {"sequence": [(64, .45, .2), (64, .45, .5), (69, .45, .35)]},
        "noisy_leakage": {"sequence": [(p, .5, .1) for p in [64, 67, 65, 62]], "noise": .025, "leakage": True},
    }


def synthesize(case, sr=22050, seed=0):
    rng = np.random.default_rng(seed)
    y, truth, rows, cursor = [], [], [], 0
    for pitch, seconds, rest in case["sequence"]:
        silence = int(round(rest*sr))
        y.extend(np.zeros(silence)); truth.extend(np.zeros(silence)); cursor += silence
        count = int(round(seconds*sr))
        t = np.arange(count)/sr
        semitones = pitch + case.get("vibrato", .0)*np.sin(2*np.pi*case.get("vibrato_rate", 5.5)*t)
        if case.get("slide"):
            semitones = semitones - case.get('slide_extent', 3)*np.maximum(0, 1-t/case.get('slide_duration', .25))
        f0 = 440*2**((semitones-69)/12)
        phase = 2*np.pi*np.cumsum(f0)/sr
        envelope = np.minimum(1, t/.015)*np.minimum(1, (count/sr-t)/.025)
        signal = .3*envelope*(np.sin(phase)+.25*np.sin(2*phase)+.1*np.sin(3*phase))
        y.extend(signal); truth.extend(f0)
        rows.append(NoteEvent(f"ref-{len(rows)}", cursor/sr, (cursor+count)/sr, float(pitch), 1.))
        cursor += count
    y.extend(np.zeros(int(sr*.2))); truth.extend(np.zeros(int(sr*.2)))
    y, truth = np.array(y), np.array(truth)
    if case.get("noise"):
        y += rng.normal(0, case["noise"], len(y))
    if case.get("leakage"):
        y += .02*np.sin(2*np.pi*130.81*np.arange(len(y))/sr)
    hop = 220
    idx = np.arange(0, len(y), hop)
    fs = truth[idx]
    track = PitchTrack((idx/sr).tolist(), [float(f) if f > 0 else None for f in fs],
        (fs > 0).tolist(), (fs > 0).astype(float).tolist(), np.ones(len(idx)).tolist(), "synthetic-ground-truth", hop/sr)
    return y, rows, track


def stress_cases():
    """Parameter perturbations declared after development, not an independent vocal dataset."""
    cases = {}
    for i, (name, original) in enumerate(synthetic_cases().items()):
        case = dict(original)
        case['sequence'] = [(pitch+(-4 if i%2 else 3), seconds*.78, rest*1.23)
                            for pitch, seconds, rest in original['sequence']]
        if case.get('vibrato'):
            case.update(vibrato=1.05,vibrato_rate=6.3)
        if case.get('slide'):
            case.update(slide_extent=5,slide_duration=.4)
        if case.get('noise'):
            case['noise'] = .08
        cases['stress_'+name] = case
    return cases


def run_benchmark(output_root="outputs/benchmark", estimators=("pyin",), suite="development"):
    """Audio inference, not a precomputed contour demonstration."""
    import librosa
    import soundfile as sf
    from .pipeline import analyze_file
    from .pitch import EstimatorUnavailable
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    records = []
    if suite not in {'development', 'stress'}:
        raise ValueError('Unknown benchmark suite')
    cases = synthetic_cases() if suite == 'development' else stress_cases()
    for name, case in cases.items():
        y, reference, truth = synthesize(case)
        wav = root / "audio" / (name + ".wav")
        wav.parent.mkdir(parents=True, exist_ok=True)
        sf.write(wav, y, 22050, subtype="FLOAT")
        write_json(wav.with_suffix(".reference.json"), {"notes": [n.to_dict() for n in reference], "pitch": asdict(truth)})
        # Original pYIN settings and original segmenter, measured separately.
        start = time.perf_counter()
        tracemalloc.start()
        f0, voiced, confidence = librosa.pyin(y, sr=22050, fmin=librosa.note_to_hz("C2"),
            fmax=librosa.note_to_hz("C7"), frame_length=2048, hop_length=512, center=True)
        legacy_time = time.perf_counter()-start
        _, peak = tracemalloc.get_traced_memory(); tracemalloc.stop()
        legacy = legacy_segment(f0, 512/22050)
        oldtrack = PitchTrack((np.arange(len(f0))*512/22050).tolist(),
            [float(f) if np.isfinite(f) else None for f in f0], voiced.tolist(),
            np.nan_to_num(confidence).tolist(), np.ones(len(f0)).tolist(), "legacy-pyin", 512/22050)
        records.append({"case": name, "system": "original-pyin-and-segmentation", "audio_sha256": content_hash(wav),
            "notes": note_metrics(reference, legacy), "frames": frame_metrics(truth, oldtrack),
            "inference_seconds": legacy_time, "python_tracemalloc_peak_bytes": peak})
        for estimator in estimators:
            try:
                start = time.perf_counter(); tracemalloc.start()
                r = analyze_file(wav, root / estimator, AnalysisConfig(estimator=estimator))
                elapsed = time.perf_counter()-start
                _, peak = tracemalloc.get_traced_memory()
                tracemalloc.stop()
                notes = notes_from_dicts(r["notes"])
                records.append({"case": name, "system": estimator+"-stable-events", "audio_sha256": content_hash(wav),
                    "notes": note_metrics(reference, notes), "frames": frame_metrics(truth, PitchTrack(**r["processed_pitch"])),
                    "inference_seconds": elapsed, "python_tracemalloc_peak_bytes": peak,
                    "runtime": r["runtime"], "provenance": r["provenance"]})
                # Same raw F0 for a controlled segmentation-only comparison.
                raw = PitchTrack(**r["raw_pitch"])
                frozen = legacy_segment([f if v else None for f, v in zip(raw.f0_hz, raw.voiced)], raw.hop_seconds)
                records.append({"case": name, "system": estimator+"-legacy-segmentation-same-contour",
                    "notes": note_metrics(reference, frozen)})
                rounded = frame_rounding_timed(raw, len(y)/22050)
                records.append({"case": name, "system": estimator+"-frame-rounding-correct-timebase",
                    "notes": note_metrics(reference, rounded)})
            except (EstimatorUnavailable, ImportError) as exc:
                tracemalloc.stop()
                records.append({"case": name, "system": estimator, "status": "unavailable", "reason": str(exc)})
    systems = sorted({r["system"] for r in records if "notes" in r})
    summary = {s: {"cases": sum(r["system"] == s for r in records),
        "macro_onset_pitch_f1": float(np.mean([r["notes"]["onset_pitch"]["f1"] for r in records if r["system"] == s])),
        "macro_onset_pitch_offset_f1": float(np.mean([r["notes"]["onset_pitch_offset"]["f1"] for r in records if r["system"] == s]))}
        for s in systems}
    report = {"dataset": f"eight deterministic harmonic synthetic {suite} cases; NOT human vocal validation",
        "seed": 0, "real_annotated_excerpts": 0, "records": records, "summary": summary,
        "memory_scope": "tracemalloc Python allocations; excludes some native/GPU allocations; not process RSS",
        "timing_scope": "first run includes imports/JIT; cache hits are marked; no cross-model speed claim"}
    write_json(root / "results.json", report)
    lines = ["# Measured synthetic benchmark", "", report["dataset"], "",
        "| System | Cases | Onset + pitch F1 | Onset + pitch + offset F1 |", "|---|---:|---:|---:|"]
    lines += [f"| {s} | {v['cases']} | {v['macro_onset_pitch_f1']:.3f} | {v['macro_onset_pitch_offset_f1']:.3f} |" for s, v in summary.items()]
    lines += ["", "No model superiority or real-singing accuracy follows from these synthetic cases.",
              "See results.json for per-case pitch, voicing, timing, cache and memory measurements."]
    (root / "RESULTS.md").write_text("\n".join(lines), encoding="utf-8")
    return report


def evaluate_manifest(path, output_root="outputs/evaluation", estimator="pyin", note_model="heuristic", **model_options):
    """User labels are separate from predictions. No automatic offset optimization."""
    from .pipeline import analyze_file
    manifest_path = Path(path).resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    results = []
    for item in manifest["items"]:
        if not item.get("annotator") or not item.get("convention"):
            raise ValueError("Reference excerpts require annotator and annotation convention")
        audio = manifest_path.parent / item["audio"]
        ref = json.loads((manifest_path.parent / item["reference"]).read_text(encoding="utf-8"))
        report = analyze_file(audio, output_root, AnalysisConfig(estimator=estimator), note_model=note_model, **model_options)
        predicted = notes_from_dicts(report["predicted_notes"])
        result = {"audio": str(audio), "annotator": item["annotator"], "convention": item["convention"],
            "notes": note_metrics(notes_from_dicts(ref["notes"]), predicted), "provenance": report["provenance"]}
        if "pitch" in ref:
            result["frames"] = frame_metrics(PitchTrack(**ref["pitch"]), PitchTrack(**report["processed_pitch"]))
        results.append(result)
    write_json(Path(output_root) / "manifest-results.json", {"items": results})
    return results
