"""Event-based composition features; acoustic expression is reported separately."""
from collections import Counter
from numbers import Real
import numpy as np
from scipy.signal import detrend


def distribution(values):
    counts = Counter(values)
    total = sum(counts.values())
    return {str(float(k)) if isinstance(k, Real) else str(k): {"count": v, "proportion": v/total}
            for k, v in sorted(counts.items())}


def expressive_features(notes, raw):
    results = []
    times = np.array(raw.times)
    f0 = np.array([f or np.nan for f in raw.f0_hz])
    for n in notes:
        a, b = np.searchsorted(times, [n.start+.06, n.end-.06])
        values = f0[a:b]
        if n.duration < .8 or len(values) < 32 or not np.isfinite(values).all():
            continue
        cents = 1200*np.log2(values / (440*2**((n.pitch-69)/12)))
        centered = detrend(cents)
        spec = np.abs(np.fft.rfft(centered*np.hanning(len(centered))))**2
        freq = np.fft.rfftfreq(len(centered), raw.hop_seconds)
        band = (freq >= 4) & (freq <= 9)
        if not band.any():
            continue
        peak = np.flatnonzero(band)[np.argmax(spec[band])]
        concentration = float(spec[band].sum() / max(spec[1:].sum(), 1e-12))
        results.append({"note_id": n.id, "start": n.start, "end": n.end,
            "vibrato_candidate_hz": float(freq[peak]) if concentration > .5 else None,
            "band_power_fraction": concentration,
            "extent_cents_p90_p10": float(np.percentile(centered, 90)-np.percentile(centered, 10)),
            "attack_to_center_cents": float(np.median(cents[:max(1, len(cents)//5)])),
            "ending_minus_center_cents": float(np.median(cents[-max(1, len(cents)//5):])-np.median(cents)),
            "label": "acoustic estimate; not a compositional property"})
    return results


def analyze_notes(notes, raw=None, beat_grid=None, chords=None, tonal_context=None):
    if not notes:
        return {"note_count": 0, "phrase_count": 0, "warnings": ["No reliable note events"]}
    pitches = np.array([n.pitch for n in notes])
    durations = np.array([n.duration for n in notes])
    groups = {}
    for n in notes:
        groups.setdefault(n.phrase, []).append(n)
    intervals, ioi, phrase_reports, recoveries = [], [], [], []
    for phrase_id, ns in groups.items():
        ints = np.diff([n.pitch for n in ns])
        intervals.extend(ints.tolist())
        ioi.extend(np.diff([n.start for n in ns]).tolist())
        for i in range(len(ints)-1):
            if abs(ints[i]) >= 5:
                recoveries.append({"note_id": ns[i+1].id, "leap": float(ints[i]),
                    "following_interval": float(ints[i+1]), "reverses_direction": bool(ints[i]*ints[i+1] < 0)})
        peak = max(ns, key=lambda n: n.pitch)
        span = ns[-1].end-ns[0].start
        phrase_reports.append({"id": phrase_id, "start": ns[0].start, "end": ns[-1].end,
            "note_ids": [n.id for n in ns], "notes": len(ns), "duration": span,
            "range": max(n.pitch for n in ns)-min(n.pitch for n in ns),
            "peak_relative_position": (peak.start-ns[0].start)/span,
            "ending_pitch_relative_to_start": ns[-1].pitch-ns[0].pitch,
            "density_notes_per_second": len(ns)/span,
            "contour": [int(np.sign(x)) for x in ints]})
    rests = [{"start": a.end, "end": b.start, "duration": b.start-a.end}
             for a, b in zip(notes, notes[1:]) if b.start-a.end > 1e-6]
    ints = np.array(intervals)
    result = {"note_count": len(notes), "phrase_count": len(groups),
        "pitch_range": [float(pitches.min()), float(pitches.max())],
        "tessitura_p10_p90": np.percentile(pitches, [10, 90]).tolist(),
        "pitch_distribution": distribution(pitches.tolist()),
        "interval_distribution": distribution(intervals),
        "interval_transition_distribution": distribution([str(tuple(float(v) for v in np.diff([n.pitch for n in ns])[i:i+2]))
            for ns in groups.values() for i in range(max(0, len(ns)-2))]),
        "stepwise_proportion": float(np.mean((abs(ints) > 0) & (abs(ints) <= 2))) if len(ints) else None,
        "repeated_note_proportion": float(np.mean(ints == 0)) if len(ints) else None,
        "duration_seconds": durations.tolist(), "mean_duration_seconds": float(durations.mean()),
        "inter_onset_seconds": ioi, "rests": rests, "phrases": phrase_reports,
        "leap_recovery": recoveries, "expression": expressive_features(notes, raw) if raw else [],
        "review_note_count": sum(bool(n.flags) or n.confidence < .6 for n in notes),
        "warnings": ["Phrase boundaries use rests; manually verify breath/section boundaries",
                     "Tessitura is note-weighted p10–p90, not a physiological range",
                     "Melisma/grace-note labels require lyric or manual annotation"]}
    if beat_grid:
        tempo, origin = float(beat_grid["tempo"]), float(beat_grid.get("origin", 0))
        if not np.isfinite(tempo) or tempo <= 0 or not np.isfinite(origin):
            raise ValueError("Invalid user beat grid")
        positions = np.array([(n.start-origin)*tempo/60 for n in notes])
        result["beat_alignment"] = {"source": "user_supplied", "tempo": tempo, "origin": origin,
            "onsets_beats": positions.tolist(),
            "nearest_eighth_deviation_beats": (positions-np.round(positions*2)/2).tolist()}
    if chords:
        observations = []
        for c in chords:
            if not 0 <= c["start"] < c["end"] or not c["pitch_classes"]:
                raise ValueError("Chord annotations require ordered times and pitch classes")
        for n in notes:
            chord = next((c for c in chords if c["start"] <= n.start < c["end"]), None)
            if chord:
                observations.append({"note_id": n.id, "start": n.start,
                    "chord": chord.get("label", "user supplied"),
                    "onset_is_chord_tone": int(round(n.pitch)) % 12 in chord["pitch_classes"]})
        result["harmony"] = {"source": "user_annotations", "onset_relationships": observations,
            "warning": "Chord-tone membership alone does not identify suspensions, passing tones or emotion"}
        result["harmony"]["phrase_endings"] = []
        for ns in groups.values():
            n = ns[-1]
            c = next((c for c in chords if c["start"] <= n.end-1e-6 < c["end"]), None)
            if c:
                result["harmony"]["phrase_endings"].append({"note_id": n.id,
                    "is_chord_tone_at_offset": int(round(n.pitch)) % 12 in c["pitch_classes"]})
        candidates = []
        for a, b, c in zip(notes, notes[1:], notes[2:]):
            chord = next((h for h in chords if h["start"] <= a.start and c.end <= h["end"]), None)
            if chord and a.phrase == b.phrase == c.phrase:
                member = lambda n: int(round(n.pitch)) % 12 in chord["pitch_classes"]
                if member(a) and not member(b) and member(c) and max(abs(b.pitch-a.pitch), abs(c.pitch-b.pitch)) <= 2:
                    candidates.append({"note_id": b.id, "start": b.start,
                        "category": "musical_interpretation", "label": "neighbour candidate" if a.pitch == c.pitch else "passing-tone candidate",
                        "basis": "stepwise non-chord tone between supplied chord tones; verify meter and spelling"})
        result["harmony"]["interpretation_candidates"] = candidates
    if tonal_context:
        scales = {"major": [0, 2, 4, 5, 7, 9, 11], "minor": [0, 2, 3, 5, 7, 8, 10],
                  "dorian": [0, 2, 3, 5, 7, 9, 10]}
        tonic, mode = tonal_context["tonic_pitch_class"], tonal_context["mode"]
        if not isinstance(tonic, int) or tonic not in range(12) or mode not in scales:
            raise ValueError("Tonal context requires tonic_pitch_class 0–11 and major/minor/dorian mode")
        degrees = {p: i+1 for i, p in enumerate(scales[mode])}
        result["tonality"] = {"source": "user_supplied", "context": tonal_context,
            "scale_degree_distribution": distribution([str(degrees.get((int(round(n.pitch))-tonic)%12, "chromatic")) for n in notes])}
    return result
