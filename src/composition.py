"""Seeded phrase-level constrained search. No source phrase is used as a template."""
from dataclasses import asdict, dataclass, field
import math
import numpy as np
from .motifs import source_similarity
from .schema import NoteEvent, notes_from_dicts

SCALES = {"major": [0, 2, 4, 5, 7, 9, 11], "minor": [0, 2, 3, 5, 7, 8, 10],
          "dorian": [0, 2, 3, 5, 7, 9, 10], "pentatonic": [0, 2, 4, 7, 9]}


@dataclass(frozen=True)
class CompositionConfig:
    tonic: int = 0
    scale: str = "major"
    tempo: float = 100.
    time_signature: tuple[int, int] = (4, 4)
    low: int = 60
    high: int = 76
    bars: int = 4
    density: float = 1.
    contour: str = "arch"
    repetition: float = .3
    section: str = "verse"
    subjective_direction: str = ""
    syllables: int | None = None
    stress_notes: tuple[int, ...] = ()
    chords: list[dict] = field(default_factory=list)
    seed: int = 0
    candidates: int = 3
    similarity_limit: float = .92

    def __post_init__(self):
        if self.scale not in SCALES or not 0 <= self.tonic <= 11:
            raise ValueError("Unknown scale or tonic pitch class")
        if not 0 <= self.low <= self.high <= 127 or self.high-self.low < 4:
            raise ValueError("Choose a MIDI vocal range of at least four semitones")
        if not 20 <= self.tempo <= 300 or not 1 <= self.bars <= 16 or not .25 <= self.density <= 3:
            raise ValueError("Tempo, bars or density outside supported bounds")
        if len(self.time_signature) != 2 or self.time_signature[0] not in range(1, 13) or self.time_signature[1] not in {2, 4, 8, 16}:
            raise ValueError("Invalid time signature")
        if self.contour not in {"arch", "rise", "fall", "late_peak", "level"}:
            raise ValueError("Unknown contour")
        if not 0 <= self.repetition <= 1 or not 1 <= self.candidates <= 8 or not 0 < self.similarity_limit <= 1:
            raise ValueError("Invalid repetition, candidates or similarity threshold")
        if self.syllables is not None and not 4 <= self.syllables <= 96:
            raise ValueError("Syllable count must be 4–96")
        for c in self.chords:
            if not 0 <= c["start_beat"] < c["end_beat"] or not c["pitch_classes"]:
                raise ValueError("Chords need beat spans and pitch_classes")
        if not all(math.isfinite(x) for x in (self.tempo, self.density, self.repetition, self.similarity_limit)):
            raise ValueError("Composition numbers must be finite")


def source_phrases(profile):
    phrases, origins = [], []
    for song in profile.get("song_reports", []):
        groups = {}
        for n in notes_from_dicts(song["notes"]):
            groups.setdefault(n.phrase, []).append(n)
        for ns in groups.values():
            phrases.append(ns)
            origins.append({"song": song["song"], "source_hash": song["source_hash"]})
    return phrases, origins


def generate_candidates(profile, config=CompositionConfig()):
    rng = np.random.default_rng(config.seed)
    scale_pcs = {(config.tonic+i) % 12 for i in SCALES[config.scale]}
    allowed = np.array([p for p in range(config.low, config.high+1) if p % 12 in scale_pcs])
    if len(allowed) < 2:
        raise ValueError("Vocal range contains fewer than two scale pitches")
    weights = {float(k): float(v) for k, v in profile.get("interval_weights", {}).items()}
    if not weights:
        weights = {-3: .05, -2: .2, -1: .1, 0: .2, 1: .1, 2: .3, 3: .05}
    rhythms = profile.get("relative_duration_weights", {}) or {"-1.0": .2, "0.0": .6, "1.0": .2}
    rhythm_values = np.array([2**float(k) for k in rhythms])
    rhythm_probs = np.array(list(rhythms.values()), dtype=float)
    rhythm_probs /= rhythm_probs.sum()
    beats_bar = config.time_signature[0]*4/config.time_signature[1]
    beats = beats_bar*config.bars
    count = config.syllables or max(4, int(round(beats*config.density)))
    phrase_count = min(count, max(1, int(np.ceil(config.bars/2))))
    source, origins = source_phrases(profile)
    accepted, rejected, seen = [], [], set()
    for attempt in range(config.candidates*24):
        notes, beat_cursor, previous = [], 0., int(rng.choice(allowed))
        partition = np.array_split(np.arange(count), phrase_count)
        for phrase, ids in enumerate(partition):
            phrase_beats = beats/phrase_count
            # A half-beat breath closes each phrase; duration sum retains a defined bar grid.
            sounding = phrase_beats-min(.5, phrase_beats*.15)
            ds = np.clip(rng.choice(rhythm_values, len(ids), p=rhythm_probs), .5, 2.)
            ds *= sounding/ds.sum()
            for k, duration in zip(ids, ds):
                pos = k/max(1, count-1)
                shapes = {"arch": math.sin(math.pi*pos), "rise": pos, "fall": 1-pos,
                          "late_peak": math.exp(-((pos-.78)/.23)**2), "level": .5}
                target = config.low+(config.high-config.low)*(.15+.7*shapes[config.contour])
                chord = next((c for c in config.chords if c["start_beat"] <= beat_cursor < c["end_beat"]), None)
                probs = []
                for pitch in allowed:
                    interval = int(pitch)-previous
                    tendency = weights.get(float(interval), .005)
                    tendency *= math.exp(-max(0, abs(interval)-5)*1.1)
                    tendency *= math.exp(-abs(pitch-target)*.18)
                    if interval == 0:
                        tendency *= .2+2*config.repetition
                    if chord and pitch % 12 in chord["pitch_classes"]:
                        tendency *= 2.5 if k in config.stress_notes or beat_cursor % 1 < .15 else 1.5
                    if k in config.stress_notes:
                        tendency *= 1.2 if pitch >= previous else 1.
                    probs.append(tendency)
                probs = np.array(probs); probs /= probs.sum()
                pitch = int(rng.choice(allowed, p=probs))
                start = beat_cursor*60/config.tempo
                end = (beat_cursor+duration)*60/config.tempo
                notes.append(NoteEvent(f"c{attempt}-{k}", start, end, float(pitch), 1., phrase=phrase,
                    flags=["composition_reference"]))
                beat_cursor += duration
                previous = pitch
            beat_cursor = (phrase+1)*phrase_beats
        signature = tuple(n.pitch for n in notes)
        if signature in seen:
            continue
        seen.add(signature)
        similarity = source_similarity(notes, source)
        if similarity["evidence"]:
            similarity["evidence"].update(origins[similarity["evidence"]["source_index"]])
        if similarity["similarity"] >= config.similarity_limit:
            rejected.append(similarity)
            continue
        # Candidate diversity is also transposition invariant.
        if any(source_similarity(notes, [notes_from_dicts(c["notes"])])["similarity"] > .96 for c in accepted):
            continue
        leaps = np.abs(np.diff([n.pitch for n in notes]))
        harmony = []
        for n in notes:
            beat = n.start*config.tempo/60
            c = next((c for c in config.chords if c["start_beat"] <= beat < c["end_beat"]), None)
            if c:
                harmony.append(int(n.pitch) % 12 in c["pitch_classes"])
        accepted.append({"notes": [n.to_dict() for n in notes], "source_similarity": similarity,
            "assessment": {"within_vocal_range": all(config.low <= n.pitch <= config.high for n in notes),
                "within_scale": all(int(n.pitch)%12 in scale_pcs for n in notes),
                "largest_leap_semitones": float(leaps.max(initial=0)),
                "large_leap_count": int(np.sum(leaps > 7)), "breath_gaps": phrase_count-1,
                "shortest_note_seconds": min(n.duration for n in notes),
                "longest_phrase_seconds": max(max(n.end for n in notes if n.phrase==p)-min(n.start for n in notes if n.phrase==p) for p in range(phrase_count)),
                "review_flags": (["very_short_notes_below_100ms"] if min(n.duration for n in notes)<.1 else [])
                    + (["large_leaps_above_7_semitones"] if np.any(leaps>7) else [])
                    + (["phrase_breath_span_above_8_seconds"] if max(max(n.end for n in notes if n.phrase==p)-min(n.start for n in notes if n.phrase==p) for p in range(phrase_count))>8 else []),
                "onset_chord_tone_fraction": float(np.mean(harmony)) if harmony else None,
                "structure": f"{phrase_count} phrases, {config.bars} bars; subjective coherence requires singing"}})
        if len(accepted) == config.candidates:
            break
    return {"config": asdict(config), "candidates": accepted, "rejected_source_matches": len(rejected),
        "source_phrase_count": len(source),
        "warnings": ["Similarity screening does not establish legal originality",
            "Contour and dramatic direction are creative prompts, not inferred emotions",
            "Singability metrics describe constraints; a human must test comfort and musical quality",
            "Repetition controls repeated-pitch probability; this is not a learned phrase generator"]
        + (["No source phrase has six notes; resemblance screening is unavailable"] if not any(len(p)>=6 for p in source) else [])
        + (["Search exhausted before finding all requested distinct candidates"] if len(accepted) < config.candidates else [])}
