# Melodic relationships: usage and validated scope

Implemented first end-to-end increment, 2026-11-05. Local app: http://127.0.0.1:8781/.

## Use the comparison

1. Open **Artist patterns**. Choose Recording A and Recording B from personal recordings. Model variants are grouped by their source hash; research recordings are excluded.
2. Click **Find related passages**. Select a candidate. An empty result means the bounded search did not establish a sufficiently strong candidate, not that the songs have no relationship.
3. Read the measured transformations and original source timestamps. The rolls show matched, changed and extra targets. Click a correspondence button to highlight its target on each side. Added/omitted targets appear only on their own side.
4. Click **Hear A / Pause** or **Hear B / Pause** to audition the original recording. Click again to pause/resume; Stop resets that passage. Loop repeats it. Space controls the currently active comparison when focus is outside a text field.
5. Toggle normalization. Normalized pitch removes the estimated constant transposition from B, using a shared pitch axis. Normalized horizontal position is percentage of each passage, not source seconds or confirmed beats. Audio always retains original pitch and tempo. Turn normalization off for source-second axes.
6. Click **Learn this pattern**. The existing Create Melody editor opens a blank independent idea with a motif-development exercise. Draw your own motif and answer, vary rhythm/ending, audition, save and export MIDI. The saved link retains both exact source examples and the immutable comparison run.
7. Existing histograms, corpus exercises and profile reports remain in **Advanced statistics and legacy Artist Patterns**. Study Song, its independent seek/selection lanes, and Transcription/Research remain available.

The composition editor's current source listening control uses example A. Both examples remain pinned in the idea's identity evidence; use Artist patterns to hear B. A dedicated saved-idea two-source listening toolbar is future work.

## What the algorithm does

`src/melodic_identity.py` searches rest-delimited note sequences with overlapping 96-target chunks (64-target stride), up to 24 chunks per source. Each pair uses local dynamic programming with explicit target matches, pitch substitutions and unit gap penalties. Eight constant-transposition hypotheses are evaluated. At least four aligned targets and nonuniform interval movement are required. Candidates pass declared strength/pitch-residual gates; overlapping candidate pairs are suppressed.

The traceback records original event IDs and source times. A constant onset-span ratio describes relative tempo; normalized matched-onset residuals and held-duration ratios expose rhythmic changes, including rest differences. Added/omitted targets are **possible ornamentation or transcription errors**, not automatic grace-note/melisma labels. Changed pitches are separated from transposition. Peak placement/range measurements describe broad matched-window structure, not proof of a recurring motif. Low versus unavailable confidence is reported separately.

Existing saved sections annotate the evidence. Saved beat maps are used for event timing observations only with confirmed validity coverage; missing/provisional grids remain unavailable/provisional. The normalized roll is explicitly elapsed-time based, not a beat-aligned warp. No quantization, vocal retuning, model inference or source modification occurs.

Runs are deterministic content-keyed JSON under `outputs/melodic-identity/runs`. Each pins source hashes, analysis IDs, prediction/correction identities, note fingerprints, note snapshots and section/grid revisions. Learning studies and idea links reference those runs. Search computes outside the workspace lock after a short input snapshot.

## Numerical verification

Run:

```powershell
.\.venv\Scripts\python.exe -B tools/evaluate_identity.py
.\.venv\Scripts\python.exe -B -m unittest tests.test_melodic_identity -v
$env:PLAYWRIGHT_BROWSERS_PATH="$PWD\.cache\ms-playwright"
npx playwright test tests/browser/identity.spec.cjs
```

The fixed seed 20261105 symbolic pilot retrieved 40/40 transposed, 40/40 uniformly tempo-scaled and 40/40 single-inserted-target pairs, and returned candidates for 0/40 random negative pairs. A harder pitch-inventory-preserving permutation control returned candidates for 4/40 pairs. These permutations are diagnostic controls, not human-verified unrelated melodies. Runtime for all 200 cases was approximately 0.23 seconds locally. Known-target correspondence precision, recall and F1 were each 1.000 on all three controlled positive categories (320 expected links per category). These checks are **not independent heldout accuracy or perceptual relevance**. Random negatives are easier than many conventional pop gestures. No thresholds were revised after this pilot. Machine-readable cases: `docs/identity/symbolic-validation.json`.

Six new unit tests cover transposition/tempo, inserted targets, changed rests, uniform-pattern exclusion, an unrelated example, embedded motifs, source-version rejection, deterministic output and input immutability. All 102 Python regressions passed with normal Windows temporary-folder access; the sandbox-only run encountered five temporary-directory permission errors. All 11 existing JavaScript edit/audio-contract tests passed.

Final browser result: **112/112 passed** at 1366×768 and 1920×1080 (4.3 minutes). The earlier run passed 111/112 and exposed a collapsed legacy-profile result; explicitly building a profile now opens Advanced, and the final full rerun passed. Browser evidence is archived under `docs/identity/`. The focused journey uses disposable synthetic sources; their cloned symbolic events are UI contracts, not independent inference or human labels. It measures actual vocal-bus RMS while switching original source URLs, pause/resume, note highlighting, blank-idea handoff, and saved idea/reload/MIDI availability at both 1366×768 and 1920×1080.

`tools/capture_identity.cjs` exercises the actual personal recordings at port 8781. It creates new derived comparison/study snapshots, with no source/annotation/context changes. The initial run returned 11 candidates; both vocal sources measured RMS around 0.15–0.16, with no page exceptions. This establishes functioning playback, not musical recognition by a listener. Screenshots are under `outputs/identity-demo/`; all 128 files in the existing protection manifest retained their hashes.

## Remaining plan work

This release delivers pairwise correspondence and composition handoff, not every stage of the larger implementation plan:

- Stable artist/song catalog and human-confirmed work/take identities remain unimplemented. Scope is explicitly **two recordings**; multiple variants cannot be compared as distinct sources. Neither source count nor filename proves distinct songs or common singer identity.
- No corpus-wide motif-family clustering, complete-link grouping, section-conditioned habit inference, rhythm-only candidate retrieval or standalone contour/structural retrieval yet. The current peak/range comparison is descriptive context on a melodic candidate.
- Sections label evidence but do not yet filter search. No changed-ending context expansion, affine gaps, multi-path ambiguity, candidate relevance review history, asynchronous job/cancel UI or calibrated score probabilities. Large searches are bounded and truncation is shown.
- No licensed external motif benchmark or blinded musician relevance review was run. Hard-negative evaluation, independent heldout splits, real-music correspondence F1 and model-edition sensitivity remain required before stronger claims.
- The existing own-motif exercise check still splits the user's note list into halves; explicit motif/answer region marking remains future work. Existing resemblance checks are retained and do not establish legal originality.
- Real transcription errors, missed/repeated targets and phrase boundaries limit every explanation. The two user recordings have no invented artist association, section labels, beat confirmations or human-reviewed motif labels.
- Audio uses the existing browser transport and original source timestamps. Browser seek/loop latency and device audibility/quality remain subject to the previously documented limitations.

Recommended next increment: explicit song/work identity and independent human review of a small set of candidate and hard-negative pairs; then add family grouping and rhythm-only retrieval against frozen evaluation splits.

## Changed components

- `src/melodic_identity.py`: local target alignment, transformation measurements, structural/quality context and source-pinned comparison snapshots.
- `src/workspace.py`: comparison/study endpoints and script registration; expensive matching outside the workspace lock.
- `src/learning_store.py`: preserve multi-source identity evidence on existing idea links.
- `src/web/artist-identity.js`: pair selection, correspondence highlighting, original-source transport, normalization and technique handoff.
- `src/web/app.js`, `index.html`, `learning.css`, `learning-roll.js`: workspace integration, Advanced profile disclosure, source restoration, shared axes and explicit normalized-time labels.
- `tests/test_melodic_identity.py`, `tests/browser/identity.spec.cjs`: algorithm and browser/audio/save regressions.
- `tools/evaluate_identity.py`, `tools/capture_identity.cjs`: reproducible symbolic cases and real-app capture/integrity checks.
- README, this guide and `docs/identity/`: usage and measured verification evidence.
