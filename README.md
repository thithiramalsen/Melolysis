# Melolysis

Learn a singer's melodic decisions and use the principles to make your own music.
Use [Song / artist associations](docs/CATALOG_IDENTITY.md) in the recording library
to confirm artists, musical works and takes without rewriting original reports.
Unresolved identities stay explicit; model variants are one source recording.
The primary workflow is **Study song → understand a technique → create your own
melody**. Start with one recording: choose a phrase, hear its vocal and pitch
contour, analyze the actual note events, then choose **Try this technique**. Draw
an independent melody, explore transformations of your own motif, hear a piano
reference, save an idea and export the edited MIDI. Singing/recording is optional.
There is no voice cloning or generated singing.

The default workspace is song study. **Artist patterns** compares selected songs;
its [melodic relationships workspace](docs/MELODIC_IDENTITY_USAGE.md) now compares
two recordings with explicit note correspondences, original-audio A/B and a linked
original-motif exercise. Legacy profile statistics remain under Advanced.
**Transcription / research** retains the full correction, reference and evaluation
workflows. Seed/density/MIDI-limit generation controls are under Advanced in the
composition workspace. See the [learning journey and validation](docs/LEARNING_EXPERIENCE.md)
and [product gap audit](docs/PRODUCT_GAP_AUDIT.md).

[Transport and technique explorer](docs/TRANSPORT_AND_TECHNIQUES.md): Space/Play
pause and resume in each workspace; drag a passage with live timestamps/handles,
select one evidence-backed technique, then experiment with original notes and
receive live structural feedback.

[Sections and manual beat alignment](docs/SECTION_BEAT_USAGE.md): label timed sections, align a vocal to an audible metronome, inspect saved-grid timing, compare section occurrences and carry a timing principle into an original idea. This is a fixed-tempo increment; the guide lists remaining plan work.

This overhaul fixes the original loss of rests, frame-based note fragmentation and
missing timestamps. Phase 2 measured actual pretrained GAME Small and TorchCREPE
Tiny inference against two published human annotation editions of eight Vocadito
recordings, with four singers held out from local development. Accuracy remains
limited and annotation-dependent; synthetic scores do not predict real note F1.
pYIN remains the default CPU baseline. SOME/Basic Pitch remain unvalidated.
See [measured evaluation and limitations](docs/EVALUATION.md),
[technical audit](docs/TECHNICAL_AUDIT.md), and [model assessment](docs/MODEL_COMPARISON.md).
See the [real-vocal results](docs/REAL_VOCAL_VALIDATION.md),
[model environment setup](docs/MODEL_SETUP.md) and [human annotation protocol](docs/ANNOTATION_PROTOCOL.md).

The integrated [visual annotation editor](docs/ANNOTATION_EDITOR.md) now supports
direct note dragging/resizing, a pitch-aligned piano keyboard, original-vocal and
contextual piano/vocal audition, loops, slow playback, undo/redo and independent
revision restore. Recording-level grouping, scoped corpus selection and a collapsed
tabbed inspector keep the main editor clear. [Current UX validation](docs/UX_VALIDATION.md)
records browser/audio checks and source-integrity regression.
[Browser and audio validation](docs/EDITOR_VALIDATION.md) records the tested scope.

## Quick start — Windows PowerShell

The existing project venv works with Python 3.14.3. For a fresh core installation,
use Python 3.12–3.14 and available wheels; only the recorded 3.14 environment has
been tested locally. Keep neural backends in their supported environments.

```powershell
cd D:\VSCode\GitHub\Melolysis
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-eval.txt
.\.venv\Scripts\python.exe main.py analyze "data/vocals/MHS Chorus.wav" --artist "Artist" --section chorus
.\.venv\Scripts\python.exe main.py serve
```

Open [the local workspace](http://127.0.0.1:8765) yourself. The server binds only to
127.0.0.1 and does not open or control desktop windows. Ctrl+C stops it. Choose a
different port with `serve --port 8766`. The workspace uses no CDN or cloud service.

`python main.py` still selects the first supported filename alphabetically in
`data/vocals/`, preserving existing file discovery. It now reports missing input
instead of silently synthesizing an example. WAV, FLAC, MP3, OGG, M4A and AAC are
accepted; codec support depends on the decoder. MP3 was tested with this libsndfile
build. AAC/M4A may need FFmpeg on PATH and have not been tested here. Isolated vocal
stems are the default input; no source separation runs automatically.

## macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-eval.txt
python main.py analyze /path/to/vocal.wav
python main.py serve
```

These instructions are provided for portability; this overhaul was tested on
Windows. `requirements-tested.lock.txt` records the exact Windows Python 3.14
packages, including transitive and evaluation dependencies. The bounded core
requirements are preferable when using a different Python or OS.

## Review and correct

1. Choose a song in the library or **Import vocal audio**. Artist and song search
   are available immediately; model versions/settings remain secondary.
2. Choose an audible phrase, or drag a region on the waveform/pitch grid. Hear it
   with **Hear passage**, then choose **Analyze this melody**.
3. Read a supported observation and click **Hear** to see its exact targets and
   hear the original recording. Multi-phrase passages can be compared A/B with
   transposition-normalized views and interval patterns.
4. Choose **Try this technique**. The idea roll starts blank. Draw your own notes,
   choose a comfortable note-name range, key/scale and tempo, and use **Explore
   variations of my motif** to change rhythm, ending or develop an answer.
5. Audition the piano reference, edit, **Check this technique**, **Save idea** and
   **Export saved MIDI**. The exported revision includes your edits. Source
   evidence remains linked; it is never copied into a new idea automatically.
6. Use **Artist patterns** to compare several songs by the same singer. One song
   still has useful local findings, but cannot establish an artist signature.
   Research/Vocadito stays separate and needs explicit corpus opt-in.
7. When needed, open **Transcription / research** for the original DAW editor,
   independent reference editions and model comparisons. Optional singing feedback
   is at the end of the composition workflow, after saving an intended melody.

Prediction files, original recordings and manual editions are separate. Selecting
another model never deletes corrections; a correction stays attached to the input
content hash. Rechecking a correction against a substantially different prediction
is a human task. Imported polyphonic MIDI is rejected with an explicit overlap
error; select/export the lead melody in your DAW before importing it.

### Create a human reference

Normal working corrections and evaluation references have separate histories.
Use the reference toolbar and **Inspector → History / revisions**; select source-time loop bounds,
enter your name and choose a blank reference or a clearly marked model-seeded draft.
Edit pitch/onset/offset and phrase fields; add, split, merge or delete events. Label
ambiguous spans using **Uncertain** with a reason. Green bars show the reference;
red bars show raw predictions. Download saved reference JSON for backup.
In reference mode the header exports the **saved reference JSON**. Working-mode
MIDI/CSV/report exports remain separate; switch to Working mode to access them.

For the supplied **MHS Chorus.wav**, a draft is ready at **0.500–6.500 source
seconds**, with **11 predicted events** requiring review. Select that recording,
choose the **Pending human annotator** edition, and click **Edit / compare reference**.
Listen and correct every event using the protocol. Enter your annotator/reviewer
names, tick the explicit listening attestation only after review, and save.
The draft has not been scored as validated accuracy and contains no fabricated
human labels. A second independent reviewer is preferable. The eight public
recordings have published musician annotations, not new reviews by this agent.

**Export reviewed manifest** freezes reference revisions and content checksums.
Draft previews are visibly labeled; formal `real-evaluate` rejects drafts. A note
editor alone supplies no expressive F0 truth, so frame metrics remain unavailable
for your recording until independently corrected F0 labels are supplied.

The interface supports microphone recording into local PCM WAV, but browser/device
permission and end-to-end microphone capture were not tested. Recording does not
upload audio to a remote service. Use the file-import alternative if a microphone
is unavailable. Editor playback streams the original audio and channels after a
source-hash check. Unsupported browser codecs explicitly fall back to the existing
mono/resampled playback copy. Source audio stays intact. Browser latency and
time-stretch sound quality require listening on your own device.

## Build an artist corpus

```powershell
.\.venv\Scripts\python.exe main.py analyze "verse.wav" "chorus.wav" "another-song.wav" --artist "Artist"
.\.venv\Scripts\python.exe main.py profile --all --artist "Artist" --output outputs
```

In the workspace, select recordings and build a style profile. Set metadata first:
artist, **song**, section, tempo, key/mode, language, genre and tags. Use identical
artist/song names for excerpts of the same song. Duplicate analyses of identical
content count once. Excerpts are averaged within each song; songs have equal
weight. A long recording cannot dominate simply through its number of frames.

Reports include phrase-local interval/rhythm distributions, tessitura, rests,
leap/recovery evidence, phrase peaks/contours, section ranges, candidate motif
families within/across songs, sample counts and exceptions. Acoustic expression
estimates remain separate. Timestamp buttons return to the supporting source.
Bootstrap intervals require at least three song groups and describe this sample,
not a population. A small corpus does not establish artist specificity.

A reference comparison is available via `profile report1.json report2.json
--reference other1.json other2.json`. References must be reports, not raw audio.
No population baseline, deep artist embedding or unsupported emotional claims are
produced. A single song profile is exploratory.

## Configuration and harmonic context

```powershell
.\.venv\Scripts\python.exe main.py analyze "vocal.wav" --config configs/analysis.example.json
```

Analysis settings specify sample rate/hop, range, channel policy, confidence,
minimum duration, transition persistence and phrase-rest threshold. The default
stereo policy chooses the higher-energy channel to avoid antiphase cancellation;
choose `mean`, `left` or `right` when appropriate. Lower thresholds increase review
work and can admit leakage. Closely spaced ornaments can still be merged.

All frames retain source timestamps. Centered pYIN frames occur at k*hop/sample_rate;
notes use half-open [start,end) intervals. F0 computation uses overlapping context
chunks, retaining each core frame once. TorchCREPE uses an explicit native 16 kHz
lattice; the effective hop is in `raw_pitch.timebase`, avoiding internal hop-rounding
drift. No guessed universal latency correction is applied.

A confirmed grid can be supplied with `--tempo 100 --beat-origin 0.2`. This enables
beat positions and eighth-grid deviations; tempo is **not** inferred from drum
transients in the vocal. Optional `--chords chords.json` accepts a list such as:

```json
[{"start":0,"end":4,"pitch_classes":[0,4,7],"label":"C"}]
```

For scale degrees, pass `--metadata metadata.json` with an explicit context:

```json
{"tonal_context":{"tonic_pitch_class":0,"mode":"major"},"language":"en"}
```

Chord membership and phrase endings are measured against supplied annotations.
Passing/neighbour-tone suggestions are marked as interpretations. No chords are
confidently inferred from an isolated voice. Full suspension, harmonic tension and
meter-aware syncopation analyses remain future work.

## Compose and sing

```powershell
.\.venv\Scripts\python.exe main.py compose outputs/artist-profile.json --config configs/composition.example.json
```

The composer uses seeded interval/rhythm tendencies, phrase/breath templates,
scale/range constraints and optional chord scoring. Configure tonic, scale, tempo,
time signature, bars, density, contour, section, repeated-pitch tendency, syllable
count, stress note indices and a subjective creative direction. Section/direction
are creative metadata; they do not activate an untrained emotional model.
Syllable counts currently use one note per syllable, not automatic lyric alignment.

Multiple candidates have piano-roll previews, plain reference tones, MIDI/CSV/JSON
and constraint assessments. Editable note JSON can be auditioned; downloaded MIDI
is labeled as the original candidate. Edited candidate persistence/export is not
implemented yet. No generated voice is used.

Transposition-invariant interval and duration-ratio window matching rejects high
source resemblance. Comparisons require at least six notes; shorter source/candidate
material is marked **not assessed**. Screening is heuristic and does not establish
legal originality. Compare and sing any candidate yourself.

Build a profile for evidence-linked exercises, editable four-bar structures and
constraint feedback. Pick an exercise, record/import your sung attempt, inspect its
transcription and compare the stated constraints. Exercises with little supporting
occurrence are labeled contrast exercises. Artistic merit and emotion are yours
to judge. CLI feedback is also available:

```powershell
.\.venv\Scripts\python.exe main.py feedback path/to/attempt/report.json exercise.json
```

Extract one exercise object from `artist-profile.json` into exercise.json.

## Tests and reproducible benchmarks

```powershell
.\.venv\Scripts\python.exe -m unittest discover -v
.\.venv\Scripts\python.exe main.py benchmark --output outputs/benchmark --estimators pyin torchcrepe
.\.venv\Scripts\python.exe main.py benchmark --suite stress --output outputs/stress --estimators pyin torchcrepe
.\.venv\Scripts\python.exe main.py evaluate evaluation/my-reference-manifest.json --output outputs/evaluation
# Phase 2: strict reviewed references, grouped splits, real pretrained inference.
.\.venv\Scripts\python.exe tools/import_vocadito.py
.\.venv\Scripts\python.exe main.py real-evaluate outputs/real-validation/vocadito.manifest.json --systems evaluation/real/systems.validated.json --split development
.\.venv\Scripts\python.exe main.py real-evaluate outputs/real-validation/vocadito.manifest.json --systems evaluation/real/systems.validated.json --split heldout
.\.venv\Scripts\python.exe tools/report_real_validation.py
```

Benchmarks perform actual F0 inference on deterministic synthetic harmonic audio
with known continuous F0 and note labels. They are explicitly not a real singing
dataset. The development suite helped tune the scoop rule; the perturbed stress
suite is reported separately. The short-melisma stress failure is retained.
Comparisons include original compressed-time segmentation, frame rounding with a
correct timebase, and improved events. `mir_eval` validates onset/pitch/offset scores;
frame and timing metrics use source-aligned conventions.

Install/download the isolated models and optional public dataset using
[MODEL_SETUP.md](docs/MODEL_SETUP.md) before running the Phase 2 commands. For your
own reviews, use `reference-manifest --output outputs --manifest path.json`, then
`real-evaluate path.json --systems ... --split development` (or heldout).
The older `evaluate` command accepts legacy manifests and does not enforce the
new human-review/split gates. Both score raw predictions, never active corrections.
Optional neural models/weights and their licenses are documented in
[MODEL_COMPARISON.md](docs/MODEL_COMPARISON.md).

Optional browser regression tests (Node/Chromium are not production requirements):

```powershell
npm ci --ignore-scripts
$env:PLAYWRIGHT_BROWSERS_PATH="$PWD\.cache\ms-playwright"
npx playwright install chromium
npm run test:editor
npm run test:browser
```

These use disposable synthetic fixtures, headless Chromium and muted speaker
output while measuring actual Web Audio/decoded media signals. They do not create
human annotations or establish real-singing perceptual audio quality.

## Storage, compatibility and remaining limits

`outputs/` contains content-keyed pitch/note caches, immutable predictions, current
reports, mono playback copies, correction history, corpus profiles and composition
references. Relevant configuration, package versions, local stage-code hashes and
model identities participate in caching/provenance. Keep backups of **corrections**
and originals; outputs and raw data/vocals are git-ignored. Cache deletion is never
needed to retain manual work; avoid deleting the corrections directory.

Original audio and pre-existing PNG/MIDI files are untouched. Legacy load_audio,
extract_pitch, midi_conversion, extract_features, plotting and pitch-chain APIs
remain available. `midi_conversion` durations are now **seconds**, with start/end
fields. Its default 512-hop compatibility convention must match the supplied F0.
The new pipeline does not use the old Markov chain as its composer.

Remaining priorities: human review of your own recording; larger independent
real-vocal evaluation; robust short ornaments/repeated syllables; polyphonic lead selection;
validated slides and octave ambiguity; richer beat/harmony/lyric modelling; broader
browser/device/OS coverage. F0 inference is chunked, but decoding still loads the
recording in memory. External model processes cold-load per uncached clip. Motif
search is bounded and discloses truncation. See the evaluation report for the
precise tested scope rather than treating every planned capability as complete.
