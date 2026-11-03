"""Equal-song aggregation with explicit evidence, exceptions and exercise links."""
import numpy as np
from .features import analyze_notes
from .schema import notes_from_dicts
from .motifs import discover_corpus_motifs


def profile_artist(reports, artist="Unspecified", reference_reports=None):
    # One recording contributes once even if analyzed using multiple models.
    unique = {r["audio"]["content_sha256"]: r for r in reports}
    reports = list(unique.values())
    songs = []
    interval_weights, duration_weights, song_groups = {}, {}, {}
    for r in reports:
        ns = notes_from_dicts(r["notes"])
        f = analyze_notes(ns)
        if not ns:
            continue
        song_name = r.get("metadata", {}).get("song") or r["audio"]["content_sha256"]
        song_key = (r.get("metadata", {}).get("artist", artist), song_name)
        row = {"song": song_name,
            "source_hash": r["audio"]["content_sha256"], "source_path": r["audio"]["source_path"],
            "section": r.get("metadata", {}).get("section", "unknown"),
            "report_path": r.get("report_path"), "features": f, "notes": r["notes"],
            "correction_revision": r["provenance"].get("correction_revision")}
        songs.append(row)
        song_groups.setdefault(song_key, []).append(row)
        # Tempo-independent relative duration bins, separately normalized per song.
        ds = np.array(f["duration_seconds"])
        bins, counts = np.unique(np.round(np.log2(ds/np.median(ds))*2)/2, return_counts=True)
        row["relative_durations"] = {str(float(b)): float(c/len(ds)) for b, c in zip(bins, counts)}
    interval_support = 0
    for recordings in song_groups.values():
        valid = [s for s in recordings if s["features"]["interval_distribution"]]
        if valid:
            interval_support += 1
            for s in valid:
                for k, v in s["features"]["interval_distribution"].items():
                    interval_weights[k] = interval_weights.get(k, 0.)+v["proportion"]/len(valid)
        for s in recordings:
            for k, v in s["relative_durations"].items():
                duration_weights[k] = duration_weights.get(k, 0.)+v/len(recordings)
    size = len(song_groups)
    conclusions = []
    for feature, text in (("stepwise_proportion", "Proportion of within-phrase transitions moving 1–2 semitones"),
                          ("repeated_note_proportion", "Proportion of within-phrase repeated pitches")):
        values = [float(np.mean([s["features"][feature] for s in group if s["features"][feature] is not None]))
                  for group in song_groups.values() if any(s["features"][feature] is not None for s in group)]
        if not values:
            continue
        ci = None
        if len(values) >= 3:
            rng = np.random.default_rng(0)
            samples = rng.choice(values, (2000, len(values)), replace=True).mean(axis=1)
            ci = np.percentile(samples, [2.5, 97.5]).tolist()
        conclusions.append({"category": "measured_property", "feature": feature, "description": text,
            "equal_song_mean": float(np.mean(values)), "song_bootstrap_95_interval": ci,
            "support_songs": len(values), "support_recordings": len(songs),
            "support_notes": sum(s["features"]["note_count"] for s in songs if s["features"][feature] is not None),
            "evidence": [{"source_hash": s["source_hash"], "song": s["song"],
                "value": s["features"][feature], "phrases": s["features"]["phrases"][:3]} for s in songs],
            "exceptions": [{"song": s["song"], "value": s["features"][feature]} for s in songs
                if s["features"][feature] is not None and abs(s["features"][feature]-float(np.mean(values))) > .15]})
    sections, paired_sections = {}, []
    for (_, song_name), group in song_groups.items():
        per_section = {}
        for s in group:
            per_section.setdefault(s["section"], []).append(s["features"]["pitch_range"])
        ranges = {section: max(r[1] for r in rs)-min(r[0] for r in rs) for section, rs in per_section.items()}
        for section, span in ranges.items():
            sections.setdefault(section, []).append(span)
        if 'verse' in ranges and 'chorus' in ranges:
            paired_sections.append({'song': song_name, 'chorus_minus_verse_semitones': ranges['chorus']-ranges['verse']})
    result = {"artist": artist, "songs": size, "recordings": len(songs), "phrases": sum(s["features"]["phrase_count"] for s in songs),
        "notes": sum(s["features"]["note_count"] for s in songs), "song_reports": songs,
        "interval_weights": {k: v/interval_support for k, v in interval_weights.items()} if interval_support else {},
        "interval_support_songs": interval_support,
        "relative_duration_weights": {k: v/size for k, v in duration_weights.items()} if size else {},
        "section_ranges": {k: {"song_count": len(v), "mean_range": float(np.mean(v))} for k, v in sections.items()},
        "paired_section_comparisons": paired_sections,
        "conclusions": conclusions,
        "inferences": [{"category": "statistical_inference", "text": "Limited corpus; no artist-specific claim is established",
            "basis": "No population baseline; songs are convenience samples and may not be independent"}],
        "interpretations": [], "motif_families": [{"source_hash": r["audio"]["content_sha256"],
            "motifs": r.get("motifs", {})} for r in reports],
        "cross_song_motifs": discover_corpus_motifs(songs),
        "warnings": ["Song groups use artist and song metadata; give excerpts of the same song identical names",
            "Recordings are averaged within a song before equal-song weighting",
            "Uncorrected transcription errors propagate into every reported tendency",
            "Bootstrap intervals describe this corpus, not an artist population"]}
    if reference_reports:
        reference = profile_artist(reference_reports, "reference")
        result["reference_comparison"] = [{"feature": c["feature"],
            "difference_equal_song_mean": c["equal_song_mean"]-other["equal_song_mean"],
            "target_songs": c["support_songs"], "reference_songs": other["support_songs"]}
            for c in conclusions for other in reference["conclusions"] if c["feature"] == other["feature"]]
    return result


def songwriting_exercises(profile):
    exercises = []
    for c in profile.get("conclusions", []):
        repeated = c["feature"] == "repeated_note_proportion"
        exercises.append({"id": c["feature"], "category": "songwriting_suggestion",
            "title": "Repeat a pitch, change its rhythm and ending" if repeated else "Rise by steps, release downward",
            "observed_feature": c, "why_selected": ("Explore this measured corpus tendency; inspect linked phrase evidence"
                if c['equal_song_mean'] >= .15 else "Contrast exercise: this property is uncommon in this corpus; it is not an established artist tendency"),
            "constraint": {"min_repeated_transitions": 2} if repeated else {"min_stepwise_proportion": .6, "end_below_peak": True},
            "structure": [{"bar": i+1, "role": role, "editable_notes": []}
                for i, role in enumerate(["introduce", "repeat", "vary", "answer and breathe"])],
            "instructions": "Choose a comfortable key. Sing your own four-bar response, record it, then compare the stated constraints.",
            "subjective_interpretation": "You choose the dramatic meaning; the measurements do not establish emotion"})
    return exercises


def assess_attempt(notes, exercise):
    f = analyze_notes(notes)
    constraint = exercise["constraint"]
    checks = {}
    if "min_stepwise_proportion" in constraint:
        observed = f.get("stepwise_proportion")
        checks["stepwise"] = {"observed": observed, "target": constraint["min_stepwise_proportion"],
            "met": observed is not None and observed >= constraint["min_stepwise_proportion"]}
    if "min_repeated_transitions" in constraint:
        count = sum(a.pitch == b.pitch for a, b in zip(notes, notes[1:]) if a.phrase == b.phrase)
        checks["repeated_transitions"] = {"observed": count, "target": constraint["min_repeated_transitions"],
            "met": count >= constraint["min_repeated_transitions"]}
    if constraint.get("end_below_peak"):
        checks["release"] = {"met": bool(notes) and notes[-1].pitch < max(n.pitch for n in notes)}
    return {"checks": checks, "note_count": len(notes),
            "scope": "Constraint feedback only; not an artistic-quality score"}
