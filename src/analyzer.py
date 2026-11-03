"""Compatibility report API backed by the timed musical feature engine."""
from collections import Counter
import numpy as np
from .features import analyze_notes
from .schema import NoteEvent
from .transcription import assign_phrases


def extract_features(notes):
    """Accept event dictionaries; legacy duration-only inputs are interpreted in seconds."""
    if not notes:
        return {}
    events, cursor = [], 0.
    for i, n in enumerate(notes):
        start = float(n.get('start', cursor))
        end = float(n.get('end', start + float(n.get('duration', 0))))
        events.append(NoteEvent(n.get('id', f'compat-{i}'), start, end, float(n['pitch']),
                                float(n.get('confidence', 0)), phrase=int(n.get('phrase', 0))))
        cursor = end
    events = assign_phrases(events)
    features = analyze_notes(events)
    pitches = [n.pitch for n in events]
    intervals = [b.pitch-a.pitch for a,b in zip(events,events[1:]) if a.phrase==b.phrase]
    groups = {}
    for n in events:
        groups.setdefault(n.phrase, []).append(n.pitch)
    triples = Counter(tuple(ps[i:i+3]) for ps in groups.values() for i in range(len(ps)-2))
    return {'average_interval': float(np.mean(np.abs(intervals))) if intervals else 0.,
        'stepwise_percentage': 100*(features['stepwise_proportion'] or 0),
        'repeated_note_percentage': 100*(features['repeated_note_proportion'] or 0),
        'jump_percentage': 100*float(np.mean(np.abs(intervals)>2)) if intervals else 0.,
        'pitch_min': int(min(pitches)), 'pitch_max': int(max(pitches)),
        'pitch_range': int(max(pitches)-min(pitches)),
        'most_common_motifs': [(m,c) for m,c in triples.most_common() if c>=2][:5],
        'average_duration': features['mean_duration_seconds'],
        'raw_intervals': intervals, 'raw_pitches': pitches, 'features': features,
        'duration_unit': 'seconds', 'warning': 'Exact triples are a compatibility summary, not motif-family evidence'}


def print_report(report):
    if not report:
        print('No note events to analyze.')
        return
    print('\nMELODY ANALYSIS REPORT')
    print(f"Pitch range: {report['pitch_min']}–{report['pitch_max']} MIDI ({report['pitch_range']} semitones)")
    print(f"Stepwise (1–2 semitones): {report['stepwise_percentage']:.1f}%")
    print(f"Repeated pitch: {report['repeated_note_percentage']:.1f}%")
    print(f"Leaps (>2 semitones): {report['jump_percentage']:.1f}%")
    print(f"Mean note duration: {report['average_duration']:.3f} seconds")
