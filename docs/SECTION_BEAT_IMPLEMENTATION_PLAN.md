# Section-aware and beat-aligned melodic intelligence: implementation plan

**Planning audit: 2026-11-05. Status: proposed, not implemented.**

This document is the only intended change from this task. The explicit planning-only instruction takes precedence over the implementation language in the requirements. No application changes, dependency installation, model inference, user annotation, or benchmark updates are part of this audit. Existing test results below are previously reported results, not fresh executions.

## 1. Product outcome and recommended sequence

Keep **Study song → understand a technique → create an original melody** as the primary journey. Add musical structure and a listening-based beat-alignment mode inside that journey. A single recording must remain immediately useful, even without sections or a confirmed grid.

Recommended order:

1. Define source identity, section revisions, beat-map revisions, musical time units, and compatibility contracts.
2. Ship manual section annotation and section playback using existing range selection.
3. Ship fixed-tempo manual alignment with an audible, synchronized metronome and honest confirmation state.
4. Add beat-aware measurements, uncertainty gating, and seconds/bar displays.
5. Add section-filtered, equal-song profiles and explicit cross-song A/B correspondence.
6. Connect these findings to the existing blank-original-idea workflow and shared meter/metronome.
7. Validate the complete journey and publish usage/audio-validation documentation.
8. Add variable-tempo anchors only after fixed-grid alignment and measurement are reliable.

Optional reference audio is a separate increment after the fixed-grid transport works. It should not block manual a cappella alignment. No new transcription model or general-purpose frontend framework is justified for this work.

## 2. Audit findings: working foundations and actual gaps

| Area | Existing evidence and reuse | Gap / required change |
|---|---|---|
| Source identity and ingestion | `src/audio_processor.py`, `src/pipeline.py`: native-source metadata, duration, content hashes, source-second events. `src/import_jobs.py` and `src/web/imports.js`: durable background import status. | Use source hash for structure/alignment ownership. A separate reference-audio role must bypass melodic transcription and artist inclusion. |
| Library/corpus membership | `src/library.py:recording_groups`, `validate_corpus_sources`: hash-based variant grouping, research exclusion requiring explicit opt-in. `src/web/library.js`: song search and corpus selection. | Song grouping currently uses artist/name text; no stable song/artist IDs. Different artists are not rejected just because an artist-profile title is supplied. Multiple recordings of the same song need explicit grouping. |
| Sections | `metadata.section` in reports, metadata editing in `src/workspace.py`, default import section in `src/web/app.js`; `src/corpus.py:profile_artist` compares whole-recording ranges grouped by this string. | No bounded section entities, occurrence IDs, section revisions, or waveform section track. Current “verse versus chorus” support depends on separate recordings carrying labels. A metadata default is not evidence of a section. |
| Phrases | `src/transcription.py:assign_phrases`, `NoteEvent.phrase` in `src/schema.py`; `src/features.py` groups events by phrase. | Rest-delimited phrase candidates are not section annotations or independently reviewed phrase boundaries. Sections must not rewrite these IDs. |
| Passage interaction | `src/web/learning.js`: live waveform range preview, handles, clear, phrase snapping, fit, source playback and loop. `src/web/learning-roll.js`: source roll, editable idea roll, shared edit history and highlighting. | Reuse the gestures for a separate section region layer; do not treat a section-boundary drag as note editing. Persist sections independently of the transient selected passage. |
| Existing beat arithmetic | `src/features.py:analyze_notes` computes `(onset-origin)*tempo/60` and deviation from nearest eighth-note position. | No meter, beat-unit declaration, bar numbering, beat duration/rest analysis, explicit confirmation, alignment uncertainty, swing model, or variable tempo. “user_supplied” is not a verification state. |
| Study context and chords | `src/learning.py:passage_study` accepts tempo/origin; `src/web/learning.js` sends passage context. Studies save context via `src/learning_store.py`. Chord analysis uses user-supplied annotations. | BPM/origin is study context, not a reusable independently revisioned recording beat map. UI wording “User-confirmed tempo” has no actual confirmation workflow. `chord_spans` assumes **one 4/4 bar per symbol** (`240/tempo`). |
| Core profile calculations | `src/corpus.py` deduplicates source hashes, averages recordings within artist/name song groups, then weights songs equally; includes support counts and conservative inference text. | Calls `analyze_notes(ns)` without beat context. Cannot filter timed section occurrences or make beat-aware section comparisons. Current song-title identity is fragile. |
| Motifs | `src/motifs.py`: bounded relative-pitch and adjacent-duration-ratio matching, edit distance, candidate variation labels, timestamped within/cross-song occurrences. | No beat/bar phase, IOI/rest representation, explicit correspondence path, or section filter. Duration ratios alone miss differences in rests. Cross-song matching compares song strings, which must become stable song IDs in the new path. |
| Evidence and exercises | `src/learning.py`: computed passage findings and explicit limitations; `src/learning_store.py`: immutable study snapshots, linked techniques, revisioned original ideas. | Add section/grid revision references and beat-aware evidence. Existing clipping can turn a sustained note crossing a selection edge into an artificial onset if treated naively. |
| Comparison UI | `src/web/learning.js:showComparison`: two normalized pitch rolls, original-vocal A/B, highlighted differences at equal sequence indices; different counts explicitly lack one-to-one matching. | Existing correspondence is positional, not an edit-alignment traceback. Add source-specific loading, beat-normalized axes, matched/unmatched notes, and honest weak-match states. |
| Transport/audio | `src/web/audition.js:VocalAudition`: one AudioContext, separate piano/vocal gains and analysers, original media element, resumable sessions, seek, source loops, temporary audition. Existing transport browser tests exercise actual signal. | No metronome bus, scheduled beat clock, accented count, tap tempo or count-in. Current loops are frame-driven and not promised gapless/sample-accurate. Extend the transport; do not start an independent playback engine. |
| Composition time | `src/composition.py:CompositionConfig` supports meter and uses numerator × 4 / denominator for bar length. Saved learning ideas explicitly use quarter-note beats. | `src/learning.py:idea_config` drops meter; `idea_notes`/`develop_idea` and frontend layout use `bars*4`; draw snapping is fixed quarter-beat increments. Correct these integration assumptions without rewriting the generator. |
| MIDI export | `src/pipeline.py:export_notes` uses actual event seconds and supplied tempo. | No time-signature event is written. Add an optional meter parameter for new idea exports, with existing default export semantics preserved. |
| Scientific isolation | `src/references.py`, `src/storage.py`, `src/real_metrics.py`, frozen manifests and `tools/check_editor_integrity.py`. | Structure/grid confirmation must never set human-reference attestation or change evaluation labels/splits. New derived analyses must not overwrite archived studies/profiles. |

Inspection also covered README, technical/evaluation/learning/transport/upload documentation, dependencies, browser configuration, and existing analysis, library, learning, import, transport and persistence tests. No metronome, section-region store or tap-tempo implementation was found in the current application.

### Local two-recording scenario, inspected read-only

The personal `outputs/analyses` catalog contains these two distinct source hashes:

| Recording | Source identity | Observed state |
|---|---|---|
| MHS Chorus | `baa063dd73f1676cb9615935b273df5fd6f7d8b36889b3d5797355f0379467d9` | 33.812494 s; three analysis versions; artist “Unspecified singer”; whole-recording section “chorus”; no report beat grid. |
| `[fadr.com] Vocals - 30 October 2026 - 108bpm - Cmaj.mp3` | `68c8eb595f18ee297d6c7f84bf72138f88aa7a4b18a28ab381a7f85d7b3e1735` | 42.353197 s; one analysis version; blank artist; section metadata “verse”; no report beat grid. |

These are two recordings, not verified independent songs by the same singer. The filename's “108bpm” and “Cmaj” are not confirmed musical context. Ask the musician to establish song/artist associations during actual use; do not invent them in the integration test. Neither pre-chorus/chorus boundaries nor beat offsets can be inferred as ground truth from these metadata fields. Test edits on isolated copies/disposable fixtures only.

### Validation baseline

`docs/UPLOAD_RELIABILITY.md` reports 91 Python, 11 JavaScript and 90 browser tests at 1366×768 and 1920×1080. Older documents report earlier totals. `docs/TRANSPORT_AND_TECHNIQUES.md` documents browser/device timing limitations and independently unvalidated MHS transcription. Preserve frozen real-vocal scores; passing UI or arithmetic tests does not validate musical annotation accuracy. No tests were rerun during this planning-only task.

## 3. Architectural decisions and storage contracts

### 3.1 Stable hierarchy without moving existing files

Represent the requested hierarchy as a **derived view**, not by nesting/copying note events:

`artist_id → song_id → recording source_hash → section_id → phrase intersection → note-edition event ID`

Add a versioned identity sidecar with explicit artist/song IDs and recording associations. An unassigned recording remains usable immediately. Legacy artist/song strings remain display metadata and grouping suggestions, never destructive merges. Choosing another model for a source does not create another song. Stable song links should be user-confirmed; changing a display title must not change identity.

Sections are owned by recording content hash and verified against source duration; edited/re-encoded audio with a different hash does not inherit them silently. Different excerpts/recordings of one song retain separate timelines. Association does not imply alignment between different audio files.

### 3.2 Independent revision stores

Proposed paths (new files only):

- `outputs/musical-context/catalog/{current.json,revisions/<revision>.json}`: stable identities and explicit recording membership.
- `outputs/musical-context/<source_hash>/sections/{current.json,revisions/<revision>.json}`.
- `outputs/musical-context/<source_hash>/beat-maps/<map_id>/{current.json,revisions/<revision>.json}`.
- A revisioned source-context selection identifies the active beat map; changing it does not rewrite either map's history.
- Optional accompaniment assets live under a separate reference-audio directory, linked by hash, role and offset.

Reuse atomic `write_json`, UUID IDs, `base_revision` optimistic concurrency, append-only revisions and restore-as-new-revision patterns. Share small persistence helpers where sensible; do not extend `ReferenceStore` to mean musical structure. Protect read/save/restore using the workspace lock only for brief state operations. Long analysis/audio decoding should not hold that lock, preserving the recent upload responsiveness fix.

Required envelope: schema version, source hash/duration, revision/parent, author, timestamp, items, provenance. Validation rejects NaN/infinite/out-of-source boundaries, duplicate IDs, unknown revisions and stale writes. GET/list requests must not create annotation files. Deletion removes an item in a new revision; restore preserves history.

### 3.3 Section semantics

Each section stores stable `section_id`, `type` (required enum plus Custom), editable display name, occurrence label/number, start/end **source seconds**, optional notes, color token and display order. Types: verse, pre-chorus, chorus, post-chorus, bridge, intro, outro, instrumental, custom.

- Initial primary section track is non-overlapping, with gaps allowed; adjacent edges may coincide. Reject overlap visibly rather than trimming another section silently.
- Multiple same-type occurrences are independent IDs. Names such as Chorus 1/2 are editable and are not matching keys.
- Chronological order is calculated from boundaries. Reordering a navigation list changes `display_order`, not source time. Adjacent-section/transition analysis always uses chronological order.
- Minimum interactive length: 80 ms, consistent with current passage selection; backend accepts valid positive finite spans. No rounding of stored coordinates to display precision.
- A section intersecting a phrase yields a derived phrase segment retaining parent phrase and event IDs. A crossing note is a carry-in/carry-out, not a new attack. Boundary fragments are excluded from attack and complete-duration comparisons, with excluded counts exposed.
- A phrase may appear in two section intersection views; aggregate unique source-event IDs and report partial coverage so it is not mistaken for two original notes/phrases.

### 3.4 Beat-map semantics: decide units before UI

Persist a fixed-map v1 with map ID, source identity, validity interval, BPM, **explicit BPM pulse unit in quarter-note units**, meter numerator/denominator, count grouping, bar-one origin in source seconds, subdivision/swing settings, and confirmation/provenance.

Canonical calculation unit remains **quarter-note beats (q)**, matching existing ideas. If BPM counts a pulse of `u` quarter notes:

`q(t) = (t - origin_seconds) × BPM × u / 60`

`t(q) = origin_seconds + q × 60 / (BPM × u)`

Bar length `L = numerator × 4 / denominator`; a notated denominator beat is `4/denominator` quarter notes. Legacy BPM uses `u=1`. Default 4/4 counts four quarter-note pulses; 6/8 explicitly supports six eighth-note counts or two dotted-quarter pulses with grouping 3+3. Show the chosen pulse unit next to BPM so 6/8 at “120” is not ambiguous.

Bar number is `floor(q/L)+1`; within-bar position uses positive modulo. Negative positions before bar one are displayed as pickup/preroll positions, never clamped or counted as song seconds. An origin may fall before zero or after an initial pickup. A map's declared usable interval stays inside the audio duration. “Align beat 1 at playhead” means set the bar-one origin; a future reanchor-other-bar command must preserve the named bar rather than silently resetting numbering.

Keep map state `provisional` or `user_confirmed`, with confirmer/time, listened validation range and optional user-estimated timing tolerance. Every BPM/origin/meter/subdivision/anchor edit invalidates previous confirmation. Confirmation is neither a calibrated probability nor a human-reference attestation. Missing uncertainty is “unknown”, never zero. Multiple saved candidate maps are permitted, but one explicitly active map is used for analysis. Conflicting maps cannot be silently mixed across a comparison.

Swing is explicit: store the long:short ratio for a chosen paired subdivision within the configured pulse. Ratio 1:1 is straight; 2:1 positions the second event at 2/3, not 1/2. No swing inference from a cappella. UI, scheduler, snapping and analysis must consume the same grid specification.

### 3.5 Compatibility and reproducibility

- Existing reports, source audio, raw predictions, corrections, reference revisions, frozen evaluation artifacts and saved ideas remain readable unchanged.
- Legacy `metadata.section` is displayed as legacy recording metadata. Offer an explicit “use as whole-recording section” action, never silent migration.
- Legacy `{tempo, origin}` context is an unconfirmed quarter-note grid in new interactive views. Existing archived features/studies remain historical snapshots; generating a new view does not relabel their provenance as confirmed.
- Old ideas default to 4/4 and quarter-note BPM. Add versioned meter fields only to new revisions; export previously saved revisions using their original semantics.
- New study/profile cache identity includes note fingerprint/prediction and correction revision, section revision, beat-map revision, identity/catalog revision, analysis version and relevant settings. No model re-inference is needed for a section/grid edit.
- Source evidence links pin exact structure/grid and note-edition revisions. After a change, mark old findings historical/stale and offer recomputation; do not rewrite saved technique or idea links.
- Keep old profile JSON keys and legacy endpoint behavior available. Add a new contextual profile response/version or opt-in path rather than replacing the saved profile format in place.

## 4. Audio and visual alignment design

Extend `VocalAudition` with a metronome component in the **existing AudioContext**. Add independent gain/analyser and a separate scheduled-node collection. Canceling a piano audition must not accidentally cancel clicks, and canceled transport clicks must never survive a seek/tab change.

Use Web Audio scheduled click envelopes with a distinct downbeat accent. Use a short scheduling lookahead (initial target: 100 ms horizon, 25 ms replenishment) driven by the current transport epoch and playback rate. JavaScript timers replenish the schedule; they do not directly produce the click on every tick. Visual count/playhead reads the same mapped playback clock, not an independent counter.

Original vocal time remains authoritative. Establish/rebase media-time ↔ AudioContext-time mapping after play/seek and invalidate future scheduling on pause, stop, waiting/stall, rate change, loop wrap, map edit, source switch and AudioContext suspension. At 0.5× playback, real-time click intervals double while stored source beat positions remain unchanged. Never modify audio samples or symbolic note times when moving the grid.

Count-in is a transport state with metronome-only pre-roll, not negative audio seeking. Generate one or more full bars ending at the selected entry's actual musical phase; if playback starts mid-bar, show the resulting count explicitly. Canceling count-in must prevent delayed vocal start. Auto note auditions temporarily suspend main-transport clicks; resuming the saved main position restores phase. Tab changes silence and cancel all active buses using existing transport lifecycle rules.

Do not advertise gapless or sample-accurate vocal loops based on scheduled-click accuracy. Media playback has browser/device latency. Display available latency information; distinguish measured Web Audio/internal timing from physical speaker latency. If scheduling reliability is insufficient during stalls or background throttling, pause/rebase and expose status rather than allowing a silently drifting click.

Reference audio increment: import through existing decoding/size validation into a reference-only asset; no transcription job/corpus checkbox. Link to a vocal using an explicitly chosen source offset (`reference_time = vocal_time - offset_seconds`) and optional gain/mute. Reject out-of-range access or render silence outside its coverage. Use the same transport and context with an additional controlled media source; verify seeks/stalls/rate changes on both streams. Different edits/tempos require additional alignment and must not be described as synchronized by filename or hash similarity.

## 5. Beat-aware measurements and interpretation rules

Introduce a pure beat-coordinate module with mirrored frontend transforms and shared test vectors. Keep original notes in seconds. Produce a derived per-event projection with note ID, original onset/offset, beat onset/offset/duration, bar position, nearest configured grid target, signed residual in beats and milliseconds, confidence/flags and map revision.

Required calculation families:

- Attack position within pulse/bar/subdivision; repeated-pitch onset and IOI rhythm.
- Full note duration in beats; strictly interior beat/bar crossings, distinguishing a note ending exactly on a line from one sustaining across it.
- Phrase entry/ending coordinates and carried notes at section boundaries.
- Internal rest start/end positions and durations; do not invent silence outside known/transcribed coverage.
- Rhythmic motif descriptors using relative onset/IOI, duration, gaps and optional bar phase, retaining continuous values alongside configurable matching tolerances.
- Peak location and density changes within explicit phrase/section windows, with supporting timestamps and denominators.

Confirmed grid required for beat-dependent musical findings. A provisional map may show a **preview calculation** to help alignment; it cannot emit an asserted groove finding, enter confirmed-only aggregation, or seed a beat-specific exercise as established evidence. Without a map, retain all existing second-based analyses and explain the missing context.

Report offsets as “X ms before/after this configured grid point.” Only call an entry anticipated/delayed **relative to a specified expected target**; nearest-grid assignment alone does not establish an intended attack. Boundary detection can track the pitched vowel later than a consonant. Show model scores separately from alignment tolerance; no conversion of model confidence into millisecond error bars. Where uncertainty bounds are supplied, test whether the residual sign/classification survives those bounds. Unknown or material uncertainty yields descriptive offsets and a listening prompt, not intentionality claims.

For section edges, count attacks by half-open onset membership `[start,end)`, include occupied overlap for sustained-time metrics, and flag clipped durations. Never calculate a melodic interval between unrelated phrase/section fragments. Transitions between adjacent sections are a separately labeled analysis with explicit end/start context and actual gap size.

## 6. Contextual profiles, comparisons and composition

### Profile aggregation

Select artist/song IDs explicitly. Mixed known artists or unresolved singer identity triggers a visible mixed/unassigned-corpus choice; do not present it as one singer's style. Retain existing research exclusion and source-level deduplication. Choose one note edition per recording explicitly, keeping the library preference stable.

Aggregate selected occurrences within a recording, recordings within a song, then equally across eligible songs. For repeated chorus comparisons, show each occurrence but count the song once toward cross-song support. Paired verse/chorus differences use only songs containing both requested types; disclose missing/unconfirmed sections and grids. Report separate supporting songs, recordings, occurrences, phrases, unique events, complete events and grid coverage. Two-song results are exploratory; no “signature” or robust population confidence claim.

Default Artist Patterns: compact section overview and context selector, then one active finding/comparison. Navigation groups: melodic structure, rhythm/groove, motif development, cross-song comparisons, Try This Technique. Existing interval distributions and long candidate lists move into an Advanced Statistics disclosure. One-song and insufficient-grid states remain useful and actionable.

### Comparison evidence

Reuse the two `LearningRoll` instances and original-vocal A/B transport. Each side carries its own analysis ID/source hash, section occurrence/revision, map revision, note edition and source bounds. Restore the source/playhead/passage correctly when switching A/B or returning from composition.

Relative-pitch view subtracts a declared anchor pitch. Beat-normalized view maps each side through its own confirmed grid, aligns an explicit section/bar/motif anchor, and retains a seconds toggle. This normalizes visualization/descriptors, not the source recordings. Default A/B playback remains original tempo/pitch; optional common-tempo playback is deferred rather than required for valid beat comparison.

Extend the motif matcher with a bounded traceback returning matched, inserted and deleted event IDs. Keep the legacy scalar distance path available. Explain what corresponds, what changed, and unmatched structure; do not equate equal array length with a true musical alignment. If grids are incompatible/unconfirmed or similarity is weak, show independent contours/seconds and the limitation. Bound candidate counts by section/song and expose truncation; do not let earliest file order dominate all evidence.

### Try This Technique

Carry a principle, concise instruction, measurable constraints, exact evidence/revision links, and suggested meter/tempo. Ask the user to accept those musical settings; never copy the source origin or note sequence into an idea. New idea time starts at its own bar one. Reuse existing blank roll, own-motif transformations, save/history/export, source return, live constraint feedback and similarity warnings.

Add only supported checks: e.g. increasing attack density in specified beat windows, peak after a chosen proportion of phrase beats, an explicit offbeat entry, or varying an original motif's rhythm. Avoid claiming a “progressive build” based solely on a longer last note. No constraint score is artistic quality; source similarity remains a warning, not an originality guarantee.

Propagate meter through `idea_config`, validation, bar limits, transforms, frontend fit/rulers/snapping, playback/count-in and optional MIDI meter export. Fix `bars*4` and fixed-4/4 chord placement at the integration points. Do not replace the existing composition engine or automatically reinterpret previously saved notes.

## 7. Phased delivery and completion gates

| Increment | Concrete work and affected files | Completion gate |
|---|---|---|
| **P0 — Contracts and preservation** | Add proposed `src/musical_context.py` (schemas/store) and `src/beat_grid.py` (pure coordinate logic); integrate new routes in `src/workspace.py`. Plan stable identity adapter in `src/library.py`. Add schema/test fixtures without migrating user files. | Legacy artifacts load; GET is read-only; source-bound validation, stale-save rejection and revision restore pass; Python/JS time-unit fixtures agree. Protected data hashes recorded. |
| **P1 — Section annotation vertical slice** | Add `src/web/sections.js`; extend `learning.js`, `learning-roll.js`, `index.html`, `learning.css`, `workspace.py`. Reuse selection/loop controls and add a dedicated colored section lane and compact navigator. Support all section types, multiple occurrences, boundary handles, rename/remove/reorder, undo/redo/save. | In a disposable recording create pre-chorus and Chorus 1/2, edit and reload, jump/loop/analyze each. No note/reference change; overlap/clipping semantics tested; single-song section findings work before any grid exists. |
| **P2 — Fixed beat-map + audible alignment** | Add `src/web/beat-grid.js` and `src/web/metronome.js`, integrated with `audition.js`; add Beat Alignment mode in study markup/controller. BPM/unit, meter, tap/reset/half/double, origin drag/nudge, align beat one, subdivision, volume, accent, count-in, loop, save/confirm. | Vocal and click signals demonstrably coexist; count and bars agree in 4/4, 3/4 and configured 6/8. Pause/seek/loop/rate changes rebase; grid editing changes no source/event time. Confirmation clears on edits and persists on reload. |
| **P2b — Optional reference audio** | Reuse ingestion/import validation with a separate reference-only upload endpoint; context link/store plus controlled reference bus in existing audio owner. | Reference import never enters artist corpus or runs transcription; offset/gain, source coverage, play/pause/seek and failure/stall handling tested. Manual vocal-only path works without this feature. |
| **P3 — Beat projection and Study overlay** | Add beat feature projection (prefer `src/rhythm.py` with narrow integration into `features.py`/`learning.py`); extend `learning_store.py` cache identity; shared beat/bar overlay in `learning-roll.js` and waveform. | Exact unit vectors, pickup/edge/carry-in tests pass; seconds↔bars toggles preserve source selection/edit precision; provisional/missing grids cannot create confirmed rhythmic conclusions. Every new finding links event IDs and map/section revisions. |
| **P4 — Section-aware profile and A/B** | Extend `corpus.py`, `library.py`, `motifs.py`, workspace/profile API; add focused `src/web/artist-patterns.js` and integrate existing profile UI in `app.js`, library controls and comparison rolls. | Same-section comparisons across two explicitly grouped songs, within-song occurrences and adjacent transitions work. Equal-song/mixed-artist/research safeguards pass; matched/unmatched notes have inspectable evidence. Advanced statistics remain accessible. |
| **P5 — Beat-aware original composition** | Extend `learning.py`, `learning_store.py`, `learning.js`, `learning-roll.js`, shared grid/metronome, `index.html`; optional meter argument to `pipeline.py:export_notes`. Reuse `CompositionConfig` meter validation. | Try opens a blank idea with accepted structural settings; user draws original notes, hears meter-aware piano/click, gets supported feedback, saves/exports/reloads and returns to exact source without losing the idea. Old 4/4 ideas/export behavior remains valid. |
| **P6 — Integrated validation and handover** | Add focused Python/JS/browser tests and capture tools; update README and dedicated section/alignment protocol and usage docs. Extend integrity checks with a fresh baseline limited to protected data/unmodified algorithms. | Complete nine-step user journey passes at both viewports with audio measurements, screenshots and no data drift. Read-only local two-recording checks completed; unsupported artist/beat labels remain unconfirmed. |
| **P7 — Later variable tempo** | Beat-map v2 monotonic anchors, piecewise-linear seconds↔quarter-note mapping, local validity/uncertainty, segment-aware scheduler and rhythmic projection. | Anchor monotonicity and interpolation/inversion, boundary-crossing durations, drift at early/middle/late anchors, edit invalidation, v1 compatibility all pass before enabling variable tempo by default. |

Each increment is an independently reviewable change. P1 can ship before P2; P4 must wait for identity/section contracts, and rhythmic P4/P5 features must wait for P2/P3. P2b and P7 are independent additions, not excuses to postpone the fixed-grid learning journey. Automatic sections, vocal beat tracking, swing detection and automatic accompaniment matching remain out of initial scope.

## 8. Acceptance-test specification

### Unit and persistence tests

Proposed `tests/test_musical_context.py`, `tests/test_beat_grid.py`, `tests/test_rhythm.py`, additions to existing library/analysis/learning/persistence suites, and `tests/beat_grid.test.cjs`:

1. Revisions append; restore creates a new revision; stale writers fail; invalid source/hash/bounds/meter/tempo fail. Removed section IDs remain inspectable in history.
2. At 120 quarter-note BPM, origin 0.5 s, 4/4: 0.5 s = bar 1 beat 1; 1.0 s = beat 2; 2.5 s = bar 2 beat 1. At 0.75 s: beat coordinate 0.5. At 0.4 s: pickup coordinate -0.2. Round-trip error ≤1e-9 s on ordinary-length finite fixtures.
3. At 120 dotted-quarter BPM in 6/8, one bar lasts 1 s and contains two grouped pulses or six eighth-note counts as configured. 3/4 bar duration differs from 4/4 at the same quarter-note BPM.
4. Swing 2:1 places the second of a paired subdivision at 2/3 of the pulse. Straight, triplet and swing calculations are explicit, not inferred. Equidistant nearest-grid ties have a deterministic documented policy.
5. A note spanning a section edge retains one source ID and one actual attack; a note ending on a bar line is not held beyond it. Rest, phrase ending and IOI calculations retain source evidence and uncertainty.
6. Missing/provisional/edited maps cannot produce confirmed groove findings; legacy context cannot bypass this gate. Filename tempo does not become a confirmed grid.
7. Two versions of one recording, two chorus occurrences, and multiple recordings explicitly grouped into one song do not increase cross-song support. Mixed artist and research inclusion requires explicit choice.
8. Motif match paths distinguish substitutions/insertions/deletions and gaps, and carry both source IDs. Weak/different-meter matches expose limitations. Cached results change when relevant section/grid/note revisions change.
9. Old reports/ideas/studies/profiles load without disk migration. Non-4/4 idea limits, chord bars, piano duration and MIDI meter round-trip correctly. Saved historical links retain their original evidence.

### Browser and actual audio tests

Add `tests/browser/sections-beats.spec.cjs`, extending existing fixtures and signal probes; use 1366×768 and 1920×1080. Tests use disposable sources and a read-only snapshot/copy of user material where needed.

- Label one recording's pre-chorus and chorus using live selection; drag boundaries, undo/redo, rename and reorder navigation; save/reload; test invalid overlap and stale revision conflict. Verify every original event/source hash is unchanged.
- BPM input, deterministic tap timestamps (e.g. 500 ms intervals →120 quarter-note BPM), outlier/pause reset, align/nudge/drag, subdivisions and meter all alter only the grid. Tap output is a provisional estimate, with stability feedback rather than false precision.
- Measure actual click-bus RMS/onset times and downbeat versus ordinary-beat envelope/accent; independently vary vocal/click gains and verify only the intended bus changes. Confirm original vocal remains audible and unmodified.
- Use rendered click signal as timing evidence, not just scheduler log entries. Initial foreground Chromium acceptance targets: offline scheduled-click onset within 2 ms; live click/transport relation within 40 ms after settled playback; visual count within one frame plus 40 ms; no accumulating drift over a 60-second test. Record hardware/browser and measured distributions. These are proposed test gates, not claims of achieved accuracy or external speaker latency.
- Seek, pause halfway, resume, stop, change playback rate, loop a non-bar-aligned section, interrupt count-in, switch tabs and audition a note. Verify silence after stop/pause, cancellation of stale scheduled clicks, correct resumed musical phase, no duplicate playback, and no note-timestamp changes.
- Verify downbeat count in 4/4 and 3/4 plus explicit 6/8 grouping; source-time alignment stays fixed at 0.5×/0.75×/1×. Test stalls/background suspension for safe resynchronization; expose limits if stable playback cannot be maintained.
- Compare two confirmed disposable same-artist songs with sections. Check normalized visual coordinates, original-tempo source A/B, event correspondence and exclusions. Neither an unconfirmed grid nor merely two matching passages can create an established artist signature.
- Open a beat-aware technique, draw a different original melody, hear piano/click, edit, check constraints, save/export/reload and return to the pinned source example. Composition notes survive workspace changes.
- Keyboard shortcuts ignore text input; section/grid gestures do not edit notes. Roll remains visible at both sizes with secondary controls collapsed; context/revision saves show progress and errors.

For the actual two-recording scenario: inventory hashes/versions and load/play existing sources read-only. Do not run mutating metadata/profile/study/reference endpoints against user data merely to demonstrate the plan. For authored section/grid tests, use disposable copies with visibly synthetic/test-only associations. A musician must eventually verify the real sections and beat phase; passing automated fixtures cannot supply that judgment.

### Scientific regression and delivery evidence

Before implementation, snapshot original audio, predictions, corrections, references, existing saved ideas/studies/profiles, frozen manifests and benchmark results. Re-score stored predictions with the existing evaluation environment and compare all score fields, using `tools/check_editor_integrity.py` with a fresh appropriate snapshot. Do not freeze every application file that is intentionally changing. Do not rerun inference or overwrite existing benchmark reports to make checks pass.

Handover must report new/existing test totals, skipped/blocking cases, measured click timing and latency caveats, screenshots of actual UI, exact local URL, user-data integrity checks, and remaining transcription uncertainty. Include a short musician-facing guide: label sections → tap/enter pulse → align/count/listen at beginning and end → confirm valid span → compare → try the technique. The guide must explain pickups, pulse units and how to leave alignment provisional.

## 9. Dependencies, risks and release decisions

**Dependencies:** Current Python stdlib/dataclasses/JSON, NumPy, existing decoding stack, pretty_midi, Canvas/DOM/Web Audio and pinned Playwright are sufficient for the planned fixed-grid scope. No runtime dependency addition is currently required. Reuse existing evaluation environment rather than installing model packages. Verify Web Audio/meter-export behavior against actual installed versions during implementation. Native browser audio/codec limitations and optional existing FFmpeg support remain relevant to reference-audio formats.

| Risk | Mitigation / release gate |
|---|---|
| False groove precision from imperfect note boundaries | Gate conclusions on confirmation and coverage; expose residuals and confidence provenance; distinguish pitched onset from syllable attack; no intentionality assertion. |
| Ambiguous BPM unit, pickups, compound meter | Explicit pulse unit and grouping; canonical quarter-note coordinates; shared Python/JS vectors before UI work. |
| Tempo drift in a cappella | Listen at separated points; allow limited validity span/provisional status; defer variable tempo honestly instead of forcing one grid onto the full recording. |
| Metronome drift/orphan clicks or disruptive count-in | One transport/context owner, scheduling epochs, cancellation on every lifecycle transition, actual multi-bus audio tests. |
| Source duplication or misleading artist sample size | Hash-based recording identity plus explicit song/artist IDs; per-song hierarchy of weights and eligible denominators. |
| Boundary clipping invents attacks or motifs | Separate occupancy from onset membership; retain carry flags and original IDs; exclude censored events where needed. |
| Repeated sections dominate comparisons | Aggregate within song first; expose occurrence counts separately; paired comparisons use eligible songs only. |
| Backward-incompatible 4/4/chord/idea changes | Versioned schemas, legacy defaults, optional export parameters, old saved-revision tests; no mass migration. |
| Save races and stale technique evidence | Optimistic concurrency; revision-pinned links; explicit recompute rather than silent overwrite. |
| Performance/clutter from many section pairs | Bounded candidate enumeration, relevant context filters, cached projections and one active comparison; long lists in Advanced. |
| Reference audio mistaken for a vocal or duplicate song | Explicit asset role, separate store, no transcription/corpus inclusion, manual offset/coverage validation. |

Proceed with P0→P1→P2→P3 first. That sequence delivers useful manual section study and an audible trustworthy musical time reference before using the new context to make cross-song or compositional claims.
