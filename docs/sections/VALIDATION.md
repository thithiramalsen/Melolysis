# Section reliability regression gate

The machine-readable [summary](validation.json) records final counts, and [per-test results](browser-test-results.json) record browser case titles, viewport, status and duration. [Audio measurements](audio-checks.json) decode the JSON attachments from the browser suite. These are new UX-validation artifacts, separate from frozen MIR evaluations.

## Reproduce

From the repository root, with the virtual environment and the existing bundled Chromium available:

```powershell
.venv\Scripts\python.exe -B -m unittest discover -s tests -v
npm run test:editor
node tools/run_browser_tests.cjs
node tools/run_browser_tests.cjs --config playwright.navigation.config.cjs --grep 232
node tools/capture_section_fix.cjs
```

The default browser configuration owns port 8772 and creates a new disposable fixture; stop an existing test server on that port before running it. The 232-second test uses port 8773 and `.cache/long-fixture.json`, separately from the short fixture. Run fixture creation sequentially because the legacy fixture factory also writes `.cache/editor-tests/current.json`. The read-only capture requires the actual application already running on port 8784. No dependency installation or model inference is needed for these browser fixtures.

## Coverage

- Fresh Chorus → Verse and Custom → Pre-chorus names, optional manual titles, canonical type changes and custom-title preservation.
- Real section-edge pointer dragging, linked adjacent boundaries, explicit analytical overlap, confirmed trim/split ancestry, deletion, undo/redo, exact save/reload identity and time equality.
- Primary-layer versus all-layer comparison, unique-source/edition attribution, overlap-component note union and work-weighted aggregation.
- One full-song overview plus one detailed ruler/section/waveform/pitch stack; real paused/playing pointer scrubbing, passage handles, cancellation, zoom, pan, fit and playback state.
- Long-fixture section creation, resizing, saved IDs/times, reload, sidebar resizing/collapse, collection controls and Transcription/Research transport/zoom.
- Historical catalog, upload, correction/reference independence, review safeguards, learning/composition persistence/export, cross-song evidence, dual audition and metronome tests.

Both desktop projects use Chromium at 1366×768 and 1920×1080. Speaker output is muted; Web Audio analyser/decoded media signals still measure generated tones, original-vocal activity, independent buses, pause silence, loops and accented metronome output. This is signal verification, not a human listening-quality judgment.

The catalog test loops its short fixture and samples over a short window: a single frame can legitimately fall in a rest. It still requires continuing playback and a measured non-zero vocal signal after association edits. Earlier obsolete selectors were updated for controls intentionally moved to the collection manager and for viewport-relative seeking. A real overlapping sidebar-button hit target was fixed in the application rather than bypassed in the test.

Expanded history coverage also exposed and fixed loss of the restored section's active edit target after undo/redo. Saved-technique tests wait for the asynchronous composition handoff. The empty-state test holds the real library request pending and verifies **Choose an available song** stays disabled until catalog readiness, preventing an early click from incorrectly launching import.

## Protected actual recording

[Actual-recording acceptance](actual-acceptance.json) uses the 232.047-second personal recording without context-save, correction-save, reference attestation or composition writes. It navigates near 44 seconds, fits a 25-second passage, scrubs the detailed ruler, zooms, plays and pauses the original vocal, and checks independent passage/section state and absence of duplicate rulers. The recording has no saved 20–30-second section, so the journey explicitly uses a passage instead of inventing labels. Section edits are tested only on disposable fixtures.

[Protected-data verification](protected-data.json) compares SHA-256 with the pre-task manifest for 825 existing files under `data`, `outputs` and `evaluation`. No protected-root file was changed, removed or added. This includes existing audio, analysis reports/predictions, corrections, human references, context/beat revisions, ideas and stored scientific artifacts.

## Scope and limitations

The release does not establish new transcription accuracy or human annotation ground truth. Matching/retrieval, model estimation, note transcription, composition generation and frozen evaluation algorithms are unchanged. Section comparison's range aggregation changes explicitly to avoid overlapping-label double-counting; every label remains separately inspectable. The schema and interpretation are documented in [the section guide](../SECTION_EDITING.md).

Only structural and analytical layers are supported. A single shared-boundary conflict can be resolved directly; nested/multiple conflicts need explicit analytical overlap or confirmed trim. The compact overview cannot show every dense overlapping label in full. Legacy names remain untouched even when a user may wish to correct them. Roadmap M1 is not part of this task.
