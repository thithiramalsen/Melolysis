# Product refocus audit — 2026-11-04

## Intended outcome and current gap

The primary task is **study a singer → understand a melodic decision → construct
an independent idea**. Before this change the opening page was the transcription
editor, the Style page required corpus selection, and Compose started with MIDI
limits/density/seed controls. There was no complete source-to-idea journey.

| Existing evidence | Reuse | Missing product connection |
|---|---|---|
| `src/features.py:analyze_notes` | Note/phrase range, contour, peak positions, intervals, rests, durations, optional beat/chord relationships | Passage selection, plain-language explanations and linked listening examples |
| `src/motifs.py:discover_motifs`, `sequence_distance`, `variation` | Bounded, transposition-invariant rhythm-aware candidate matching | Audible A/B, note highlighting, exact changed-interval display; candidate status must remain explicit |
| `src/corpus.py:profile_artist` | Equal-song aggregation, song counts, exceptions, cross-song candidates | Separate one-song study from multi-song generalization; actionable empty state |
| `src/corpus.py:songwriting_exercises` | Explicit constraints and measurable feedback | Only two corpus-wide exercise templates; no passage-specific technique handoff |
| `src/composition.py:generate_candidates` | Existing optional constrained candidate search and source-similarity checks | Editable canvas, saved user ideas, transformations of the user's own motif and technique feedback |
| `src/web/editor-core.js` | Validated move/resize/draw/delete, fractional pitches, undo/redo | Reuse operations for an independent beat-based composition roll, not reference correction |
| `src/web/editor.js`, `audition.js` | Source-time playback, waveform/F0, keyboard audition, full correction/revision workflows | Primary listening/study view; correction should be secondary and remain intact |
| `src/workspace.py`, `pipeline.py:export_notes` | Local APIs, original audio integrity checks, saved analysis identities, MIDI/CSV export | Versioned technique/idea persistence separate from all reference/model data |
| `src/web/library.js` | Hash-grouped recordings, research separation, unique-song inclusion | Hide model/corpus infrastructure from the default song picker |

The old generated candidates could be edited only as JSON and exported only in
their original state. Song exercises and generated candidates were disconnected;
no technique library existed. These are product gaps, not pitch-model problems.

## Implementation stages

1. Add a source-backed passage study service: immutable study snapshots, evidence
   IDs/timestamps, measured observations and conditional technique exercises. Reuse
   event features and bounded motif discovery; keep uncertainty visible. No model
   replacement or alteration of frozen evaluations.
2. Make Study song the default, with a song picker, passage selector, synchronized
   waveform/roll, focused findings, highlighted examples and phrase A/B. Keep
   Artist patterns, Transcription/research and legacy composer available.
3. Link Try this technique to a blank, independent beat-based idea roll. Reuse
   editing operations, local reference-tone audio, source similarity and MIDI
   export. Transform user-entered motifs rather than copying source pitches.
4. Persist techniques and idea revisions separately; expose range/key/tempo/feel
   controls and optional singing feedback after construction. Give every empty or
   unreliable state an action.
5. Validate source-derived claims with unit tests, actual browser journeys and
   audio routing checks at both supported desktop sizes. Demonstrate MHS read-only;
   save/edit tests use disposable fixtures. Recheck protected scientific artifacts.

## Interpretation boundaries

One recording can support a local observation, not an artist signature. Rest-based
phrases and motif similarity remain candidates. Unreviewed transcription limits
every conclusion; no emotion, lyric syllable, chord progression or accuracy claim
is inferred from the isolated vocal. Creative constraints are suggestions drawn
from observed properties, not quotations of a source melody. Similarity checks
flag resemblance and never establish legal originality.
