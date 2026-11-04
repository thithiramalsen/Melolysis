# Visual vocal annotation and dual audition

The existing workspace now has a direct-manipulation piano roll, original-vocal
audition and a local piano-like reference instrument. Production use still requires
only the existing Python server and a modern browser; Node/Playwright are test
dependencies. There is no cloud upload, voice cloning or generated singing.

## Open the prepared MHS draft

The updated review server for this session is at **http://127.0.0.1:8773/**, leaving
the previous server/browser undisturbed. Choose MHS Chorus, select **Pending human
annotator**, then **Edit / compare reference**. It opens **0.500–6.500 original source
seconds**, with 11 unreviewed model-assisted notes. The reference ID remains
`137e4f16e5b3425d91367adc0169eaf3`; no MHS annotation, correction or attestation was
written during development. The selected analysis/reference are kept in the local
URL so a refresh reloads the saved edition. Unsaved edits require an explicit save.

To start your own server after this session:

```powershell
.\.venv\Scripts\python.exe main.py serve --output outputs --port 8773
```

An older Python server must be restarted before using updated assets/routes; it
does not hot-reload backend code. The new session server above already has them.

For any new excerpt, follow this sequence:

1. Choose a 5–12-second passage with edges in rests. Set loop bounds or drag the
   **Select time range** tool across the pitch grid.
2. Use **Play range** and listen before making judgments about the model.
3. Enter your name in **Reference setup, review & revisions**. Start a **New blank
   reference** or **Seed draft**. Seeding copies raw predictions and records their
   identity; it never creates a reviewed reference.
4. Inspect the waveform, continuous F0 and note rectangles together. Use the piano
   keyboard and original-vocal auditions as listening aids.
5. Drag pitches/times and resize boundaries. Add, split, merge or delete notes.
6. For an unresolved passage, select a range, write an uncertainty reason in the
   inspector, then choose **Mark selected range uncertain**. The amber span and
   region list remain editable without typing JSON.
7. Listen to the complete excerpt again. Check every target, attack, offset and
   rest. Follow the [annotation protocol](ANNOTATION_PROTOCOL.md), including its
   conventions for vibrato, slides, grace notes, repeated attacks and melismas.
8. Use **Finish review…**, enter the reviewer's name, and explicitly tick the
   listening attestation. **Save reference revision** saves the edition as reviewed
   only when that attestation is supplied. Otherwise it saves a draft. A second
   independent reviewer remains preferable.

Confirming a review-queue item is a local note-review flag. It does not verify the
whole excerpt, assign a human F0 truth contour or mark the reference reviewed.

## Work directly on notes

| Action | Interaction |
|---|---|
| Select | Click a rectangle. Shift/Ctrl-click toggles multi-selection. |
| Select a group | Shift-drag a box across the grid. |
| Move | Drag a note body; selected notes move as a group. |
| Resize | Drag its left/right edge. Boundaries stop at neighbours and source/excerpt limits. |
| Adjust pitch | Drag vertically; **−1 / +1** transpose the selection. |
| Fine pitch | Turn off **Semitone moves**, or hold Alt during a drag. |
| Add | **Draw notes** tool: click for a short note, or drag its duration. Double-click empty grid in Select mode also adds a note. |
| Split | Put the playhead inside a note, then **Split at playhead**. |
| Merge | Select adjacent compatible notes, then **Merge selection**. Targets must be within one semitone; the duration-weighted center stays fractional. |
| Delete | Delete/Backspace or **Delete selection**. |
| Cancel a gesture | Escape before releasing. No annotation change or history entry is committed. |
| Undo / redo | Ctrl+Z / Ctrl+Shift+Z (or Ctrl+Y), or the toolbar buttons. |

Horizontal movement is unquantized source time. Semitone moves apply an integer
**delta**, preserving a label's tuning: 69.37 → 70.37, not 70.0. Free pitch and exact
inspector fields remain available. Resizing keeps strictly positive duration with
a 1-microsecond interaction floor; musical accuracy is limited by the audio,
listening and display resolution, not established by the number of decimals.
Source sample times, F0 hop timestamps and audio speed are never rewritten.
Reference mode exports its saved reference JSON; Working mode retains its separate
MIDI/CSV/report exports. MIDI's existing semitone-only note export does not replace
the fractional-pitch reference JSON or CSV data.

Dragging only previews a proposed change until release. The same edit history
covers notes, uncertainty regions and confirmation flags; new edits branch away
from the redo history. The advanced table uses that same history and save path.
Piano keys and notes use one pitch-to-pixel map at every zoom level.

Green rectangles are the human-reference edition; blue rectangles are ordinary
working corrections. Red lines are immutable raw model events, gray lines are the
optional alternative model, and the lime trace is raw expressive F0. Amber marks
identify review flags/uncertainty, not known errors. A raw model line can be selected
for listening even in a blank reference; its inspector is read-only and it is not
copied into human annotations merely by selection or audition.

## Piano, vocal and Both

Choose **Click auditions**:

- **Piano reference:** a local additive piano-like tone at the selected symbolic
  pitch. A4 is 440 Hz; every visible semitone, including black keys, is available.
- **Original vocal:** the original recording at the event's source onset/offset,
  with adjustable pre-roll/post-roll (defaults 60/80 ms).
- **Both together:** that same original vocal segment plus a reference tone at the
  symbolic target. There is one vocal media source, not two copies of the recording.

**Audition note** always plays the selection using that mode. **Audition on click**
optionally makes note selection play it immediately; it defaults off. Clicking a
piano key always auditions: in Vocal/Both mode it chooses a selected associated
note first, then another matching note when available. If none exists, it explicitly
falls back to piano. The status line says which source is playing. Selecting a raw
prediction allows its source segment to be auditioned without creating a reference.

**Hear −1 / Hear +1** audition neighbouring semitones without editing a note.
**Vocal → piano A/B** plays the recorded segment, then the reference tone.
**Piano drag preview** optionally sounds proposed target pitches during a vertical
drag. Piano and vocal volumes are independent. The main **Play** button/Space
always controls original recording playback regardless of audition mode.

Moving a rectangle does **not** retune the recorded singer. Both/A-B can expose a
difference between original intonation and a proposed target; the reference tone
is a listening aid, not proof of an annotation. No microphone is required.

## Listening, navigation and browser limits

- Drag the playhead handle or click the ruler/waveform to seek.
- **Note loop** and **Phrase loop** use selected source events, including pre/post
  roll. Phrase membership is the stored annotation/rest heuristic, not lyric truth.
- **Select time range**, loop bounds and **Play range** provide custom loops.
- Ctrl+wheel zooms time at the pointer; Alt+wheel zooms pitch. Plain wheel scrolls
  pitch; Shift+wheel scrolls time. Middle-button drag pans both axes. **Fit** returns
  to the reference excerpt, selection or complete source.
- Choose 1×, 0.75× or 0.5× playback. Browser pitch preservation is requested and
  unsupported exposed APIs are handled explicitly. Note timestamps stay in source
  seconds, including at slower speed.

The server streams the hash-checked original file for playback. If the browser
cannot decode a validated original codec, it explicitly falls back to the existing
mono/resampled playback copy with the same timeline. A changed/missing original
does not silently bypass the source-integrity check. The analysis waveform/F0 may
use the configured channel policy; original playback retains the original channels.

Both mode routes one HTML media element and the reference instrument through one
AudioContext and schedules the piano against the vocal's source position. The
playhead uses `currentTime`; neither seeks, loop boundaries nor acoustic alignment
are sample-accurate guarantees. Loop stopping uses animation-frame checks and may
overshoot by a frame or more under load. Browser/device output latency and
time-stretch artifacts remain. **Browser audio timing** exposes reported latency
where supported. Automated headless checks do not calibrate speakers/headphones
or establish perceptual transparency on real singing.

The implementation follows the browser's [pitch-preserving playback interface](https://developer.mozilla.org/en-US/docs/Web/API/HTMLMediaElement/preservesPitch)
and [Web Audio timing/source model](https://www.w3.org/TR/webaudio-1.1/). It applies
no guessed universal timestamp offset.

## Review queue and saved editions

The queue ranks evidence for listening: alternative-model event disagreements,
low F0 confidence, explicitly unavailable note confidence, octave-sized jumps,
wide F0 spread, short fragments, close repeated pitches, legato boundaries,
internal contour transitions and alternative-only possible missing notes. A
possible melisma requires actual syllable/lyric confirmation. All thresholds are
disclosed in the item text/source rules. Suggestions are confined to the selected
reference excerpt; they never insert or verify notes automatically.

Selecting an item zooms to its source passage; optional queue looping auditions
the original passage. Confirm notes, edit them, or mark unresolved uncertainty.
Model agreement/disagreement is not ground truth. Working mode stores review
flags on notes; only independent reference regions supply evaluation masks.

Open **Reference setup, review & revisions** to restore a saved edition. Restoration
appends a new revision and keeps earlier files intact. Reference restoration clears
listening attestation and remains in the current assigned split. Published dataset
editions stay read-only. Working corrections and references have separate histories,
and stale saves/restores are rejected. Backup saved JSON/history and original audio;
undo/redo covers the current unsaved session, not browser closure.

## Optional shifted-vocal preview: investigated, deferred

Arbitrary formant-preserving vocal pitch shifting is **not implemented**. Native
pitch-preserving slow playback does not supply that feature. The investigated
[Rubber Band library](https://breakfastquay.com/rubberband/) supports independent
pitch/time manipulation with GPL/commercial distribution terms; integrating a
native or WASM worker would add processing, caching, latency and licensing work.
It would also require listening tests for formants, consonants, vibrato and
crossfaded note boundaries. No adapter, model-quality claim or retuned-vocal export
is presented here. Clean piano/original-vocal audition is complete first.

## Reproduce validation

```powershell
.\.venv\Scripts\python.exe -m unittest discover -v
npm ci --ignore-scripts
$env:PLAYWRIGHT_BROWSERS_PATH="$PWD\.cache\ms-playwright"
npx playwright install chromium
npm run test:editor
npm run test:browser
```

Playwright 1.64.1 is pinned in package-lock.json. Tests launch a separate headless,
speaker-muted Chromium with one worker, and a disposable synthetic fixture server
on port 8772. No test edits the MHS reference or main correction store. The fixture
uses actual synthetic WAV decoding/pYIN plus a clearly labeled alternative stub
for disagreement tests; it is not a second-model accuracy demonstration or human
ground truth. Browser output/audio measurements are archived in
[editor validation](editor/browser-validation.json) and
[audio checks](editor/audio-measurements.json). Scientific evaluation regression is
reported in [evaluation-regression.json](editor/evaluation-regression.json).

Screenshots at [1366×768](editor/fixture-1366x768.png) and
[1920×1080](editor/fixture-1920x1080.png) show the disposable fixture. Private MHS
screenshots stay under git-ignored `outputs/editor/`. See
[EDITOR_VALIDATION.md](EDITOR_VALIDATION.md) for exact results and limitations.
