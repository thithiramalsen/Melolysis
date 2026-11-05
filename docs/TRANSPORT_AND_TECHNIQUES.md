# Transport, passage selection and technique exploration — 2026-11-05

Current server: **http://127.0.0.1:8776/**.
[Open MHS Chorus](http://127.0.0.1:8776/?analysis=5fb48b6259d2a98d40c651bcbe3ea15420284cd49d9e6a8a62cd4deae598cf6e).
The previous server/browser was left alone. To start this version later:

```powershell
.\.venv\Scripts\python.exe main.py serve --output outputs --port 8776
```

## Listening controls

The existing `VocalAudition` owns one original-vocal media element, one AudioContext
and the existing independent piano/vocal buses. Main transport now has resumable
song, passage and composition contexts; it is separate from temporary auditions.
No additional playback engine or model was introduced. The previous advanced
composer's reference playback also uses the shared player.

- **Space** toggles the current workspace's main playback. It is ignored in text
  fields, selects, editable text and dialogs; checkbox Space retains normal input
  behavior. Holding Space does not repeatedly toggle.
- **Play song / Play passage / Play piano** pause when already playing and resume
  from the stored position on the next press. Completion, a new passage, or Stop
  can start a new traversal; ordinary Pause does not restart a phrase.
- **Stop** cancels audio and resets the relevant context: song start, passage
  start, research loop origin or composition beat zero. It also works after an
  audition before the first main Play, and after returning from another tab.
- Individual keys/notes and source examples temporarily pause main playback.
  The next main Play resumes its saved position. Main playback does not restart
  automatically when an audition ends. The Study clock identifies auditions.
- Changing workspaces pauses main playback and ends temporary sounds. Returning
  does not start audio automatically or discard the stored context position.
- Clicking the source timeline seeks in original seconds. The composition ruler
  seeks in beats at the idea's tempo. Song, selected-passage and piano looping
  use their own contexts; hidden research-loop controls cannot wrap Study playback.

Reference-note elements stay stable while a playhead moves. Previously the learning
roll rebuilt them each frame, which could delay a click until the passage ended.
Note clicks can now interrupt running playback promptly and preserve its position.

## Select and inspect a passage

Drag the full-song waveform with its crosshair cursor. The highlighted region,
boundary labels and source-second readout update **before mouse release**. On
release, the detailed roll fits the selected passage. Selecting a finding retains
that passage and highlights its evidence rather than replacing the selection.

Drag either boundary handle to resize; focused handles also accept Left/Right
in 10-ms steps, or Shift+Left/Right in 100-ms steps. Precise numeric fields remain
under Passage details. Stored values retain full floating-point source time;
three-decimal labels are display formatting. The minimum range is 80 ms.

**Snap to phrases** optionally attracts boundaries within 150 ms of detected phrase
edges. These are transcription/rest-based candidates, not verified breath or lyric
boundaries. Snapping defaults off. **Clear selection** returns to whole-song scope,
with a distinct waveform treatment and explicit Entire song label. A changed range
asks for a fresh analysis rather than presenting stale findings.

## One active technique

The compact candidate list includes source timestamps. Selecting one candidate:

1. Activates one explanation and highlights its actual note IDs in the main roll.
2. Shows the measured event, exact example bounds and its surrounding phrase scope.
3. Offers contrasting choices and a prominent **Try this technique** action.
4. Retains the full measured observation and limitations in optional details.

Peak observations mark the relevant high target. Duration contrast includes
proportional long/short bars. Supported phrase comparisons retain A/B audio and
normalized contour views. For equal-length examples, highlights indicate changes
in interval/duration ratio at corresponding sequence positions; this alignment
still needs listening. Different target counts are explicitly unaligned, rather
than inventing a precise changed-note correspondence.

The composition handoff retains the principle, exercise, exact source audio link
and structural constraints. The canvas starts independently from source pitches.
Once three original notes exist, appropriate controls let the user alter first
leap size, move a peak, or shorten/hold alternate notes. Descending leaps retain
their direction when size changes. Each operation participates in Undo/Redo.

Edits trigger a debounced, read-only constraint check. The roll border and compact
toolbar status update along with detailed checks. Matched/unmatched colors describe
measurable goals, **not artistic quality**. Tests demonstrate changing an original
contour, refreshing feedback and returning to the source without losing notes.

## Actual validation

| Check | Result |
|---|---|
| Python regressions | **87 passed** |
| JavaScript editing/core | **11 passed** |
| Playwright | **84 passed**, no skips/flakes/failures; 42 cases at each of 1366×768 and 1920×1080 |
| New interaction coverage | 12 checks for transport positions/signals, live selection/handles/snap/clear, compact evidence, temporary audition restoration, typing, tab silence, loop/seek and live experiments |
| Scientific regression | **64 stored comparisons re-scored identically**; frozen manifest revalidated |
| Protected files | **154 unchanged**: Python algorithms, original audio, raw predictions, annotations/corrections, existing idea/technique/study revisions and frozen evaluation files |

Tests use one speaker-muted headless Chromium worker and disposable synthetic
fixtures. Legacy annotation, reference-history, MIDI persistence, research exclusion
and audio-bus tests remain in the combined run. These checks do not establish new
transcription accuracy. [Browser results](transport/browser-validation.json),
[audio measurements](transport/audio-measurements.json),
[evaluation regression](transport/evaluation-regression.json).

### MHS acceptance journey

The real application capture dragged a **0.500–6.500-second** range, verified the
highlight/readout while holding the mouse down, then committed it. At 1366×768:

- Original vocal RMS was approximately **0.101** before pause and **0** after pause.
- The passage paused at **3.562132 seconds**, stayed fixed while paused, then
  resumed to approximately **3.710159 seconds** without restarting.
- Analysis produced real source-backed candidates; one active finding highlighted
  its evidence while retaining the selected passage.
- Four original notes were drawn in a separate, **unsaved** idea. Piano RMS was
  approximately **0.0203**, then **0** when paused. Its own transport position
  advanced from about **0.2233** to **0.3160 seconds** after resume.
- Returning to the source preserved those original notes. No annotation,
  correction, idea-save, technique-save, generation or inference POST was made.

Both viewport sizes passed with no runtime errors. Exact signals, positions,
requests and protection checks are stored locally in
`outputs/transport-demo/journey-checks.json`. Private MHS screenshots remain
git-ignored in the same directory:

- `mhs-selecting-1366x768.png`, `mhs-selecting-1920x1080.png`
- `mhs-paused-1366x768.png`, `mhs-paused-1920x1080.png`
- `mhs-technique-1366x768.png`, `mhs-technique-1920x1080.png`
- `mhs-compose-1366x768.png`, `mhs-compose-1920x1080.png`

The user's existing saved ideas and MHS human-reference edition were not changed
or attested. The test idea was discarded on browser close.

## Reproduce

```powershell
npm run test:browser
npm run test:editor
.\.venv\Scripts\python.exe -m unittest discover -q
.\.cache\model-env\Scripts\python.exe tools/check_editor_integrity.py --snapshot .cache/transport/protected-before.json --output .cache/transport/evaluation-regression.json
node tools/archive_editor_validation.cjs --transport
node tools/capture_transport_journey.cjs
```

Run only one browser-test process at a time. The integrity snapshot is a session
artifact. Development tests require the already documented Playwright install;
normal application use still needs only Python and a supported browser.

## Files and limits

Implementation: `src/web/audition.js`, `app.js`, `editor.js`, `learning.js`,
`learning-roll.js`, `learning.css`, `index.html`. Tests/capture:
`tests/browser/transport.spec.cjs`, `tools/capture_transport_journey.cjs`.
Archival/documentation: `tools/archive_editor_validation.cjs`, this document,
README and `docs/transport/*`.

Positions are preserved in the transport's own source-second/tempo timebase; browser
seeks, output latency and frame-driven loop boundaries are not sample-accurate or
guaranteed gapless. Resuming a held piano target schedules its remaining duration
with a new reference-tone envelope, not phase-continuous sample playback. No
speaker/headphone calibration or new human usability study was performed.

MHS transcription is still independently unvalidated. Target errors, phrase
segmentation, short fragments and clipped selections can change these observations.
Peak/repetition/duration findings are local properties of extracted events; neither
numerical compliance nor model agreement establishes emotion, artistic quality or
an artist-wide habit. Existing source-similarity warnings and harmonic/lyric-context
requirements remain unchanged.
