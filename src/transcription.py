"""Conservative monophonic event transcription with inspectable frame links."""
from dataclasses import replace
import numpy as np
from scipy.ndimage import median_filter
from .schema import AnalysisConfig, NoteEvent


def assign_phrases(notes, rest_seconds=.35):
    phrase, previous = 0, None
    result = []
    for note in sorted(notes, key=lambda n: n.start):
        if previous is not None and note.start - previous >= rest_seconds:
            phrase += 1
        result.append(replace(note, phrase=phrase))
        previous = note.end
    return result


def segment_notes(track, duration, config=AnalysisConfig()):
    f = np.array([x if x is not None else np.nan for x in track.f0_hz])
    midi = np.full(len(f), np.nan)
    valid = np.array(track.voiced, dtype=bool) & np.isfinite(f) & (np.array(track.confidence) >= config.confidence)
    midi[valid] = 69 + 12 * np.log2(f[valid] / 440)
    hop = track.hop_seconds
    hold = max(1, int(np.ceil(config.transition_seconds / hop)))
    minimum = config.min_note_seconds
    edges = np.diff(np.r_[False, valid, False].astype(int))
    notes = []

    def emit(a, b):
        start = track.times[a]
        end = min(duration, track.times[b] if b < len(f) else track.times[b-1] + hop)
        if end - start < minimum:
            return
        values = midi[a:b]
        values = values[np.isfinite(values)]
        if not len(values):
            return
        flags = []
        confidence = float(np.mean(track.confidence[a:b]))
        if confidence < .6:
            flags.append("review_confidence")
        if float(np.percentile(values, 90) - np.percentile(values, 10)) > 1.5:
            flags.append("slide_or_unstable_pitch")
        if any(a <= i < b for i in track.flags.get("suspect_octaves", [])):
            flags.append("suspect_octave")
        notes.append(NoteEvent(f"n{len(notes):05d}", start, end, float(np.round(np.median(values))),
            confidence, a, b, flags=flags))

    for first, last in zip(np.flatnonzero(edges == 1), np.flatnonzero(edges == -1)):
        smooth = median_filter(midi[first:last], size=max(1, hold // 2 * 2 + 1), mode="nearest")
        rms = np.array(track.rms[first:last])
        a, i = int(first), int(first)
        anchor = float(np.median(smooth[:min(hold, len(smooth))]))
        initial_stable = bool(np.ptp(smooth[:min(hold, len(smooth))]) < .35)
        while i < last:
            local = i - first
            end = min(last, i + hold)
            proposed = smooth[local:end-first]
            change = (len(proposed) == hold and np.all(np.abs(proposed - anchor) >= config.pitch_change_semitones)
                      and np.ptp(proposed) < .35)
            # Repeated attacks require a valley and recovery, not spectral flux alone.
            radius = max(2, int(.09 / hop))
            attack = False
            if i - a >= max(hold, int(.12 / hop)) and local >= radius and local + radius < len(rms):
                left, right = rms[local-radius:local], rms[local+1:local+radius+1]
                attack = (rms[local] < .45 * min(float(left.max()), float(right.max()))
                          and rms[local] <= rms[local-1] and rms[local] < rms[local+1]
                          and abs(smooth[local] - anchor) < config.pitch_change_semitones)
            if (change or attack) and track.times[i] - track.times[a] >= minimum:
                # A moving entry scoop is part of the arriving note until a plateau
                # exists; it is not evidence for an independent short note.
                if change and not initial_stable and a == first:
                    anchor = float(np.median(proposed))
                    initial_stable = True
                    i += hold
                    continue
                emit(a, i)
                a = i
                anchor = float(np.median(proposed))
                initial_stable = True
                i += hold if change else 1
            else:
                i += 1
        emit(a, int(last))
    return assign_phrases(notes, config.phrase_rest_seconds)
