# Human singing-note reference protocol — singing-notes-v1

Reference annotations describe the main sung melody on the **original file's
timeline**, in seconds. They are musical interpretations made by a named person,
with uncertainty recorded explicitly. A model-assisted draft is not ground truth.

## Prepare an excerpt

1. Select a recording and listen before inspecting model differences. Prefer a
   5–12 second passage containing complete phrases, with excerpt edges in rests.
   Set **Loop from/to** to the original source times; do not subtract the excerpt
   start from note timestamps.
2. Open **Independent human reference annotations**. Enter your name and choose
   **New blank reference**, or explicitly choose **Seed draft**.
   Seeding records the model identity and leaves the annotation unreviewed.
3. Assign a song/singer group and a development or heldout split before evaluation.
   The same recording or group cannot occur in both. Use separate songs/singers
   for generalization claims; two slices of one recording do not establish that.
   An unassigned draft may be assigned on save; an assigned split cannot later be
   flipped after examining results. Earlier frozen manifests keep their original groups.

## What is a note?

Use the intended, audible melodic target, checked against the performance rather
than a semitone crossing in the contour. Use the same interpretation throughout
the dataset. Disagreements between credible annotators are retained as separate
editions rather than merged into whichever gives a model a better score.

| Case | Annotation convention |
|---|---|
| Sustained note / vibrato | One note while the perceived target is sustained. Oscillations and amplitude pulses alone are not note onsets. |
| Onset | First audible periodic vocal sound belonging to that target, including its entry scoop. Exclude an unpitched preceding consonant. Mark uncertainty when the boundary cannot be located consistently. |
| Offset | End of that performed target's periodic voicing or the transition into the next intended note. Exclude detached reverberation, leakage and breaths. Do not erase a real quiet ending just because the model loses it. |
| Entry scoop / bend | Attach a continuous entry gesture to the arriving target. Preserve the expressive contour separately. |
| Glissando / portamento | Annotate identifiable intended endpoints. Do not make every crossed semitone into a note. If there is no reproducible target interpretation, label the ambiguous interval uncertain; add a glissando region. |
| Grace note | Keep a very short but clearly separate intended pitch target. There is no automatic 60/80/100 ms minimum for human labels. Mark ambiguous ornament-versus-scoop decisions. |
| Same-pitch repetition | Separate audible re-attacks or re-articulated syllables, including glottal attacks without silence. Preserve any gap. Small vibrato/energy fluctuations alone are insufficient. |
| Melisma | Annotate each intended melodic target on the same syllable. Label a melisma region only when the syllable relationship is actually known from listening/lyrics. A sequence of short notes is not automatically a melisma. |
| Silence / breath | Leave a gap between note events. Do not move later notes earlier. Breaths are not pitched notes. |
| Harmony / doubling / leakage | Follow the selected lead melody. Mark regions where the lead cannot be separated confidently; do not select the loudest or highest line merely because a model does. |

Pitch is a MIDI-valued target center and may be fractional. For example, a note
35 cents below MIDI 60 can be labeled 59.65. Keep the recording's tuning; do not
retune reference audio or labels to make a model agree. Consider the stable center
of a vibrato note, not its extremes. Reference notes are a symbolic interpretation;
they do not replace independently corrected continuous F0 annotations.

## Editor procedure

1. In reference mode, green bars are the reference edition and red bars are the
   immutable raw prediction. The audio, waveform and F0 retain source time.
2. Drag note bodies to adjust timing/pitch, and drag edges to resize. Use Draw for
   missing notes, split at the playhead, merge compatible fragments and delete
   false events. Fractional pitch and exact source timing remain available in the
   inspector/advanced table. Use note/phrase loops and piano/original-vocal audition
   to inspect attacks and transitions. A reference tone is a listening aid, not truth.
3. For an uncertain region, set loop bounds, choose **Uncertain**, enter a reason
   and use **Mark selected range uncertain** in the inspector (or **Label loop region**
   in the advanced setup). Other region types document vibrato, glissandi,
   grace notes, repeated attacks, breaths, leakage and known melismas. Region JSON
   can be edited to correct or remove a label.
4. Save a draft whenever needed. Reference revisions are stored separately from
   normal corrections and model predictions. Earlier saved revisions remain intact.
   Save before changing recording/editor mode; unsaved edits are not automatically
   promoted or considered annotations. Visual edits and region changes share
   undo/redo. Restoring a saved reference appends a draft and clears attestation.
5. Listen to the **whole excerpt**, then verify every pitch, onset, offset, pause
   and uncertain region. Enter the reviewer's name and tick the listening/review
   attestation before saving a reviewed revision. Editing notes/regions clears
   that checkbox. A second reviewer is preferred and recorded separately when used.
   Do not tick it merely because a graph looks plausible.
6. **Compare saved reference to raw prediction** displays note errors, coverage and
   downstream changes. A draft comparison is prominently labeled preview-only.
   Export the reviewed manifest to freeze exact revisions and checksums.

The server verifies source bounds and disallows overlapping main-melody notes in
manual editions. Imported published editions retain their authored overlaps and
fractional centers instead of silently rewriting the source labels.

## Uncertainty and scoring

Choose uncertainty based on the audio and annotation convention before examining
comparative accuracy scores. Never mask a region just to make a model score better.
Scoring excludes note events that overlap uncertain spans and reference F0 frames
inside them. Both exclusions and unmasked note scores are reported. The rule can
be optimistic if a long incorrect prediction touches an excluded span; inspect
excluded counts and coverage rather than comparing a bare F1.

A note editor does not establish frame-level F0 or voicing truth. Those metrics
remain unavailable until an independently corrected continuous contour is supplied.
Never expand flat note rectangles into a fabricated expressive-pitch reference.

Default note evaluation uses 50 ms onset tolerance, 50 cents pitch tolerance and
an offset tolerance of max(50 ms, 20% reference duration). These are evaluation
tolerances, not instructions to move boundaries onto a 50 ms grid. Timing errors
are conditional on matched events. Repeated-pitch and short-note subsets have
explicit operational definitions; a melisma score requires human-labeled regions.

## Published Vocadito references

The optional Vocadito v3 import retains the source CSVs' onset, duration and Hz
pitch, plus the published human-corrected F0. A1 and A2 remain independent editions.
Their convention differs from this protocol: musicians interpreted the line as
something they would reproduce on a piano, with different ornament and lyric
segmentation choices. Tony supplied initial automatic estimates that musicians
corrected, so annotation-tool bias toward the pYIN family is possible. These are
published musician annotations independent of Melolysis, **not new reviews by the
user or this agent**. [Dataset](https://zenodo.org/records/5578807),
[annotation methods](https://arxiv.org/abs/2110.05580).
