# Phase 2 — real singing, measured 2026-11-04

Real pretrained inference now runs for GAME Small and TorchCREPE, alongside pYIN.
The strongest offset-aware system depends on the human annotation edition. The
results do **not** establish production-quality transcription, accuracy on the
user's recording, or a validated artist-style model. Generation code is unchanged.

## Evidence and frozen selection

Used [Vocadito v3](https://zenodo.org/records/5578807), attributed to Bittner, Pasalo,
Bosch, Meseguer Brocal and Rubinstein (2021), DOI 10.5281/zenodo.5578807, CC-BY-4.0.
The import retains published onset/duration/Hz note values and corrected continuous
F0. These are published musician annotations independent of Melolysis, **not human
annotations created by this agent**. A1 and A2 remain separate, including authored
overlaps and fractional tuning. Their segmentation choices differ substantially;
they are useful references, not unquestionable truth. The publisher's annotation
method is described in the [dataset paper](https://arxiv.org/abs/2110.05580).

[Split plan](../evaluation/real/vocadito_split.json): development tracks 1, 2, 4, 5;
heldout tracks 6, 7, 10, 11. Each track has a different singer. The selection and
singer separation were established before scoring. Four development recordings
contain 300 A1 / 250 A2 notes; four heldout contain 192 A1 / 149 A2 notes. Counts
refer to annotation editions of the same audio, not independent extra performances.
This is a small pilot, not a full-dataset benchmark. Pretraining overlap is unknown.
Tony-assisted labeling may favor related F0 methods; no annotation-tool-neutral
claim is made. No new listening judgments or lyric labels were invented.

Machine-readable evidence: [development](real-vocal/development.json),
[heldout](real-vocal/heldout.json), [diagnostics](real-vocal/diagnostics.json),
[all P/R/F1, timing, per-excerpt and resource tables](real-vocal/TABLES.md),
[environment/checksums](real-vocal/environment.json), and
[artifact attribution](real-vocal/artifact-provenance.json).
Original reports/logs and full-span A1/A2 comparison figures remain under
`outputs/real-validation/`; caches, recordings and weights are not in Git.

## Models actually run

| System | Continuous F0 | Note events | Validated inference scope |
|---|---|---|---|
| pYIN baseline | librosa 0.11.0 pYIN | existing stable-event segmenter | all 8 recordings |
| TorchCREPE Tiny events | torchcrepe 0.0.24 Tiny, deterministic Viterbi bin centers | same stable-event segmenter | all 8 recordings |
| GAME Small | separately computed pYIN | official GAME pretrained Small, float CSV | all 8 recordings |
| GAME + tail refinement | unchanged pYIN | GAME events, bounded quiet-tail shortening | same 8 recordings; developed on first 4 only |

GAME code v1.0.3 is pinned to commit
`475a8ee781fe8cca980b3b12fbe6c80c768a813a`, checkpoint release v1.0.0. The
Python 3.12/NumPy 1.26 isolated environment avoids downgrading the core application.
Model seed 0, default upstream boundary/presence thresholds 0.2, no fitted time
shift, CPU two native threads. GAME returns no calibrated correctness confidence.
Its F0 scores below describe **pYIN**, not GAME's internal note-pitch estimator.

Full TorchCREPE also completed a real 33.21-second development preflight, taking
322.05 seconds including initialization; this prompted an explicitly named Tiny
comparison for practical CPU use. That single Full smoke run used upstream dither
before its removal and is not a controlled Full-versus-Tiny ranking. Tiny's native
16-kHz/160-sample grid is explicit. Upstream random ±20-cent triangular conversion
dither is removed from the adapter's bin-to-frequency output; raw expressive F0
remains continuous. Both model assets are hash-recorded.

SOME, Basic Pitch and RMVPE were not run in Phase 2. Their existing contracts or
research do not constitute accuracy evidence. GPU hardware was inventoried but
the CPU torch build was used; no CUDA speed, memory or accuracy result is claimed.
[Installation and commands](MODEL_SETUP.md).

## Accuracy

Macro F1 gives each recording equal weight. Matching is one-to-one with 50-ms
onset tolerance, 50-cent pitch tolerance and offset tolerance max(50 ms, 20% of
reference duration). `mir_eval` 0.8.2 independently checks full event P/R/F1. No
best-edition selection, automatic retuning, offset search or draft scoring.
Published references have no uncertainty masks; complete selected excerpts score.

| System | Development full F1 A1 / A2 | Heldout onset+pitch F1 A1 / A2 | Heldout full F1 A1 / A2 |
|---|---:|---:|---:|
| pYIN baseline | 0.4577 / 0.4056 | 0.5689 / 0.5622 | 0.3875 / 0.3960 |
| TorchCREPE Tiny events | 0.2747 / 0.3338 | 0.4684 / 0.5012 | 0.2470 / 0.2904 |
| GAME Small | 0.3549 / 0.5032 | 0.6423 / 0.8172 | 0.3120 / 0.4537 |
| GAME + tail refinement | 0.4295 / 0.6350 | 0.6423 / 0.8172 | 0.3829 / 0.5333 |

Thus better F0 accuracy alone did not fix note transcription. GAME improves heldout
onset+pitch matching for both editions, but pYIN retains the best full F1 against A1.
Against A2, refined GAME has the best measured full F1. A1–A2 full event F1 itself
ranges from 0.4553 to 0.7317 over these eight tracks. This is measured disagreement,
not an upper bound on model performance. Four test singers are too few for broad
superiority or statistical significance claims; no such claim is made.

Continuous metrics align published source-time F0 to the nearest estimate within
half an estimator hop, without interpolating across unvoiced regions. RPA's
denominator is reference-voiced frames; median cents errors are conditional on
jointly voiced frames. Values below are per-recording macro averages.

| F0 + confidence/energy postprocessing | Split | Voicing precision | Voicing recall | RPA ≤50c | Mean of median absolute cents errors | Any-octave error fraction on joint voiced |
|---|---|---:|---:|---:|---:|---:|
| pYIN | development | 0.9676 | 0.8944 | 0.8692 | 6.30 | 0.0000 |
| CREPE Tiny | development | 0.9003 | 0.9889 | 0.9622 | 8.00 | 0.0076 |
| pYIN | heldout | 0.9447 | 0.8822 | 0.8380 | 8.42 | 0.0000 |
| CREPE Tiny | heldout | 0.8754 | 0.9975 | 0.9837 | 8.11 | 0.0000 |

Zero observed octave errors do not establish immunity on harmonized/noisy vocals.
Full note/onset precision and recall, conditional onset/offset MAE and mean cents
error are retained in the linked tables/JSON rather than hidden by a single F1.

## Changes chosen from development errors

1. Existing pYIN events missed many short notes and merged target transitions.
   A single declared 40-ms minimum/persistence candidate increased predicted
   events from 204 to 234 over the development tracks. Full F1 decreased from
   0.4577→0.4437 (A1) and 0.4056→0.3979 (A2). It was rejected before heldout;
   [failed experiment](real-vocal/rejected-short-events.json) is preserved.
2. GAME matched-note offsets were often late on development. The optional
   `note_refinement.py` requires a trailing **unvoiced AND fading** suffix, at least
   60 ms voiced core, trim bounded 30–250 ms and tail median RMS below half the
   voiced core. It only shortens offsets; no pitch/onset/count change or merging.
   It retains parent predictions and every changed boundary's acoustic evidence.
   It is an evidence-supported heuristic, not a universally valid vocal offset rule.
3. The [freeze record](../evaluation/real/heldout_freeze.json) predates heldout
   scoring. Refinement improved full F1 by 0.0709 A1 / 0.0796 A2 on heldout, relative
   to GAME alone, without further tuning. Onset+pitch F1 stayed identical.
   Heldout conditional offset MAE fell 96.3→82.3 ms (A1), 73.5→62.2 ms (A2).
   Per-track A1 track 7 was unchanged; no claim that every excerpt improved.

The default pYIN segmentation and generator were left unchanged. Use
`refine-notes report.json` to create a separately reviewable optional edition.
Quiet genuine tails can be mistaken for silence; energetic voicing dropouts are
explicitly skipped. Vibrato/bends remain in the untouched expressive contour.

## Error evidence and downstream effects

Every record includes timestamped missed/unmatched events and overlap-based
fragmentation/merger candidates. These are metric diagnostics, not new human error
labels. [Per-excerpt tables and figures](real-vocal/TABLES.md) retain all eight
recordings; checked-in comparison figures use the same first 12 seconds for each
system with A2. Full-span figures for both editions remain in local outputs.
Bars in static figures have a small labeled vertical display separation; scoring
always uses the original pitches.

Examples of remaining failures:

- Development track 5: CREPE Tiny full F1 0.0774 A1 / 0.1832 A2; 70 A1 events are
  unmatched and 29 merger candidates occur despite high frame-level accuracy.
- Heldout track 6: pYIN misses 36 A1 events; GAME misses 42. Against A2 GAME's
  offset-aware F1 is 0.4000, improved to 0.4800 by refinement. This recording also
  has pronounced reference disagreement (A1 vs A2 full F1 0.4553).
- Heldout track 10: pYIN full F1 0.3448 A1 / 0.2400 A2; refined GAME 0.4194 / 0.6296.
  Strong aggregate improvements still leave many individual notes wrong.

Repeated-pitch subsets are defined as adjacent reference centers within 50 cents,
with gaps ≤500 ms, and include the surrounding note windows. Heldout macro
onset+pitch F1 is 0.5955 / 0.5178 (pYIN A1/A2), 0.4686 / 0.4598 (Tiny), and
0.7064 / 0.8051 (GAME, unchanged by refinement). These are operational subsets,
not independently labeled re-attack ground truth. Short-note (≤180-ms) recall on
heldout is 0.3741 / 0.4590 for pYIN, 0.2803 / 0.3403 for Tiny, and 0.4205 / 0.8493
for GAME. **True melisma accuracy is unavailable** because the dataset has no
time-aligned syllable/melisma regions. The editor supports human labels for that
future evaluation. Short events must not be relabeled melismas to fill the gap.

Feature sensitivity uses identical phrase-rest rules and nearest-semitone bins
on both prediction and reference; event accuracy itself retains fractional pitch.
Heldout mean interval-distribution total variation (0=identical, 1=disjoint):

| System | A1 | A2 |
|---|---:|---:|
| pYIN | 0.1992 | 0.2168 |
| CREPE Tiny | 0.2251 | 0.1803 |
| GAME / refined GAME | 0.2202 | 0.1506 |

Against A2, pYIN underestimates repeated-note proportion by 9.67 percentage points
and overestimates stepwise proportion by 7.56 points on average; GAME deviations
are −1.16 and −0.48 points. Phrase counts differ too: on track 10 the same rest
heuristic yields 1 reference phrase, 3 pYIN phrases, 1 GAME phrase. Reference motifs
exist on tracks 6, 10 and 11 where pYIN discovers no family; GAME also changes
candidate motif intervals, rather than faithfully reproducing all families.
Duration-only refinement can change rhythm-sensitive motif grouping even when
pitch/onset sequences stay fixed. Full contours, phrase lengths and timestamped
motif families are retained in result JSON. These are sensitivity checks, not
motif precision/recall or an independent phrase-boundary benchmark.

Do not treat predicted artist-style summaries as established habits until note
editions have been reviewed. This pilot contains one excerpt per singer and
cannot validate multi-song artist specificity. No downstream feature or melody
generation algorithm was changed to make those summaries look better.

## Resources, application checks and remaining work

All three primary models ran successfully on all eight sources; no fallback was
used. Heldout mean cold worker wall time: pYIN 9.51 s, Tiny 7.49 s, GAME 20.75 s.
Refinement adds 1.40 s excluding parent inference. Peak sampled concurrent
process-tree RSS was 279.5 / 409.6 / 804.6 MiB respectively. Sampling every 50 ms
includes external child processes, startup/imports/exports and OS caching effects;
it is not exclusive memory or GPU usage. Host load affects comparisons. Hardware
inventory and exact packages are linked above. Long recordings/streaming and
GPU inference remain unvalidated.

**61 tests passed**, no failures/skips in the final Phase 2 suite at this checkpoint
(14.92 s). Added regression coverage includes reference provenance/revisions,
attestation/draft gates, split leakage, source integrity, uncertain/unmasked
coverage, F0-truth absence, human melisma gates, float GAME CSV, bounded refinement,
HTTP review endpoints and explicit model failures. Model contract stubs are not
the source of the accuracy measurements above. The original 38-test suite and
synthetic development/stress scores 1.0000 / 0.9306 were reproduced separately.

Hidden isolated-browser checks verified the private draft's 11 editable events,
unchecked attestation, source window, published read-only edition, aligned
reference/raw predictions and saved-reference score display. No user reference
was marked reviewed, no playback disturbed the desktop, and no microphone was
requested. Playback/loop/microphone device behavior still needs a human check.
An isolated synthetic browser fixture additionally verified fractional pitch
persistence (64.37), fractional merge (64.183011), paused-playhead split (2→3),
undo, delete/undo, saved uncertain regions and unassigned→development assignment.
All fixture references remain drafts, outside the main workspace. Checks exposed
and fixed clip-end rounding beyond source bounds, stale edits on save, unwanted
merge quantization and review state after undo. The fixture remained paused and
was not promoted to a human reference.

For **MHS Chorus.wav**, review the prepared **0.500–6.500-second, 11-event draft**:
select the recording in the workspace, load **Pending human annotator**, follow
[ANNOTATION_PROTOCOL.md](ANNOTATION_PROTOCOL.md), correct pitches/boundaries and
uncertainty, then attest and save under your name. Its original 59-note pYIN
prediction remains unvalidated; alternative neural analyses are review aids.
Actual MHS inference produced 59 pYIN notes / 16 phrases, 91 Tiny notes / 1 phrase,
and 85 GAME notes / 12 phrases; the refiner changed 13 GAME offsets. These counts
demonstrate substantial disagreement, not which transcription is correct. In
particular, Tiny's single inferred phrase needs careful rest/voicing review.
Actual human review cannot be completed by generating or trusting predictions.

Next useful work: independent second review of that excerpt; several additional
songs/singers with predefined repeated-attack and lyric-labeled melisma passages;
a fresh heldout split for future tuning; confidence/voicing-aware event segmentation
for CREPE; model-specific offset/quiet-tail review and noisy/harmonized vocals.
