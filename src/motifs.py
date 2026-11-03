"""Bounded transposition-invariant, rhythm-aware phrase/window matching."""
import numpy as np


def representation(notes):
    if len(notes) < 2:
        return np.empty((0, 2))
    pitches = np.array([n.pitch for n in notes])
    durations = np.array([n.duration for n in notes])
    return np.column_stack((np.diff(pitches), np.log2(durations[1:] / durations[:-1])))


def sequence_distance(a, b):
    """Normalized edit alignment with interval and duration-ratio substitution costs."""
    if not len(a) or not len(b):
        return 0. if not len(a) and not len(b) else 1.
    table = np.zeros((len(a)+1, len(b)+1))
    table[:, 0], table[0, :] = np.arange(len(a)+1), np.arange(len(b)+1)
    for i, x in enumerate(a, 1):
        for j, y in enumerate(b, 1):
            cost = .75 * min(1., abs(x[0]-y[0])/4) + .25 * min(1., abs(x[1]-y[1]))
            table[i, j] = min(table[i-1, j]+1, table[i, j-1]+1, table[i-1, j-1]+cost)
    return float(table[-1, -1] / max(len(a), len(b)))


def variation(a, b):
    if len(a) < len(b):
        return "expansion"
    if len(a) > len(b):
        return "contraction"
    x, y = representation(a), representation(b)
    pitch_same = np.allclose(x[:, 0], y[:, 0], atol=.1)
    rhythm_same = np.allclose(x[:, 1], y[:, 1], atol=.15)
    if pitch_same and rhythm_same:
        return "exact_repetition" if abs(a[0].pitch-b[0].pitch) < .1 else "transposed_repetition"
    if pitch_same:
        return "rhythmic_variation"
    if len(x) > 1 and np.allclose(x[:-1, 0], y[:-1, 0], atol=.1):
        return "changed_ending"
    return "melodic_variation"


def discover_motifs(notes, max_windows=180, threshold=.16):
    phrases = {}
    for n in notes:
        phrases.setdefault(n.phrase, []).append(n)
    windows = []
    for phrase in phrases.values():
        if len(phrase) >= 4:
            windows.append(phrase)
        for length in (4, 6, 8):
            for i in range(0, len(phrase)-length+1, 2):
                windows.append(phrase[i:i+length])
    # Deduplicate windows; bounded work is exposed in the report.
    windows = list({tuple(n.id for n in w): w for w in windows}.values())
    total = len(windows)
    windows = windows[:max_windows]
    reps = [representation(w) for w in windows]
    used, families = set(), []
    for i, a in enumerate(windows):
        if i in used or len(a) < 4:
            continue
        # Uniform repeated tones and a single repeated interval are weak signatures.
        # Keep rhythmically informative repeated tones; label all results candidates.
        if len(np.unique(reps[i][:, 0])) < 2 and np.ptp(reps[i][:, 1]) < .5:
            continue
        occurrences = [{"start": a[0].start, "end": a[-1].end,
                        "note_ids": [n.id for n in a], "variation": "reference", "distance": 0.}]
        for j in range(i+1, len(windows)):
            b = windows[j]
            if j in used or abs(len(a)-len(b)) > 2:
                continue
            if any(b[0].start < o["end"] and b[-1].end > o["start"] for o in occurrences):
                continue
            distance = sequence_distance(reps[i], reps[j])
            if distance <= threshold:
                occurrences.append({"start": b[0].start, "end": b[-1].end,
                    "note_ids": [n.id for n in b], "variation": variation(a, b), "distance": distance})
                used.add(j)
        if len(occurrences) >= 2:
            used.add(i)
            families.append({"intervals": reps[i][:, 0].tolist(), "occurrences": occurrences,
                             "interpretation": "candidate recurrence; human review required"})
    return {"families": sorted(families, key=lambda f: -len(f["occurrences"]))[:20],
            "windows_considered": len(windows), "windows_available": total,
            "truncated": total > max_windows, "distance_threshold": threshold}


def source_similarity(candidate, source_phrases, minimum=6):
    """Maximum rhythm-aware window resemblance; not proof of legal originality."""
    maximum, evidence, comparisons = 0., None, 0
    for source_index, source in enumerate(source_phrases):
        for length in range(minimum, min(12, len(source), len(candidate))+1):
            a = np.array([representation(candidate[i:i+length]) for i in range(len(candidate)-length+1)])
            b = np.array([representation(source[j:j+length]) for j in range(len(source)-length+1)])
            comparisons += len(a)*len(b)
            d = np.mean(.75*np.minimum(1, np.abs(a[:, None, :, 0]-b[None, :, :, 0])/4)
                        + .25*np.minimum(1, np.abs(a[:, None, :, 1]-b[None, :, :, 1])), axis=2)
            i, j = np.unravel_index(np.argmin(d), d.shape)
            score = 1-float(d[i, j])
            if score > maximum:
                maximum, evidence = score, {"source_index": source_index, "source_start": source[j].start,
                    "source_end": source[j+length-1].end, "matched_notes": length}
    return {"similarity": maximum, "evidence": evidence, "minimum_notes": minimum,
            "window_pairs_compared": comparisons, "status": "assessed" if comparisons else "insufficient_source_or_candidate_notes"}


def discover_corpus_motifs(song_reports, limit=100, threshold=.16):
    """Whole-phrase candidates across distinct songs, separate from within-song windows."""
    from .schema import notes_from_dicts
    items = []
    for song in song_reports:
        groups = {}
        for note in notes_from_dicts(song['notes']):
            groups.setdefault(note.phrase, []).append(note)
        for phrase in groups.values():
            if not 4 <= len(phrase) <= 32:
                continue
            rep = representation(phrase)
            if len(np.unique(rep[:, 0])) < 2 and np.ptp(rep[:, 1]) < .5:
                continue
            items.append((song, phrase, rep))
    total = len(items); items = items[:limit]
    def occurrence(song, phrase, transform, distance):
        return {'song': song['song'], 'source_hash': song['source_hash'],
            'start': phrase[0].start, 'end': phrase[-1].end,
            'note_ids': [n.id for n in phrase], 'variation': transform, 'distance': distance}
    families, used = [], set()
    for i, (song, phrase, rep) in enumerate(items):
        if i in used:
            continue
        matches = [occurrence(song,phrase,'reference',0.)]
        for j in range(i+1,len(items)):
            other, p, r = items[j]
            if j in used or song['song'] == other['song'] or abs(len(phrase)-len(p)) > 2:
                continue
            distance = sequence_distance(rep,r)
            if distance <= threshold:
                matches.append(occurrence(other,p,variation(phrase,p),distance)); used.add(j)
        if len(matches)>1:
            families.append({'intervals':rep[:,0].tolist(),'occurrences':matches,
                'support_songs':len({m['song'] for m in matches}),
                'label':'candidate cross-song recurrence; not evidence of artist specificity'})
    return {'families': families, 'phrases_considered':len(items),'phrases_available':total,
            'truncated':total>limit,'threshold':threshold}
