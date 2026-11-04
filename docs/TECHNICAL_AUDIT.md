# Technical audit — 2026-11-03

## Scope and original pipeline

Inspected every tracked source/configuration/documentation file, working-tree diffs,
ignored input directory, installed packages and WAV headers before implementation.
No AGENTS.md, test suite, packaging configuration, trained model, annotated reference
dataset, GUI, separation, phrase model or corpus database existed.

Original graph: `main.py` selects first filename in `data/vocals` →
`audio_processor.load_audio` (librosa mono/resample to 22050) → `extract_pitch`
(pYIN, C2–C7, implicit 2048/512 centered frames) → `midi_conversion`
(delete NaNs, round MIDI, run-length encoding) → `analyzer.extract_features`
(adjacent event intervals, exact triples, durations in frames) → pitch-state
Markov chain → fixed 0.25-second MIDI. Two matplotlib PNG exports are the only UI.

## Evidence and severity

| Priority | Original location | Evidence / consequence | Remediation |
|---|---|---|---|
| Critical | `src/audio_processor.py:midi_conversion` | `valid_f0 = f0[~np.isnan(f0)]` erases rests and joins separated identical notes. No start/end timestamps. | Retain frame lattice; explicit timed events and source mappings. |
| Critical | same | Rounds each frame then splits on every pitch change. Vibrato at semitone boundaries, scoops and spikes become compositional intervals. | Stable-pitch hysteresis, minimum persistence, attack evidence, retain expressive trajectory. |
| High | `extract_pitch` | Discards voiced flags/probability; fixed range, implicit hop/frame/time conventions. No way to inspect uncertainty or estimator identity. | Typed configuration, estimator protocol, raw/processed contours and provenance. |
| High | `main.py:main` | Silently creates sine-wave input when audio is missing. Successful demo can be mistaken for vocal inference. | Explicit demo/benchmark only; missing real input is an actionable error. |
| High | `main.py` / `generator.save_midi` | Duration frames never converted using hop/sample rate; generated duration fixed independently of measured rhythm. | Seconds throughout; MIDI uses actual event times. |
| High | `analyzer.extract_features` | Intervals can cross lost silences; only exact absolute-pitch triples; even singleton triples called motifs. | Phrase-local statistics and minimum non-overlapping repeated evidence. |
| High | `generator.py` | Single-song pitch-state transitions reproduce source transitions; unseeded NumPy/Python RNGs; no resemblance check. | Seeded interval/rhythm constraints, source phrase similarity checks. |
| High | whole repository | No tests, reference annotations, model comparison, version/provenance or cache. Graphs do not establish accuracy. | Synthetic audio benchmark, annotation manifest and explicit measured limitations. |
| Medium | `load_audio` | Mono averaging can cancel antiphase stereo; metadata and original timebase lost. No stem/mix declaration. | Channel policy, native metadata/content hash, explicit resampling. |
| Medium | `visualization.py` | Pitch plot is event index rather than audio time; cannot correct or listen to evidence. | Synchronized waveform/contour/piano roll, correction sidecars. |
| Medium | `requirements.txt` | Five unbounded requirements; heavyweight alternatives absent. System Python and project venv differ. | Bounded core, exact tested lock, isolated optional models. |
| Medium | whole repository | No handling of octave errors, harmonies, separation artifacts or long clips. | Confidence-aware suspect-region flags; bounded overlapping F0 chunks; disclose monophonic limitations. |

Functioning original components: file selection (including recent user changes),
librosa decoding/pYIN, interval arithmetic on supplied events, pitch transition
sampling, pretty_midi writing, PNG rendering. These are real implementations, but
their downstream musical interpretation is undermined by segmentation. There are
no hidden deep-learning, separation, advanced motif or artist-model implementations.

## Initial execution

Project venv: Python 3.14.3, librosa 0.11.0, NumPy 2.4.4, SciPy 1.17.1,
soundfile 0.13.1, pretty_midi 0.2.11, matplotlib 3.10.8. Interpreter emits a
launcher-location warning but imports work. `python -m unittest discover -v`
ran **0 tests**. Torch, TorchCREPE, Basic Pitch, mir_eval and pytest were absent.
Available audio: two 5-second 22050-Hz mono examples and a 33.812-second
44100-Hz stereo user recording. No human labels exist; no real-vocal accuracy
can be asserted. Original sample pipeline is run with outputs in a temporary
directory to preserve existing PNGs/MIDI. See evaluation results for completion.

Existing uncommitted changes to README, main and two data PNGs were identified
before edits. Input audio and existing generated artifacts are preserved.

## Prioritized implementation phases

1. A: retain compatibility functions; add validated schemas, explicit timebases,
   content-keyed caching, tests and non-destructive CLI.
2. B: benchmark legacy segmentation against stable-event transcription; pYIN
   baseline; optional TorchCREPE and singing-note model bridges; never fabricate
   missing weights or imply imported predictions were locally validated inference.
3. C: phrase-local features, motif families, equal-song-weighted corpus reports,
   observed evidence and uncertainty rather than unsupported stylistic claims.
4. D: controllable interval/rhythm search, resemblance filtering, exercises and
   sung-attempt constraint feedback.
5. E: local browser review/correction/playback, exports, pipeline integration and
   documented remaining limitations.

Research/install decisions and primary sources: [MODEL_COMPARISON.md](MODEL_COMPARISON.md).
Final verified results: [EVALUATION.md](EVALUATION.md). Accuracy on corrected real
singing remains a separate validation gate, regardless of synthetic results.

## Execution follow-through (2026-11-04)

The original 33.812-second file completed decoding/F0/segmentation; its first
temporary-directory MIDI export failed because the sandbox denied writes in the
system temporary location. Repeating the five-second sample workflow with outputs
under `.cache/baseline/` succeeded for MIDI and both PNGs. It yielded 216 F0 frames
and 40 rounded-pitch runs in 12.43 seconds. No existing artifact was overwritten.

Implemented stage boundaries now live in `schema.py`, `audio_processor.py`,
`pitch.py`, `transcription.py`, `pipeline.py` and `storage.py`. Confidence/energy
gating and one-frame uncertain-spike repair preserve raw contours. Genuine
sustained octave leaps are not blindly corrected. An upstream TorchCREPE hop
rounding behavior was found in source inspection; the optional adapter instead
uses an explicit native 16-kHz lattice. This timing contract is unit-tested,
not a claim of validated TorchCREPE accuracy.

The feature engine (`features.py`), bounded edit-alignment motif discovery
(`motifs.py`), equal-song aggregation (`corpus.py`) and constrained composer
(`composition.py`) replace the original main workflow. `workspace.py` and `web/`
add a local review/correction interface without introducing a second analysis
implementation. Existing entry points remain compatibility wrappers; the legacy
Markov API remains available but is no longer the application composer.

Phases A–E contain functional changes and tests. Phase B's **real-vocal model
comparison is incomplete** because no independent labels/checkpoints were provided.
Later-stage algorithmic and UI capabilities are delivered with the scope/limits
listed in EVALUATION.md. They do not constitute a validated artist model or proof
of the primary accuracy criterion on real singers.

## Phase 2 follow-through — real-vocal validation, 2026-11-04

Read the prior README, audit, comparison/evaluation reports and relevant pipeline,
editor, storage, model adapters and tests before changes. All original 38 tests
passed again; synthetic scores reproduced as 1.0000 / 0.9306. Prior functionality
was preserved and the generation engine was hash-checked without modification.

| Severity | Evidence / file reference | Phase 2 response |
|---|---|---|
| Critical | `docs/EVALUATION.md` Phase 1 had no real-human reference scores; synthetic full F1 near 1 did not measure singing reliability. | Imported checksum-pinned published Vocadito A1/A2 and continuous F0; frozen singer-disjoint development/heldout comparison. Real heldout full F1 is 0.2470–0.5333 across systems/editions, not near synthetic accuracy. |
| High | `src/storage.py` working corrections lacked independent annotation origin, excerpt convention, review state, uncertainty masks and evaluation splits. | Separate `src/references.py` revision store, explicit attestation, source-sample bounds, review gates, grouped leakage checks, immutable reviewed manifest. Predictions/corrections remain intact. |
| High | `src/note_models.py` GAME MIDI bridge quantized continuous model note centers, conflating import convenience with evaluation data. | Actual official pretrained inference in isolated Python 3.12; float CSV preserves source onsets, offsets and fractional pitches. Unknown correctness confidence remains explicit. |
| High | `src/transcription.py` synthetic success masked missed real short notes/re-attacks and merged transitions. Development pYIN has 204 notes vs A1 300/A2 250. | Recorded event errors and subsets; rejected a 40-ms segmentation candidate whose full F1 worsened for both editions. Defaults preserved rather than overfitting one singer. |
| High | `src/real_metrics.py` downstream sensitivity shows nontrivial interval/motif/phrase/style changes from transcription errors. | Timestamped reference-vs-predicted feature comparisons; artist-style claims remain exploratory and generator unchanged. |
| Medium | GAME development matched-note offsets frequently late (A1 66 >50-ms late versus 16 early; A2 73 late versus 4 early). | Optional bounded unvoiced + fading-energy tail refinement, frozen before heldout scoring. Heldout GAME full F1 0.3120→0.3829 A1 / 0.4537→0.5333 A2, with onsets/pitches/count unchanged. pYIN remains slightly better on A1. |
| Medium | Installed torchcrepe 0.0.24 `convert.bins_to_frequency` adds random triangular ±20-cent dither after Viterbi. | `src/pitch.py` preserves Viterbi bin centers deterministically; version/capacity recorded. Native 16-kHz timing retained. Tiny measured on eight recordings, Full smoke-tested once. |
| Medium | Initial comparison convenience JSON was overwritten by the next experiment; original inference reports survived but initial resource summary was lost. | `src/real_evaluation.py` now archives unique immutable run results and per-job performance; final primary comparison rerun with actual inference forced. Derived models pin the exact parent in the current comparison, with no old-parent/model fallback. |
| Medium | Phase 1 allocation peaks were not whole-process memory; optional adapters had no real inference. | CPU two-thread subprocess comparisons now sample concurrent process-tree RSS including GAME children; exact logs, model failures, versions, hashes and resource scope retained. |
| High | `src/web/app.js` browser fixture exposed displayed pitch edits not always reaching saved state, clip-end rounding beyond source duration, and merge quantization of fractional labels. | Live input synchronization, exact loop bounds and nonquantizing merge; verified saved pitch 64.37, merge 64.183011, split/delete/undo and independent draft saves. Editing/undo clears review attestation. |

The model environment was checked against official upstream documentation/weights,
license restrictions and available hardware before installation. Core Python 3.14 /
NumPy 2 stayed intact; neural inference uses isolated Python 3.12 / NumPy 1.26 / CPU
torch 2.8. No source audio was uploaded. All three primary systems succeeded on
eight public recordings and the private MHS recording; private inference has no
accuracy claim. See [MODEL_SETUP.md](MODEL_SETUP.md) for reproducibility/resources.

Remaining priority order: (1) human/second-review MHS excerpt and lyric-labeled
melismas; (2) new heldout singers/songs for further tuning; (3) voicing/short-event
boundaries and genuine quiet offsets; (4) harmonized, noisy/separated and long audio;
(5) artist-level sensitivity on a genuine multi-song corpus. Neither published
annotation edition is selected to favor a model. Detailed outcomes and limits are
in [REAL_VOCAL_VALIDATION.md](REAL_VOCAL_VALIDATION.md).

## Visual annotation editor audit — 2026-11-04

Inspected `src/web/app.js`, `index.html`, `style.css`, `workspace.py`, `storage.py`
and `references.py` before editing. Existing capabilities were aligned canvas
overlays, audio playback/click-to-seek, table selection/editing, split/merge/delete
buttons, note-only undo and immutable correction/reference saves. There was no
note drag/resize, redo, aligned keyboard, dual audition, review queue or
revision-restore interface. The same state, canvas, media element, source timebase
and persistence APIs are reused; no parallel editor or annotation store was added.

| Severity | Finding | Response / evidence |
|---|---|---|
| High | Table entry was cumbersome; note blocks had no direct manipulation. | Shared pure edit operations, pitch-aligned keyboard/grid, source constraints and pointer commit/cancel. Superseded edit handlers removed. |
| High | Note-only undo omitted region edits and redo. | Atomic notes/regions/selection history; immutable saved-history restore appends an edition and clears reference attestation. |
| High | Reference-mode header exports could return working notes instead of the selected reference. | Explicit saved-reference JSON in reference mode; working MIDI/CSV/report exports remain separate and are browser-tested. |
| High | First A/B prototype showed a reference frequency but a deferred vocal pause stopped its oscillator. | Actual RMS test found silence. Sequence now waits for pause before piano; final tests verify rendered audio rather than UI status alone. |
| Medium | Playback used only the analysis copy and offered no separate piano/original-vocal listening aid. | Hash-checked original streaming, explicit codec fallback, single vocal source, independent bus gains and target reference tones. |
| Medium | Initial alternative-only flags included events outside a short reference excerpt. | Excerpt-scoped suggestions with a dedicated regression; no automatic annotation or confidence promotion. |

Final verification: 66 Python tests, 11 JavaScript core tests and 40 actual browser
checks (20 cases at two viewports). All 64 archived real-vocal event comparisons
reproduce identically. Original private audio/reference, correction histories,
benchmark artifacts and generation/transcription algorithms were checked unchanged.
Measured signals, screenshots, usage and browser/device limits:
[EDITOR_VALIDATION.md](EDITOR_VALIDATION.md), [ANNOTATION_EDITOR.md](ANNOTATION_EDITOR.md).
