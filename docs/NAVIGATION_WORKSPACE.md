# Long-recording Study Song workspace

Open http://127.0.0.1:8784/. This update changes navigation, section editing and library layout. Retrieval, transcription and model evaluation algorithms are unchanged.

## Navigate and select

The compact overview waveform always represents the full source recording. Its top edge seeks/scrubs. The blue rectangle represents the detailed editor's viewport: drag it to pan, or drag its ends to zoom. Gold section highlighting identifies the active section independently of the blue viewport.

The lower ruler, section lane, waveform and piano roll share the LearningRoll source-second viewport. The detailed ruler seeks/scrubs; the waveform's **Select range** tool selects passages. **Move / pan** and middle-mouse drag navigate without selecting. Ctrl+wheel zooms time around the cursor, Alt+wheel changes pitch zoom, and Shift+wheel scrolls time. The horizontal range slider provides discoverable navigation. Time +/−, Fit selection, Fit section and Fit song use the same viewport.

On recordings longer than 30 seconds, the initial detailed view spans 20 seconds. Selection, section boundaries, audio timestamps and beat origin are not quantized or changed by navigation. Sections can be a few seconds long anywhere in the recording. Space retains play/pause behavior outside text fields.

## Label and edit sections

1. Navigate near the desired time in the overview and zoom into a short region.
2. Drag a passage on the detailed waveform. Choose its type and click **Label selected passage**. The preview shows the automatically generated occurrence name. Optional custom naming is under **Name / precise bounds**.
3. Click **Save sections** to persist a new revision. Empty names receive type-based numbered labels; type and display name remain separate fields.
4. Double-click a section block to focus it and open precise controls. Drag its left/right handles to resize, or enter `mm:ss.sss` / source seconds, then **Update selected section** and **Save sections**.
5. Previous/Next section and Fit section navigate without rewriting times. Section undo/redo uses the existing history. Existing IDs and context revisions are retained.

Structural sections use tidy adjacent boundaries. Intentional overlaps are explicit analytical annotations, shown on separate tracks. Conflicts offer shared-boundary adjustment, analytical overlap, or confirmed trim/replacement; nothing is silently deleted. Inline feedback distinguishes unapplied fields, unsaved transactions and saved revisions. See [section editing and schema policy](SECTION_EDITING.md). Beat alignment remains under **Sections & beat alignment**; moving the grid uses the detailed viewport's time scale.

## Library, collections and uploads

- Drag the divider to resize the library; arrow keys resize it when focused. Double-click resets to 260 px. The menu icon collapses/restores it. Width and collapse preferences persist locally.
- The default library is song navigation: search, artist filter, compact recording cards, refresh and Add songs. The open recording has its existing highlight; corpus membership is a separate collection state.
- Each card's **⋯** opens artist/work associations. Model versions and human-reference controls remain accessible in Transcription/Research.
- **Add songs / uploads** opens the original file-upload control, queue, progress, retries, completed items, Open song/Dismiss actions and advanced import settings. Completed jobs are no longer permanently expanded in the sidebar. An active-upload count stays on the manager button.
- **Artist Patterns → Collection manager** contains corpus checkboxes, scoped bulk actions, research opt-in, profile building and source/model filters. Existing section comparison remains available in that workspace. Research remains excluded unless explicitly enabled.
- Saved composition ideas remain in Create Melody. Resizing, collapsing and switching workspaces do not replace the active passage or composition.

## Validation and performance interpretation

The 232-second browser fixture is synthetic UI contract data, not pretrained inference or human transcription ground truth. Tests exercise actual Chromium pointer gestures at 1366×768 and 1920×1080. Performance measurements on the actual 232.047-second personal recording (449 notes, 23,258 F0 frames) are recorded in `navigation/real-performance.json`; screenshots show the real application. Rendering uses screen-width waveform extrema summaries, cached waveform backgrounds, a cached full-song overview and animation-frame-coalesced detail renders.

Reported render timings measure the draw/update callback; pointer timings measure DOM pointer-event timestamp to animation-frame callback, not physical display latency. Heap figures are Chrome's reported JavaScript heap, not total browser/process memory. No old-UI benchmark was taken, so these numbers do not establish a speedup. Source loading and transcription processing are separate from navigation timing. Large catalogs, substantially longer audio and very large note/F0 arrays require further benchmarking.

The earlier navigation release measured p95 draw callbacks of 8.9 ms at 1366×768 and 9.8 ms at 1920×1080, and pointer-event-to-frame p95 of 20.2 / 23.7 ms. Chrome reported about 19.3 MB of JavaScript heap in both sizes. These are historical samples (71 renders and 31 pointer events per size), not a fresh benchmark of the section reliability follow-up or a performance guarantee.

The preceding navigation release passed 112 Python and 11 JavaScript tests plus focused browser tests. The section reliability follow-up reruns the full historical gate with selectors updated for deliberately relocated controls; see its [current validation summary](sections/validation.json) for exact results rather than treating the preceding focused run as full coverage.

Reproduce the focused browser suite with `node tools/run_browser_tests.cjs --config playwright.navigation.config.cjs`. The server uses only disposable synthetic data. The real-recording capture script is `tools/capture_long_workspace.cjs`; it navigates and listens but does not save edits. Existing protected file hashes are checked independently. See [validation summary](navigation/validation.json) and [real performance](navigation/real-performance.json).

Limitations: precise section properties and beat controls expand vertically; at 1366×768 some vertical scrolling is needed. The full-song overview remains sticky within Study Song. Very short overview labels may require their tooltips; use the detailed lane for precise editing. Composition and statistical algorithms remain unchanged, and roadmap M1 is not implemented here.
