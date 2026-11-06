# Section editing and the unified Study timeline

Open [Melolysis](http://127.0.0.1:8784/?workspace=study). This update concerns section annotation and navigation; it does not implement roadmap M1 or change pitch estimation, transcription, motif matching, generation or evaluation algorithms.

## Fast labeling

1. Navigate with the compact full-song overview. Drag its blue viewport to pan; resize its ends to zoom.
2. Drag a passage in the detailed waveform using **Select range**. A new passage starts a fresh section draft: names from the previous section are cleared. A simple click does not replace a passage.
3. Choose a canonical **Section type**, then **Label selected passage**. The preview shows the exact type, generated name, layer and source-second bounds. Ordinary sections receive names such as **Chorus 1**, **Verse 1** and **Pre-chorus 1**.
4. Click **Save sections** to persist the revision. The inline receipt lists the saved sections and their times. Applying an edit and saving a revision are separate operations.

**New section** explicitly leaves edit mode. **Name / precise bounds** opens optional display-name and timing fields. A custom display name belongs only to its section; it is not a classification. Changing an automatically named section's type generates an appropriate new name. Existing manually named sections keep their names when edited, including when their classification changes.

Click a saved block to edit that exact section; the preview says **Editing** and shows its ID prefix. Double-click to fit it with modest surrounding context and open precise fields. Focusing a section does not change the independently selected passage. Selecting a new passage clears section-specific form fields while retaining the active section's visual highlight. **Fit section** and **Fit selection** therefore remain independent commands.

Drag section edges or use source seconds / `mm:ss.sss`, then apply and save. Previous/Next navigates sections. Undo/redo restores section transactions, including names, types, deletion, shared boundaries and overlap resolutions. To persist a restored state, save another revision. Undo history is in-session; previously saved immutable revisions remain in storage.

Invalid precise-time fields are reported inline and block applying the draft; malformed clock text never silently reuses the old numeric value. Unapplied field edits participate in the existing leave-recording/refresh warning, alongside unsaved section transactions and beat-grid edits.

## Explicit overlap policy

There are two typed layers:

| Layer | Purpose | Overlap policy |
| --- | --- | --- |
| `structure` (default) | Ordinary consecutive arrangement sections | Non-overlapping, apart from a one-microsecond numeric tolerance |
| `analysis` | Pickups, transitions, nested or intentionally overlapping labels | Explicit `overlap_policy: "allow"` |

Near-touching structural endpoints snap within 30 ms. This changes the candidate endpoint, not an existing neighbour. Exact source-second values are retained without frame quantization.

For an existing shared boundary, enable **Move shared boundary with adjacent section**, then drag or edit one side. This is an explicit two-section transaction; the option is off by default. All affected intervals must remain valid.

An unresolved structural conflict leaves the annotations unchanged and opens three choices:

- **Adjust shared boundary**: adjust one adjacent neighbour. A nested region or multiple conflicting neighbours requires a different choice.
- **Keep as analytical overlap**: keep both regions, IDs, names and times; put the candidate in the analytical layer.
- **Trim / replace existing regions…**: inspect the conflicting names/times and confirm before trimming/removing them. If a region is split, the first surviving part retains its ID; the second receives a new ID with `derived_from` pointing to the original. Undo restores the entire previous transaction.

Cancel leaves saved data unchanged. Invalid or out-of-source durations are rejected beside the controls. Overlapping blocks occupy separate detailed-lane tracks. The overview is deliberately condensed; use the detailed lane to select/edit individual overlaps.

## Two time-navigation levels

The full-song overview remains at whole-song scale. The unified detailed editor contains exactly one transport ruler, one section lane (with additional tracks for overlaps), one waveform and one pitch roll. All use the same source-second viewport and playhead. The former intermediate SEEK/SCRUB panel and duplicate pitch-roll waveform/ruler are removed.

Use the detailed ruler to click-seek or drag-scrub, independently of passage selection. The playhead extends through the editor. Ctrl+wheel zooms time around the pointer, Alt+wheel changes pitch zoom, Shift+wheel scrolls time, and middle-mouse drag or **Move / pan** navigates. Fit song, Fit selection, Fit section and the horizontal navigation slider change the viewport without changing annotations. Space toggles playback outside text fields.

## Storage compatibility and consumer audit

Section revisions written by this release use `melolysis-musical-context-v2`, with unchanged source hash, revision/parent-revision relationship and source-second coordinates. Beat-grid revisions remain v1 and are saved independently. No migration rewrites existing records or past revisions. Legacy sections without `layer` are structural; without `name_mode` they are treated as manually named, because the system cannot safely guess whether a historical name was automatic.

The optional fields are `layer` (`structure`/`analysis`), `overlap_policy` (`allow` for analytical regions), `name_mode` (`auto`/`custom`), and `derived_from` for an explicitly split region. Existing IDs and custom names survive edits. Type, never display name, is the canonical comparison filter. Multiple occurrences of the same type remain independent records. Start/end validation and stale-revision protection apply to all layers.

| Consumer | Interpretation |
| --- | --- |
| `src/musical_context.py` | Validates structural projection independently of interleaved analytical annotations; deterministic `(start, end, id)` ordering. `section_projection` is the explicit primary-layer/all-layer API. |
| `src/workspace.py` section comparison | Defaults to structural sections. Users can explicitly request analytical or all layers. Returns every occurrence with source, section/grid revision and the selected analysis edition. Overlapping interval components union note IDs before range aggregation; components average within recording, recordings within work, then works receive equal weight. Occurrence counts remain label counts, not independent-song support. |
| `src/web/context.js` Artist Patterns | Uses canonical type and an explicit layer filter. Multiple prediction editions are deduplicated by source before comparison. |
| `src/melodic_identity.py` | Retains all intersecting section metadata on a passage. This is attribution metadata, not an extra motif occurrence or independent-song count. Pairwise matching is unchanged. |
| `src/learning_store.py` | Carries source context revisions with study evidence; does not flatten section layers into note predictions or rewrite saved ideas. |
| Catalog snapshots / artist corpus | Preserve source/context revision relationships. Legacy song metadata is not inferred from section display names; source/work identity and existing equal-song safeguards remain separate. |

Future consumers requiring a segmentation must explicitly request the structural projection. Do not concatenate all layer occurrences into a new note sequence or count overlapping labels as independent songs.

## Verification and limits

See [validation results](sections/validation.json), [actual recording acceptance](sections/actual-acceptance.json), and the screenshots in `docs/sections/`. Browser tests edit only disposable synthetic fixtures; no human annotation is invented or attested. The actual 232.047-second recording is navigated and played read-only. It currently has no saved 20–30-second section, so that journey fits a selected 25-second passage instead of manufacturing a saved annotation.

Only structural and analytical layers are provided, not arbitrary user tracks. Shared-boundary resolution handles an adjacent neighbour; nested/multiple conflicts require analytical overlap or explicitly confirmed trim. Highly overlapping catalogs may create tall section lanes. Legacy names are preserved even if misleading; review them explicitly. Musical findings still depend on note-boundary, pitch and beat-alignment accuracy; this release establishes no new transcription accuracy claim.

## Implementation map

- `src/web/section-edits.js`: pure naming, snapping, conflict planning, shared-boundary and confirmed-trim transactions.
- `src/web/section-editor.js`: create/edit state, preview, optional properties, inline validation, conflict dialog and revision feedback.
- `src/web/study-navigation.js`, `learning.js`, `learning-roll.js`, `style.css`: unified timeline assembly, viewport-aware ruler, overlap tracks and linked pitch-only roll.
- `src/musical_context.py`, `src/workspace.py`, `src/web/context.js`: compatible section validation, explicit layer queries, overlap-safe summaries and the existing Artist Patterns controls.
- `src/web/app.js`: unapplied-section-field navigation protection. `workspace-layout.js`: contextual collection master controls retained when the sidebar controls are hidden. `index.html`: loads the two section modules.
- `tests/test_musical_context.py`, `tests/section_edits.test.cjs`, `tests/browser/section_editor.spec.cjs`: schema, transactional and real interaction coverage. Historical browser specifications update intentional sidebar relocation and viewport coordinates without bypassing core behavior.
- `tools/capture_section_fix.cjs`: actual-library read-only acceptance and screenshots. `package.json` and Playwright configurations include the new cases and keep the long fixture isolated.
