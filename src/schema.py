"""Validated contracts. Event times are seconds on the original source timeline."""
from dataclasses import asdict, dataclass, field
from math import isfinite

SCHEMA_VERSION = 1
PIPELINE_VERSION = "2.0.0"


@dataclass(frozen=True)
class AnalysisConfig:
    estimator: str = "pyin"
    sample_rate: int = 22050
    hop_length: int = 220
    frame_length: int = 2048
    fmin: float = 65.406
    fmax: float = 1046.503
    confidence: float = 0.15
    min_note_seconds: float = 0.06
    transition_seconds: float = 0.08
    pitch_change_semitones: float = 0.75
    phrase_rest_seconds: float = 0.35
    silence_db: float = -55.0
    chunk_seconds: float = 20.0
    context_seconds: float = 1.0
    channel: str = "loudest"
    input_kind: str = "isolated_vocal"
    device: str = "auto"
    model_seed: int = 0
    model_language: str = ""
    model_boundary_threshold: float = .2
    model_presence_threshold: float = .2

    def __post_init__(self):
        if not all(isfinite(v) for v in asdict(self).values() if isinstance(v, (int, float))):
            raise ValueError("Configuration numbers must be finite")
        if any(not isinstance(v, int) or isinstance(v, bool) for v in
               (self.sample_rate, self.hop_length, self.frame_length, self.model_seed)):
            raise ValueError("Sample rate, hop, frame and seed must be integers")
        if not 0 < self.fmin < self.fmax < self.sample_rate / 2:
            raise ValueError("Require 0 < fmin < fmax < Nyquist")
        if self.sample_rate < 8000 or self.hop_length < 1 or self.frame_length < 32:
            raise ValueError("Invalid sample rate, hop or frame length")
        if self.frame_length < 2 * self.sample_rate / self.fmin:
            raise ValueError("Frame must contain at least two periods at fmin")
        if not 0 <= self.confidence <= 1:
            raise ValueError("Confidence must be in [0, 1]")
        if not 0 <= self.model_boundary_threshold < 1 or not 0 <= self.model_presence_threshold < 1:
            raise ValueError("Model thresholds must be in [0, 1)")
        if min(self.min_note_seconds, self.transition_seconds, self.pitch_change_semitones,
               self.phrase_rest_seconds, self.context_seconds) <= 0:
            raise ValueError("Durations and sensitivity must be positive")
        if self.chunk_seconds <= 2 * self.context_seconds:
            raise ValueError("Chunk must exceed twice its context")
        if self.channel not in {"loudest", "mean", "left", "right"}:
            raise ValueError("Unknown channel policy")
        if self.input_kind not in {"isolated_vocal", "mix"}:
            raise ValueError("Unknown input kind")


@dataclass(frozen=True)
class AudioMetadata:
    source_path: str
    content_sha256: str
    original_sample_rate: int
    original_samples: int
    channels: int
    sample_rate: int
    samples: int
    duration: float
    decoder: str
    channel_policy: str
    input_kind: str


@dataclass
class PitchTrack:
    times: list[float]
    f0_hz: list[float | None]
    voiced: list[bool]
    confidence: list[float]
    rms: list[float]
    model: str
    hop_seconds: float
    flags: dict[str, list[int]] = field(default_factory=dict)
    timebase: dict = field(default_factory=dict)

    def __post_init__(self):
        n = len(self.times)
        if any(len(a) != n for a in (self.f0_hz, self.voiced, self.confidence, self.rms)):
            raise ValueError("Pitch frame lengths differ")
        if self.hop_seconds <= 0 or not isfinite(self.hop_seconds):
            raise ValueError("Invalid hop time")
        if any(not isfinite(t) or t < 0 for t in self.times):
            raise ValueError("Invalid timestamps")
        if any(b <= a for a, b in zip(self.times, self.times[1:])):
            raise ValueError("Pitch times must increase")
        if any(f is not None and (not isfinite(f) or f <= 0) for f in self.f0_hz):
            raise ValueError("F0 must be positive or null")
        if any(not isfinite(c) or not 0 <= c <= 1 for c in self.confidence):
            raise ValueError("Invalid confidence")
        if any(not isfinite(r) or r < 0 for r in self.rms):
            raise ValueError("Invalid RMS")


@dataclass(frozen=True)
class NoteEvent:
    id: str
    start: float
    end: float
    pitch: float
    confidence: float
    frame_start: int = 0
    frame_end: int = 0
    phrase: int = 0
    flags: list[str] = field(default_factory=list)

    def __post_init__(self):
        if not all(isfinite(x) for x in (self.start, self.end, self.pitch, self.confidence)):
            raise ValueError("Note numbers must be finite")
        if not 0 <= self.start < self.end or not 0 <= self.pitch <= 127:
            raise ValueError("Invalid note time or MIDI pitch")
        if not 0 <= self.confidence <= 1 or not 0 <= self.frame_start <= self.frame_end:
            raise ValueError("Invalid confidence or frame span")

    @property
    def duration(self):
        return self.end - self.start

    def to_dict(self):
        return {**asdict(self), "duration": self.duration}


def notes_from_dicts(rows):
    fields = NoteEvent.__dataclass_fields__
    notes = [NoteEvent(**{k: v for k, v in row.items() if k in fields}) for row in rows]
    notes.sort(key=lambda n: (n.start, n.end))
    if len({n.id for n in notes}) != len(notes):
        raise ValueError("Note IDs must be unique")
    if any(b.start < a.end - 1e-6 for a, b in zip(notes, notes[1:])):
        raise ValueError("Main melody notes must not overlap; review polyphonic predictions")
    return notes
