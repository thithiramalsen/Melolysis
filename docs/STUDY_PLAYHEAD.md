# Independent Study Song playhead and passage lanes

Updated 2026-11-05. Application: http://127.0.0.1:8780/.

The ruler above the full-recording waveform is always a seek/scrub surface. Click it or drag the yellow handle to move the playback position. Pointer capture keeps the drag active beyond the handle and outside the ruler. The live label displays source seconds during the gesture. Arrow keys on the focused handle nudge 10 ms, Shift+Arrow nudges one second, and Home/End seek the recording bounds.

The waveform below it is always a passage-selection surface. Drag to create a passage, resize with its existing boundary handles, or use Clear selection. A waveform click no longer seeks. Piano-roll note clicks continue to audition the vocal; they do not select passages. Alt-drag waveform remains a deliberate beat-alignment gesture. The global waveform gesture dropdown was removed.

The two lanes stay pinned together while scrolling the Study workspace. They show the full recording as a stable navigation reference; the detailed piano-roll viewport retains independent time/pitch zoom and pan. Time/Pitch buttons, Ctrl+wheel, Alt+wheel, middle drag, Fit excerpt and Fit song retain their behavior. View changes do not alter the selected passage, sections or beat-grid parameters.

Scrubbing reuses VocalAudition's original media element and resumable song session. During a drag, the existing transport pauses, source-position previews update immediately, and actual media seeks are serialized with the latest pending target replacing older intermediate targets. Releasing resumes if the transport was playing when the gesture began. A paused drag stays paused. This is source-position scrubbing, not synthesized tape-scrub audio. Source timings and pitch are unchanged. Browser decoding/seek latency still applies.

Cancellation/lost capture ends the gesture without starting playback. Changing source/workspace invalidates pending resume intent. The ruler/handle DOM stays stable during playback. Static ruler marks are cached; paused animation frames do not repeatedly redraw waveform/note layers.

## Validation

`tests/browser/study_playhead.spec.cjs` uses actual pointer down/move/up gestures at 1366×768 and 1920×1080. It selects five seconds, drags the handle outside the lane, checks live time/unchanged bounds, drags while playing, pauses/resumes from the new position, zooms and repeats. Additional cases exercise ruler clicks, boundary handles, vocal-note audition, Clear selection and pointer cancellation. Existing transport/context tests cover audio, looping, grids and metronome behavior. The metronome-accent test now captures actual audio callback buffers instead of opportunistic short-window analyser samples, avoiding missed transients under UI load.

`tools/capture_study_playhead.cjs` repeats real pointer interactions against MHS in a muted headless browser. Mutating API calls are blocked; only local passage selection, navigation and playback occur. At both sizes a 0.5–5.5 s passage survived paused/playing drags and zoom. A drag to 2.1 s resumed, then paused at approximately 2.18 s; the subsequent piano-roll zoom and ruler drag reached 3.2 s. Resumed original-vocal RMS was approximately 0.066. No page exceptions occurred. All 128 protected original data/reference/evaluation files retained their hashes.

Screenshots and measured results: `outputs/playhead-demo/`. Archived browser results: `docs/playhead/`.

Final results: all 110 full-suite browser checks passed at both desktop sizes. All six focused pointer/transport checks passed again after the recording-end guard was added. Scrubbing past the recording end stays paused at the end rather than restarting. The final preservation check confirms all 128 protected files are unchanged.
