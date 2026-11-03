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
