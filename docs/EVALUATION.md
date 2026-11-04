# Verified results and remaining limitations

## Phase 2 — real-vocal validation

Completed 2026-11-04: actual pretrained GAME Small and TorchCREPE Tiny inference
on eight Vocadito recordings with two published human editions; four singers
reserved from local development. **61 tests pass** (14.92 s), no failures/skips.
Full results, per-excerpt figures, diagnostics and resource measurements:
[REAL_VOCAL_VALIDATION.md](REAL_VOCAL_VALIDATION.md).

Heldout full note F1 A1/A2: pYIN **0.3875/0.3960**, CREPE Tiny
**0.2470/0.2904**, GAME **0.3120/0.4537**, optional bounded GAME offset refinement
**0.3829/0.5333**. The last improves GAME on heldout but does not beat pYIN against
A1. True melisma/lyric-specific accuracy, GPU behavior, and accuracy on the user's
private recording remain unvalidated. The private 0.5–6.5 s reference draft needs
human listening/correction; no agent-created labels were promoted to truth.

Human reference revisions, excerpt/uncertainty labels, aligned comparison and
formal evaluation gates now exist separately from normal working corrections.
[Protocol](ANNOTATION_PROTOCOL.md), [setup](MODEL_SETUP.md). The results below
are the retained **Phase 1 historical record**, not current neural-model status.

## Phase 1 verification (retained)

Verification completed 2026-11-04 on Windows, Python 3.14.3. Exact packages are in
`requirements-tested.lock.txt`. Only pYIN performed pretrained-free audio inference.
Neural adapter contract tests are **not** pretrained-model accuracy tests.

## Automated and application checks

**38 tests passed; 0 failures, 0 skips** in the final Python suite (16.13 s).
`node --check src/web/app.js`, Python compileall and `git diff --check` passed.

Tests cover rests/source timestamps, sustained vibrato, legato changes, repeated
energy attacks, entry scoops, conservative octave-spike repair, low confidence,
empty contours, invalid events, configuration cache separation, immutable manual
revisions, one-to-one metrics, equal-song weighting including multiple sections,
tonal/chord context, motif evidence, source-copy detection, deterministic constrained
composition and exercise feedback. Real audio inference tests additionally cover
MIDI timing round trips, MP3/FLAC/WAV decoding, native-rate metadata, antiphase stereo,
actual pYIN chunk boundaries and prevention of correction leakage into evaluation.
Composition checks also cover extreme syllable density and sparse phrase layouts;
sub-100-ms notes, leaps above seven semitones and breath spans above eight seconds
receive heuristic review flags, not physiological judgments.
HTTP messages are parsed through the real request handler using an in-memory socket
fixture, including byte ranges, correction saves, CSV exports and cross-origin rejection.
An initial loopback test was denied by the execution sandbox; the test was changed
to exercise HTTP parsing without requiring a network permission.

The isolated in-app browser subsequently reached the locally running server outside
that network sandbox. Verified: loading the real recording, decoded audio readyState
4 and duration 33.812517 s, waveform/contour/note overlays, editable fields and
confidence indications. Using **synthetic fixtures only**, verified note-pitch edit
and correction save, merge (3→2 notes), undo (2→3), delete (3→2), undo, evidence profile,
and three candidate previews. Both tested tabs had zero console errors. The user's
recording annotations were not edited. No microphone permission was requested and
no playback was used to interrupt the user's desktop activity. Microphone capture,
audible reference playback, split-at-playhead interaction and loop playback still
need broader manual/device testing. Their code paths are implemented, not all
visually/audibly validated end to end.

The original 5-second bundled example ran through the old F0/segmentation and
existing MIDI/PNG exports (40 pitch runs). The new pipeline also ran on the real
33.812-second 44.1-kHz stereo `MHS Chorus.wav`: **59 notes, 16 rest-delimited phrases**.
The CLI built its one-song profile and exported **three** melody candidates. These
are successful workflow executions, **not manually verified transcriptions**.
At that Phase 1 checkpoint there were **zero independently annotated real vocal
excerpts**. Phase 2 imports published references independently of Melolysis.

## Reproducible synthetic audio comparison

Saved full machine-readable measurements:
[development.json](benchmarks/development.json), [stress.json](benchmarks/stress.json).
Each contains configurations, model/version/code hashes, audio hashes, per-case
metrics, timings, Python allocation peaks and explicit unavailable-model records.

Both suites contain eight deterministic harmonic audio clips with analytical
continuous F0 and symbolic annotations: vibrato, steps, jumps, repeated attacks,
melisma, slide, rests and noise/leakage. They are idealized oscillators with attack
envelopes, not natural sung voices, formants or realistic separation artifacts.
The development suite informed the scoop fix. The stress suite perturbs registers,
durations, vibrato, slides and noise without subsequent tuning. It is still a
related synthetic suite, **not an independent real-vocal test set**.

The table shows macro-averaged **onset + pitch + offset F1**:

| System | Development (8 cases) | Stress (8 cases) |
|---|---:|---:|
| Original pYIN + original compressed-time segmentation | 0.0000 | 0.0156 |
| Original segmentation on improved raw F0, still deleting rests | 0.0000 | 0.0167 |
| Frame rounding on improved raw F0, **correct source timestamps retained** | 0.6069 | 0.5504 |
| pYIN + stable timed events | **1.0000** | **0.9306** |

The old API did not output onsets/offsets at all. Its baseline rows reconstruct
time from cumulative frame durations starting at zero, exposing the lost-rest
defect. Initial silences make that baseline particularly poor. This is **not**
evidence that original pYIN pitch accuracy was zero. The correctly timed rounding
ablation is the more useful controlled comparison of note fragmentation. The
improved F0 configuration also uses a different hop and restricted range; do not
attribute the entire end-to-end difference to segmentation alone.

Onset + pitch F1 without offsets is 1.0000/0.9306 for improved events and
0.6569/0.6072 for correctly timed frame rounding (development/stress).

| Improved F0 metric, equal-case average | Development | Stress |
|---|---:|---:|
| Voicing precision | 0.9743 | 0.9774 |
| Voicing recall | 0.9994 | 0.9792 |
| Raw pitch accuracy, ≤50 cents, denominator reference voiced frames | 0.9793 | 0.9432 |
| Mean of each case's median absolute cents error on jointly voiced frames | 2.05 cents | 5.52 cents |
| Octave-error fraction on jointly voiced frames (1150–1250 cents) | 0.0000 | 0.0000 |
| Mean per-case onset MAE on onset/pitch matches | 6.04 ms | 12.20 ms |
| Mean per-case offset MAE on onset/pitch matches | 15.18 ms | 15.05 ms |

Note tolerances: onset 50 ms, pitch 50 cents, offset max(50 ms, 20% reference
duration). Matching is one-to-one. mir_eval 0.8.2 independently supplies the full
note precision/recall/F1/overlap fields. Continuous metrics align nearest frames
within half an estimator hop; no interpolation crosses a rest. Timing errors are
conditional on matched notes and do not describe missed events. Octave-error rate
does not capture arbitrary harmonic or multi-octave failures.

## Recorded failure

The stress melisma has six notes approximately **109 ms** long. The default
pipeline produced three events and onset/pitch/offset F1 **0.4444**. All seven
other stress cases scored 1.0000. This exposes the current interaction between the
93-ms pYIN window, boundary persistence and short unstable regions. Lowering
segmentation thresholds may trade missed ornaments for extra notes; no automatic
setting is claimed to solve it. More realistic syllable attacks, noisy unvoiced
gaps and human-corrected melismas are needed before selecting new thresholds.

The original development slide failure produced three notes for a one-note entry
scoop. A plateau-aware entry rule fixed that development case and its perturbed
stress version. This targeted fix must not be presented as independent discovery
of universally reliable slide transcription.

## Performance scope

Final cold pitch-cache runs took 1.39–2.49 seconds per development clip and
1.42–2.67 seconds per stress clip for the measured improved workflow. Maximum
tracemalloc peaks were 29.16/29.00 MiB respectively. These are **Python allocation
peaks**, not whole-process RAM, native-library peaks or GPU memory. Import/JIT warmup,
host load and stage boundaries affect time; these numbers do not rank different
model families. Original baseline timings remain in the JSON. All final improved
benchmark records have pitch_cache_hit=false. Real-file cold runtime observed in
an earlier smoke run was approximately 35 seconds; no long-file throughput claim
is established.

## Delivered functionality and boundaries

| Phase | Functional implementation | Remaining validation / scope |
|---|---|---|
| A | repository audit, source-preserving ingestion, typed contracts, version/code/config provenance, pitch/note caches, compatibility APIs | clean-install verification on other Python/OS combinations |
| B | raw/processed continuous F0, pYIN chunking, confidence/energy gating, stable event boundaries, repeated attack heuristic, scoop handling, octave flags, reference evaluation | GAME/SOME/Basic Pitch/TorchCREPE pretrained inference and real-label comparisons; hard repeated syllables, short ornaments, dense harmonies |
| C | note/phrase composition features, separate expression candidates, supplied grids/chords/tonic, bounded edit-alignment motifs within/across songs, equal-song profiles, section comparisons, bootstrap sample intervals | artist-specific conclusions need a real multi-song corpus and reference population; ornament/lyric alignment, robust harmonic interpretations and meter-aware syncopation |
| D | seeded interval/rhythm constrained search, breath templates, scale/range/chord scoring, source resemblance screening, exercises and attempt constraints | musical quality, nuanced phrasing, stress/lyric realism, learned section-conditioned generation; persisted edited candidate exports |
| E | local browser timeline/player, confidence/alternative overlays, correction revisions, editable tables, JSON/CSV/MIDI, candidate piano rolls and recording code | broader responsive/device QA, microphone, loop/split/audio-reference checks, persistent external-model workers, streaming decoding |

Do not infer chords, emotional meaning, artistic merit or legal originality from
the outputs. Note confidence scores are not calibrated correctness probabilities.
MIDI-imported neural notes lack confidence and quantize float model pitch; raw
continuous F0 remains independent. Phrasing uses rest heuristics, not linguistic
or structural understanding. Expression estimates require long enough reliable
contours and cannot establish compositional intent. Motif search is bounded and
labels coincidences as candidate families; truncation is reported.

## Phase 1 next validation gate (historical)

Create a modest, independently corrected set of isolated real vocals covering the
eight stress categories, multiple recordings, phrase boundaries and uncertain
regions. Agree annotation conventions and split by song. First compare pYIN timed
events with GAME in its compatible isolated environment, then add TorchCREPE or
other estimators if evidence justifies them. Inspect precision/recall failures,
timestamp offsets and artist-corpus conclusions before making stylistic claims.
The primary success criterion remains **unproven on real singers** until that gate
is passed; the application now provides the mechanisms to investigate it.
