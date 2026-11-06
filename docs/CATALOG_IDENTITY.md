# Catalog and snapshot integrity — M0

Open **http://127.0.0.1:8783/**. The catalog is an independent sidecar; it does not change source audio, raw predictions, human references or their review status.

## Associate your recordings

1. In the song library, click **Song / artist associations** beneath a recording. This does not switch your open editor or stop its audio.
2. Enter **Add artist** to create a named artist, or choose an existing performer in **Artist / performer**. The default is explicitly **Unresolved artist — choose one**. Optional additional performers are in a separate expandable control. **Leave artist unknown** clears both selections.
3. Enter **Add a different work** for a new song, or choose an existing **Musical work**. Choose the same work for two takes, versions or excerpts of one song. Give each recording an optional **Take / version** label.
4. Choose its **Primary analysis edition**. Model variants remain under one source recording and never become additional songs.
5. Click **Preview count changes**, then **Save associations**. Preview writes nothing. Existing titles/artist metadata are shown as unconfirmed suggestions and are never automatically accepted.
6. Use the dialog's **Recording** selector to associate another recording with the same artist/work or a different work. Choose **Unresolved work** if you do not know the relationship.

The sidebar displays confirmed artist/work associations, take labels and unresolved identities. Search includes the work title and take. Artist filters may also offer legacy metadata explicitly labeled **unconfirmed metadata**; that is a browsing aid, not a confirmed association.

In Artist Patterns / Research, corpus counts distinguish recordings, confirmed works and unresolved works. Known works aggregate across their recordings; unresolved recordings remain separate provisional units. Statistical support remains exploratory, and performer credit does not establish who composed the melody.

## Reproducible input snapshots

Select recordings using the existing corpus controls. In the association dialog, expand **Pin reproducible input snapshot** and save the selected input. This uses each recording's catalog primary analysis, one edition per source, including its current working correction. It pins notes, model/configuration, source hash/availability, catalog identities, supplied musical context, section revision and beat-grid revision. It never copies section timing between recordings.

Snapshots are immutable and readable through `corpus-get`; future association, correction or grid changes do not alter them. A snapshot is an analysis input record, not a human transcription verification. Human references retain their existing independent selection/review workflow. This M0 interface does not make human references the default corpus edition.

Research material is excluded from ordinary snapshots. Explicit research-corpus inclusion creates a research-purpose snapshot; it does not turn Vocadito into a singer's catalog. Audio redistribution permission is recorded as unknown, never inferred from import.

## Storage and compatibility

- Catalog authority: `outputs/melodic-intelligence/catalog/current.json` and immutable `catalog/revisions/`.
- Snapshot authority: `outputs/melodic-intelligence/corpora/<content-id>.json`.
- Recording IDs are deterministic UUIDs from content hashes; artist/work IDs are independent UUIDs created only through explicit reconciliation. Edition IDs hash source, analysis/prediction, correction, notes and model/configuration.
- Legacy reports are read without migration writes. Current corrections are projected in memory when an older analysis is opened; explicit correction saves retain the existing persistence workflow.
- Stale catalog revisions reject a save; reload the association dialog and review before saving again. Existing entities/revisions are not destructively merged or deleted.

M0 does not infer duplicate encodings, covers or excerpt offsets. Different files remain different recordings until the user associates their work. Catalog-wide motif discovery, family clustering and fingerprints belong to later milestones. No M1 functionality is added here.

### Comparing sections after catalog association

The 2026-11-06 integration fix makes section comparison read the saved catalog artist/work identities instead of requiring matching legacy artist text. Unknown or different artists do not block an explicitly selected recording comparison; the result labels the attribution limitation and makes no artist-style claim. Multiple takes aggregate by work ID. If the chosen section type has no saved labels, the comparison explains how to label passages in Study Song. For an immediate comparison without section labels, use **Explore melodic relationships → Find related passages**.

Fix verification: 112 Python regressions and 18 focused browser checks passed at both desktop sizes, including original-audio signal checks. The actual two personal recordings displayed their saved chorus sections and comparison rolls without the artist error. All 800 protected existing audio/data/result files retained their hashes. [Actual comparison screenshot](catalog/section-comparison-fixed.png).

## Verification

See `docs/catalog/` for actual-library screenshots/checks. Unit tests cover migration dry runs, unknown identities, multiple takes/works, model deduplication, stale/foreign identifiers, research exclusion, immutable source/context snapshots, work-title collisions and read-only correction projection. Browser tests use disposable recordings for edits and actual audio-signal checks; the user's two personal recordings are inspected read-only.
