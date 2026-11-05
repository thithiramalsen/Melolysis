# Sections and manual beat alignment

Implemented increment, 2026-11-05. Open the updated server at http://127.0.0.1:8779/.

## Study one recording

1. Open a song. Use the permanently available timeline ruler to click-seek or drag the yellow playhead. Drag in the separate waveform lane to select a passage; its edge handles resize the passage. Seeking never changes the selected passage. No gesture-mode dropdown is required.
2. Expand **Sections & beat alignment**. Select a passage, choose its type/name and click **Label selected passage**. Drag the yellow section edges or edit the precise boundary fields. Sections may have gaps but cannot overlap. Repeated choruses have distinct IDs. Rename, remove or change navigation order, then **Save sections**. Undo/redo applies to section edits; saves append independent revisions.
3. Use **Open** or **Loop** for a section. Analyze this melody uses the selected region. Section labels never change model notes or transcription references.
4. Use Time/Pitch zoom buttons, Ctrl+wheel for time, Alt+wheel for pitch, Shift+wheel for time pan, and middle drag to pan. **Fit excerpt** and **Fit song** change the roll viewport without changing the selected passage. The entire-song overview remains a fixed navigation reference.

## Align the musical reference

Expand Beat alignment. Enter BPM, meter and the pulse unit (quarter, eighth or dotted quarter). Tap tempo estimates from the median recent tap interval; a long pause resets tapping. Filename tempo is never automatically accepted.

Play the original vocal with **Metronome** enabled. Volume controls the separate click bus. Downbeats use a stronger, higher-pitched click. The visible count follows the denominator beats in the chosen meter (4/4 counts 1–4; 6/8 counts 1–6). **Beat 1 at playhead**, +/-10 ms, the origin field, or Alt-drag in the waveform lane adjust the grid, never the recording. Count in one bar plays a metronome-only lead-in before the passage. Stop cancels count-in.

Confirm only after listening, then save. Confirmation covers the selected passage at save time; it does not attest the transcription. Editing grid parameters clears the checkbox. Analyze uses the **saved** grid, whereas live overlay/clicks preview unsaved controls. Save before interpreting updated measurements. Analysis outside the confirmed coverage remains provisional.

Enable Bars/beats for bar labels on the source roll; its coordinates and underlying notes remain original source seconds. The amber waveform/roll grid is a listening reference even when provisional. Swing ratio sets the paired subdivision reference used for residual calculations; audible clicks currently mark denominator beats, not swung subdivisions.

The rhythmic evidence table lists source onset, bar, within-bar position in quarter-note units, duration in quarter-note beats and signed residual milliseconds to the configured paired-subdivision reference. Click a row to hear its original note segment. These are pitched-onset observations, not conclusions about intentional groove or consonant timing. Source note confidence is an estimator score, not calibrated timing accuracy.

## Compare sections and write an original idea

In Artist patterns, use **Compare musical sections across selected songs**. Select unique personal recordings using existing corpus controls. Assign the same explicit artist using recording metadata first. Blank or unspecified singers and research material are rejected by this comparison path. Types filter actual saved section occurrences, not the recording-level legacy section field.

The comparison offers source section playback, two selectable pitch-normalized rolls and original-tempo A/B. Confirmed-grid views use quarter-note units; otherwise the view uses seconds. Each starts at its section boundary and normalizes its first pitch to C4 for display. Original audio stays unchanged. No event-to-event correspondence is asserted. The API provides per-occurrence range and an equal-song mean range, averaging occurrences within each song first. Two songs remain exploratory evidence.

A confirmed half-quarter-beat entry can produce **An entry between quarter-note beats** in the technique explorer. Try this technique starts a blank independent idea and offers the source tempo/meter as a creative reference. Draw your own pitches and rhythm. The check reports an offbeat entry against your chosen idea grid; it does not grade artistic quality. Create Melody supports 4/4, 3/4, 6/8 and 2/4, meter-aware phrase bounds and a shared metronome bus. Saved new ideas and MIDI exports retain meter. Old ideas default to 4/4.

## Preserved data and implementation boundaries

Context files live in `outputs/musical-context/<source_hash>/sections` and `grid`, with independent current pointers and append-only revisions. Stale saves fail instead of replacing newer work. No original recording, human reference, correction or frozen score is migrated. Re-encoded audio gets a different source identity. Existing source-title/artist grouping remains the song identity mechanism; stable catalog IDs from the larger plan are not implemented yet.

This increment implements manual sections, fixed-tempo grids, metronome/count-in, event timing projection, section-filtered comparison and a beat-aware technique handoff. It does **not** complete every proposed phase. Remaining work includes stable artist/song IDs; context revision restore UI; multiple candidate maps; variable tempo anchors; reference accompaniment import; subdivision click options; compound-meter accent grouping; calibrated timing uncertainty; richer phrase/rest rhythm features; motif alignment traceback; paired adjacent-section transition findings; and the full default Artist Patterns redesign. Existing detailed artist statistics remain available in their current interface.

Metronome scheduling uses the existing AudioContext and a short lookahead. Browser media loops/seeks are not guaranteed sample-accurate or gapless. Device latency, background throttling, stall recovery and long-duration drift have not been calibrated. The generated accent and independent click mute have actual signal tests, but this is not a claim of measured acoustic alignment to speakers. Count-in is a full bar, rather than a pickup-aware partial count.

MHS and the other local recording have not received invented section labels, confirmed beat maps or artist identities. Their melody transcription remains subject to the previously documented real-vocal limitations.

## Verification

96 Python and 11 shared JavaScript tests passed. The full browser suite passed 102 checks at 1366×768 and 1920×1080; after final metronome lifecycle/overlay adjustments, all 14 focused section/grid/comparison/technique checks passed again, including count-in cancellation. Actual analyser signals verify audible click generation, stronger downbeat accents and independent mute. Existing vocal/piano signal and transport regressions passed in the full suite. These checks do not establish calibrated hardware latency or long-term click/media drift.

All 128 protected data files retained their hashes. Re-scoring 64 frozen prediction/reference records yielded identical scores. Detailed records are under `docs/section-beat/`. Read-only actual MHS screenshots are under `outputs/section-beat-demo/`; MHS was not labeled, aligned or attested during capture.
