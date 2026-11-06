# Melodic Intelligence Roadmap

Approved architecture · M0 implemented 2026-11-05 · planning baseline `0cbf286`

Includes the **Intelligent Melody Variation Studio** addendum. The original roadmap was prepared without application changes. M0 has subsequently been implemented as documented in §15; all later milestones remain planned. Existing source recordings, human annotation revisions, saved compositions and frozen scientific results remain preserved.

## 1. Decision and implementation direction

Extend the existing melodic-identity service into a collection-level discovery system. Preserve its pairwise traceback and audible comparison as the detailed view inside a **Pattern Atlas**, rather than creating another independent matching system. A persistent motif family, with versioned membership and source-backed occurrences, becomes the primary navigation unit.

The learning journey remains:

**Discover → inspect all occurrences → hear and understand variation → experiment on your own motif → save an original idea.**

Recommended delivery order:

1. Establish explicit song/work, artist and recording identities; pin analysis and musical-context editions.
2. Extend retrieval and validation, then implement conservative family grouping and full discovery accounting.
3. Deliver a family-by-song atlas and multi-occurrence variation explorer, reusing the working pair view.
4. Add section-conditioned relationships and quality-gated melodic fingerprints.
5. Deliver the independent Variation Studio MVP: explicit selections, formal transformations, candidate previews, partial acceptance, MIDI exchange and versions. Its foundational work can begin after step 1; it does **not** depend on artist data.
6. Connect validated fingerprints to optional, evidence-linked composer suggestions; then enable multi-artist references.
7. Pursue the Hit Melody Observatory as a separately gated research milestone.
8. Consider learned retrieval only if it measurably improves a frozen, interpretable baseline.

This order prioritizes the atlas while allowing useful composition tools before a large catalog exists. No new transcription model or framework rewrite is needed for the first releases.

## 2. Repository capability audit

### 2.1 Evidence inspected and verification scope

Inspected README and the technical, model, evaluation, real-vocal, annotation-editor, learning, transport, section/beat and melodic-identity documentation; relevant Python services, JavaScript editors/audio, tests and evaluation tools. Particularly relevant prior plans are [Melodic Identity](MELODIC_IDENTITY_IMPLEMENTATION_PLAN.md) and [Section/Beat](SECTION_BEAT_IMPLEMENTATION_PLAN.md). This roadmap extends their delivered increments, not their aspirational feature lists.

The recorded baseline in [identity usage](MELODIC_IDENTITY_USAGE.md) is **102 Python, 11 JavaScript and 112 browser checks passing**, including two desktop sizes. The stored [symbolic pilot](identity/symbolic-validation.json) reports 40/40 retrieval and 1.000 correspondence P/R/F1 for each of transposition, uniform tempo scaling and single inserted-target tests; 0/40 random negative pairs and 4/40 pitch-permuted controls returned candidates. The code and stored numbers were inspected; these suites were **not rerun or regenerated during this planning task**. The pilot has no independent heldout or human relevance labels. Its approximately 0.23-second runtime concerns tiny symbolic cases, not catalogs.

The previous real-app capture found 11 candidates between two personal recordings and nonzero vocal-bus audio for both. That is a functional demonstration, not confirmed common singer identity, distinct musical works, artist specificity, or human agreement about the matches. [Real-vocal validation](REAL_VOCAL_VALIDATION.md) independently documents limited, annotation-dependent transcription accuracy on eight Vocadito recordings. Those reference editions and heldout splits must stay frozen and outside ordinary artist collections.

### 2.2 Reuse and extension map

| Existing component | Implemented behavior to reuse | Required extension / limitation |
|---|---|---|
| `src/schema.py`, `pipeline.py`, `pitch.py`, `transcription.py`, `note_models.py` | Fractional MIDI pitches, original-source seconds, note IDs, continuous F0, model/configuration provenance and exports | Keep transcription unchanged. A note ID is unique within an edition, not globally; add composite references in derived analysis. Existing monophonic note validation rejects overlaps. |
| `references.py`, `storage.py`, editor persistence tests | Independent references, raw predictions and working corrections; revision guards; atomic JSON writes | Pattern relevance reviews need their own revisions. Never promote pattern approval into transcription attestation. |
| `library.py` | Source-hash grouping, deterministic preferred analysis, source-category checks, research exclusion | No authoritative work/song/performer catalog. Artist/title strings can collide; different encodings or excerpts have different hashes. Hash equality is sufficient for exact-file deduplication, not work identity. |
| `musical_context.py`, `web/context.js` | Independent source-timed sections and fixed-tempo grids, confirmations/validity spans, meter, subdivisions and swing; metronome UI | Reuse revisions and grid conversion. Add queryable section/context associations and uncertainty bounds. Variable tempo and automatic alignment are not delivered. |
| `features.py:analyze_notes` | Real-event intervals, directions, transitions, leaps, duration/IOI/rest measurements, phrase range/density/peak, supplied tonal/chord relationships | Extract scope-specific, versioned features with denominators; do not infer harmony. Tie peaks and clipped phrase boundaries need explicit policies. Acoustic expression remains separate from composition. |
| `motifs.py` | Relative interval/log-duration representations; scalar edit distance; within-song candidates; elementary transformation labels and resemblance screening | Within-song search considers at most 180 windows and returns 20 families. Corpus search considers first 100 qualifying whole phrases, groups greedily around a seed and compares song strings. It is genuine cross-song code, but lacks reliable catalog identity, family validation and note traceback. |
| `melodic_identity.py:align/compare` | Local alignment across two recordings; transposition hypotheses, event traceback, gaps, changed pitches, relative timing measurements, source/context snapshots | Best reusable pairwise foundation; bounds, completeness, scoring and family issues below. |
| `corpus.py:profile_artist` | Hash deduplication, recording-within-song averaging, equal-song statistics, exceptions, bootstrap descriptions and optional reference differences | Song grouping uses artist/title strings. Section summaries use report-level legacy section metadata rather than all saved section occurrences. No fingerprint distribution service or artist distinctiveness calibration. |
| `workspace.py` | `identity-compare`, `identity-study`, `section-compare`, snapshotting under lock then pair matching outside lock; localhost APIs | Retain compatibility. Move catalog-scale work to resumable jobs; page result metadata rather than shipping full catalogs. Avoid long work inside the general dispatch lock. |
| `web/artist-identity.js` | Two-source selection, correspondence highlights, normalized rolls, original A/B playback, learning handoff | Currently one active candidate from a short list, not an atlas. Normalized time is elapsed passage percentage, not confirmed beats. Source B is pinned but composer listening uses A. |
| `web/learning-roll.js`, `editor-core.js`, `editor.js` | Draw, select/Shift-select, move, resize, delete, undo/redo, keyboard pitch references, source-time editing and shared viewport behavior | Add typed selection regions, candidate ghost layers and scalable rendering. Reuse core split/merge primitives where appropriate; do not duplicate annotation workflows. |
| `web/audition.js`, `web/context.js`, transport tests | Shared original-vocal and piano buses, source-based segments, sequence playback, context pause/resume, metronome | Reuse one audio owner. Add candidate/occurrence session keys, lazy loading and tempo-aware preview transport; avoid one player per atlas row. |
| `learning.py`, `learning_store.py` | Source-backed studies/techniques, own-note transformations, independent idea revisions, basic musical checks, MIDI/CSV export | Add explicit motif/answer regions, multi-source reference snapshots and transactional variation patches. Details in §9. |
| `composition.py`, `generator.py` | Existing constrained/legacy generation, scale definitions and resemblance guardrails | Reuse validated primitives and configuration where suitable. Do not rewrite or retune existing generation as a prerequisite. New variation operations have separate versioned contracts. |
| `import_jobs.py`, `web/imports.js` | Durable upload/job status, idempotent submission and interrupted-state reporting | Reuse lifecycle conventions for discovery; do not couple catalog jobs to model inference or block upload progress. |

### 2.3 Pairwise algorithm: important implementation facts

`event-local-v1` evaluates eight frequent constant-transposition hypotheses using local dynamic programming with a linear gap penalty. It requires at least four matched targets and excludes uniform matched interval patterns. The pitch/duration cost uses **raw duration ratios during alignment**; elapsed-onset normalization and tempo-adjusted duration diagnostics occur afterward. Its simple tempo pilot therefore does not establish general tempo invariance.

Search uses rest-delimited phrases, 96-note overlapping chunks with stride 64, and at most 24 chunks per side. Each chunk pair contributes one best alignment. Candidates pass strength/pitch-residual gates, overlapping pairs are suppressed, and only the first 12 selected candidates are returned. The `truncated` flag covers excess input chunks, **not** losses from the final 12-result limit, single-path extraction or overlap suppression. This cannot satisfy “show all discovered patterns.”

Confidence information is displayed but is not a calibrated probability of correspondence. Quality is not a robust reliability term in matching. There are no independent rhythm-only or contour-family retrieval paths, multi-path ambiguity, affine gaps, formal inversion detection, stable family identities, catalog-scale jobs or human relevance review records. Section annotations label evidence but do not filter the pair search. Rejecting equal source hashes does not prove that two other files are different songs.

### 2.4 Composition audit for the addendum

`learning.py:develop_idea` accepts the **whole idea**, not selected IDs or a region. It returns three deterministic options: alternating duration shortening; a nearest allowed changed final pitch; and a repeated/compressed whole idea with a modified answer ending. It does not generate five diverse constrained alternatives. `assess_idea` splits the note list in half to compare motif and answer, so unequal phrases, introductory notes, arbitrary selections and appended codas are misrepresented.

`web/learning.js:develop` auditions candidates and commits the entire returned note array. There is no partial acceptance, ghost-note staging, branch graph, region-aware copy/paste or MIDI import endpoint. `LearningRoll.selected` and shared move/resize/history are reusable, but blank Select mode is not a marquee implementation. Editing bounds currently use the **visible viewport** in several calls (`commit`, move, resize), which must be separated from whole-composition edit bounds before long arrangements or zoomed editing are safe.

Ideas currently allow at most 200 monophonic notes and 1–16 bars via configuration. Save revisions preserve parent IDs and reject stale saves, but UI undo stores note arrays only, not complete tempo/region/configuration transactions. Export rounds pitches to integers and uses velocity 85 (`pipeline.py:export_notes`); it does not preserve arbitrary imported MIDI performance/controller data. The installed lock includes `pretty_midi` and transitive `mido`, but this does not mean full MIDI interchange is implemented.

Current resemblance checking is a bounded equal-length interval/duration window comparison. Idea links retain both identity examples, but the assessment receives the study's source-note array (A); it does not search every selected reference occurrence. These limitations need explicit tests and versioned extensions, not inflated originality claims.

## 3. Evidence and identity contracts

### 3.1 Keep these claim types separate

| Claim type | Minimum evidence and wording |
|---|---|
| Measured property | Named input edition, algorithm, units, source span and uncertainty; e.g. first peak occurs at a measured fraction. |
| Candidate similarity | Retrieval/alignment evidence and component distances; “candidate related passages.” |
| Human-confirmed resemblance | Explicit review author/date/scope; retain disagreement and uncertain judgments. It does not certify transcription. |
| Catalog tendency | Repeated observations with distinct-song support and sampling description; two songs remain exploratory. |
| Distinctive relative to a corpus | Adequate matched comparison corpus, effect size, uncertainty and heldout robustness; never inferred from coverage alone. |
| Popularity association | Prespecified outcome/cohort, controls, statistical evaluation and limitations. |
| Musical interpretation / suggestion | Clearly marked listening interpretation or optional experiment, not a measured cause of emotion or success. |

No single “artist DNA percentage.” “DNA” may be a friendly reference-library label, but API/data terminology should say **measured reference features**. Vocalist, composer, co-writer and arranger are different roles; attribution to a performer does not establish who authored a melodic choice.

### 3.2 Catalog entities

Add a catalog sidecar without rewriting existing reports:

- `Artist`: stable UUID, display name/aliases, optional external IDs, roles, user-confirmation provenance. Multiple performers can relate to one recording.
- `SongWork`: stable UUID for the musical work, title/aliases, credited creators when known; dates/genre/era/market are sourced metadata, not filename guesses.
- `Recording`: stable UUID, immutable content hash, optional song/work relation, performer relations, take/version, source category, recording date, rights record. A song may have several performances and files.
- `SourceRelation`: exact duplicate, derived stem, excerpt, alternate take, cover or uncertain association. Store asserted mapping/offset only when established; never transfer section times between different files by title alone.
- `AnalysisEdition`: source hash + analysis/prediction ID + correction or explicitly chosen reference revision + note fingerprint + model/configuration. A corpus selects one primary edition per recording; alternate editions are sensitivity comparisons, not extra support.
- `SectionOccurrence`: reuse source hash, section ID/revision, type, user label, ordinal and source bounds. “Chorus 2” is distinct from “chorus” as a type. Unlabeled spans remain searchable as unknown.
- `PhraseView`: derived edition ID + event IDs + segmentation configuration; phrases are not sections. A phrase may cross a section boundary and an occurrence can overlap multiple sections.
- `CorpusRevision`: explicit ordered membership, purpose, primary-edition policy, inclusion/exclusion reasons, catalog revision and selection snapshot.

External identifiers can assist linking; do not require them. [MusicBrainz](https://musicbrainz.org/doc/About/Data_License) offers CC0 core metadata, while supplementary data has different, noncommercial/share-alike terms. Import field provenance and licensing separately; metadata does not license recordings.

Migration: existing source-hash groups become provisional recordings; title/artist strings become suggestions, not confirmed work merges. Offer a non-destructive “same song / different performance / different song / unresolved” reconciliation UI. Keep unresolved recordings analyzable, but report recording support separately and withhold verified distinct-song/artist counts. No automatic human labels for the current two recordings.

### 3.3 Independence and weighting

Choose one preferred performance per work for the default artist summary, or explicitly average multiple recordings **within work**. Different model editions, overlapping excerpts, stems, remasters, repeated choruses and covers do not become independent songs. For cross-artist research, track shared works/covers and co-credited artists as leakage groups. A multi-artist recording must not receive duplicated aggregate weight merely because it appears under two artists.

Research recordings remain excluded by default. Purpose-tagged research corpora require explicit selection and remain visibly distinct from personal artist libraries. Cross-artist collections are valid when explicitly selected; a mixed selection must not silently become one singer's profile.

## 4. Proposed architecture, storage and APIs

### 4.1 Processing graph

```text
Existing reports + corrections/references + source audio (read-only inputs)
    + catalog revision + section/grid/harmony revisions
                         ↓
              immutable CorpusSnapshot
                         ↓
          per-edition event/phrase representations
                         ↓
       candidate index → detailed pair alignments
                         ↓
        occurrence deduplication → conservative families
                         ↓
         coverage manifest + family revisions + reviews
                ↙                   ↘
         Atlas / Explorer       Fingerprint summaries
                ↘                   ↙
             source-backed technique contracts
                         ↓
            existing Create Melody workspace
       own-note selection → preview patches → acceptance
```

The Hit Observatory consumes frozen corpus/features/outcome snapshots in an isolated research path. Outcome labels must never affect ordinary matching or leak into unsupervised feature selection in an evaluation fold.

### 4.2 Derived schema proposals

Use explicit `format`, `schema_version`, algorithm/configuration hash and timebase on every artifact. Validate finite values, source ownership and parent revisions. Unknown future formats should fail readably rather than be silently rewritten.

| Record | Required contents |
|---|---|
| `CorpusSnapshot` | Corpus/catalog revision; resolved work/artist/recording IDs; selected editions; complete note and context fingerprints; source availability; exclusions; rights; snapshot ID |
| `Occurrence` | Stable occurrence ID; edition and source hash; composite note refs `(edition_id, note_id)`; original start/end; phrase refs; section overlaps and containment; boundary-censor flags; representation version; quality fields |
| `Alignment` | Pair of occurrence versions; parameters; estimated transposition/time scale; operation list; per-operation residuals; coverage; ambiguity; available/missing feature channels; status and warnings |
| `FamilyRevision` | Persistent family UUID; immutable revision; typed level; representative occurrence; member versions; direct alignment refs; invariants/variation distributions; support by work/recording/section; clustering parameters; previous revision and lineage |
| `PatternReview` | Family/occurrence/alignment revision being reviewed; accepted/rejected/uncertain; reviewer/date; reason and optional musical comment; no reference-annotation attestation |
| `DiscoveryRun` | Input snapshot, code/configuration versions, seed, stages/timing/resources; candidate counts; complete/partial/failed partitions; exhaustive/indexed mode; thresholds and exclusions |
| `CoverageCell` | Family/run/song scope; applicable section filter; eligible spans; completed/excluded/unavailable spans; occurrence IDs; detection and review states separately |
| `Fingerprint` | Scope/membership snapshot; feature/unit/timebase; per-song contributions; weight policy; distributions/representatives; missingness; confidence method; limitations |
| `TechniqueContract` | Principle, evidence occurrence/alignment/fingerprint revisions, applicability, measurable constraints, editable dimensions, source links; no source-note template |
| `Outcome/Cohort` | Provider, observation/release dates, market, outcome horizon, censoring, eligibility, matching rules, rights, split IDs and label availability |

Pattern UUIDs must not be hashes of the entire current member list: adding a song would otherwise break bookmarks. Immutable revisions can be content-hashed. Use deterministic sorted discovery and a versioned reconciliation policy to preserve UUIDs when membership strongly overlaps; ambiguous merges/splits produce new families with `derived_from` lineage. Keep historical family revisions and user reviews attached to the reviewed version. A new representative requires new direct alignments; never pretend old note-to-representative links still apply.

### 4.3 Persistence approach

Keep existing JSON stores and immutable runs intact. Add `outputs/melodic-intelligence/` with catalog/corpus revisions, job manifests, feature shards, alignments, family revisions, reviews, fingerprints and research manifests. Reuse atomic writes and optimistic revision guards. Store each source snapshot once, referenced by alignments, rather than copying a full song into every pair/family.

Use standard-library SQLite as a **rebuildable query index** for source identities, occurrence/section intersections, family membership and atlas cells. The versioned artifacts remain the authority. This avoids loading every JSON report for each request. Schema migration is additive/transactional; index rebuild must reproduce membership/counts. Do not migrate existing annotation, audio or composition stores into a new database.

Workers snapshot inputs under a short lock, compute outside it and publish an immutable run atomically. Jobs have queued/running/partial/complete/cancelled/failed/interrupted states, stage progress, resumable partition checkpoints and actionable errors. A cancelled job keeps valid completed partitions; it must not report missing matches as absence. Reuse `ImportJobs` conventions, not its inference queue itself. A bounded worker process is preferable to unrestricted Python threads for CPU-heavy alignment on Windows; start with one worker and explicit cancellation checkpoints.

### 4.4 API changes

Keep existing `identity-compare`, `identity-study`, context and idea actions compatible. Add actions routed through the current server rather than a second backend:

- `catalog-get`, `catalog-reconcile`, `corpus-save/get`: revision-guarded identity/membership operations with preview of count changes.
- `atlas-start/status/cancel/resume`: returns job ID promptly; progress identifies analyzed source partitions.
- `atlas-families`: cursor pagination, filters/sort, total qualifying family count, coverage summary and snapshot ID.
- `atlas-cells`: visible song/family ranges only; sparse cells plus explicit coverage states.
- `family-get/occurrences`, `alignment-get`, `pattern-review-save`: immutable revision reads and separate user review writes.
- `fingerprint-build/get/compare`: precise scope, units, weighting and feature eligibility.
- `technique-from-family`: contract and exact evidence refs consumed by existing learning handoff.
- `variation-propose/preview/apply`, `idea-branch`, `idea-region-save`, `idea-midi-inspect/import`: detailed contracts in §9.
- `cohort-validate`, `observatory-run/get`: separate research namespace/purpose gate; no implicit network acquisition.

Reject inconsistent snapshot IDs, cross-source note references, stale base revisions and out-of-bounds spans. Pagination must use a stable sort and snapshot so results do not repeat/disappear during incremental computation. Public responses return logical asset IDs, not arbitrary filesystem paths; preserve current localhost/origin checks and upload limits.

## 5. Musical representations and matching

### 5.1 Multiple representations, not one universal distance

Keep raw events untouched. Derive these views with missing-data masks:

| Channel | Representation | Valid comparisons |
|---|---|---|
| Target melody | Fractional pitches, consecutive signed intervals; pitch relative to anchor/robust center | Exact/transposed targets and interval variations; preserve octave information |
| Contour | Direction sequence with declared tolerance; range-scaled target contour; peak/turning positions | Broad shape, explicitly not exact motif identity |
| Rhythm in seconds | Durations, IOIs and rests; log ratios normalized by robust local scale | Relative rhythm without a beat claim; distinguish held duration from onset spacing |
| Rhythm in beats | Onset/offset quarter positions, meter phase, subdivisions, swing setting, residuals | Only within confirmed grid validity; beat and bar phase remain separate |
| Phrase construction | Target count, span, density trajectory, all tied peak spans, opening/ending, rest context | Structural gesture families and phrase contrasts |
| Section/transition | Section type/occurrence and adjacent-section pair; relative position and within-song deltas | Chorus comparisons, verse/chorus contrasts, pre-chorus→chorus transitions |
| Tonal/harmonic | Supplied key/mode/tonic, scale degrees, chord spans and certainty | Scale/chord-conditioned comparisons only where context is available |

Represent a clipped boundary note as a full source event plus intersection/censor flags. Do not create a new attack at the region start or use a clipped held duration as complete rhythmic evidence. Use half-open spans and a declared attack-in-region policy; preserve ties/carryovers in display. Rest-delimited phrases are a useful candidate source, not definitive compositional phrase annotations.

Time transforms remain invertible display/analysis mappings. Source seconds `t` never change. Current fixed grid gives quarter position `q=(t-origin)*BPM*unit/60`; a bar has `numerator*4/denominator` quarters. Keep original `q`, local `q-q_start`, beat phase and bar phase, including pickups/negative positions. Elapsed fraction `u=(t-start)/(end-start)` is a different representation. Tempo normalization may preserve rhythmic ratios while erasing placement; phase-dependent claims require the original beat coordinates.

### 5.2 Retrieval pipeline

1. Enumerate full phrases, multi-resolution note windows and section-transition windows. Deduplicate identical event spans. Initial motif lengths can be 4–16 targets with longer phrase candidates; expose length/stride/coverage policy in the manifest. Shorter fragments remain a separately labeled exploratory search, not forced into strong motif families.
2. Generate candidates through several interpretable indexes: interval shingles, contour shingles, normalized IOI/rest signatures and phrase-feature neighborhoods. Section filters constrain searches only when requested. Unlabeled material participates in all-sections mode.
3. Validate candidates with the reusable pair engine, versioned as a new matcher. Retain the old comparator for regression/replay. Add affine gaps, explicit reliable coverage, robust time-scale hypotheses **before** rhythm scoring, and multiple nonredundant local paths per candidate pair.
4. Add rhythm-only and structural aligners as typed channels. A rhythm family can contain different pitch patterns. Do not silently relax melodic gates until an unrelated contour passes as a target motif.
5. Deduplicate overlapping occurrences by composite event overlap and containment, while preserving meaningful nested motifs as parent/fragment relations. Do not suppress every overlap globally.
6. Persist all qualifying candidates/occurrences before ranking and group them conservatively (§6). Ranking controls order, not existence.

For small catalogs, use exhaustive eligible window comparisons as the correctness reference. For larger catalogs, indexed retrieval reduces cost but cannot promise exhaustive discovery. Report candidate-generation recall against exhaustive subsets and offer an explicit thorough job. All discovered results must remain accessible even when search coverage is bounded.

### 5.3 Alignment and scoring contract

For target alignment, estimate constant transposition `delta` from reliable pitch offsets; compare `pB-pA-delta`. For rhythm, estimate positive scale `s` from matched onset spacings, robustly excluding zero IOIs/outliers, and compare `log(dB/(s*dA))`, normalized IOIs and rests separately. Reject ill-conditioned estimates instead of returning a confident scale. Keep raw residuals in semitones and milliseconds/beats.

An alignment substitution cost may combine clipped pitch residual, interval-consistency, IOI and duration/rest costs with versioned weights. Affine insertion/deletion penalties distinguish one ornament run from several unrelated gaps. Report each cost/coverage component; fit thresholds only on development data. Missing rhythm/harmony must produce a different availability mask and validated gate, not a score that improves because a term vanished.

Confidence must not allow uncertain notes to yield a high score merely by contributing little penalty. Require minimum effective reliable matched coverage, report low-confidence and unavailable confidence separately, and show model-edition sensitivity. These are quality indicators, not probabilities. Never silently “fix” suspected octave errors in the source notes for matching; a robustness hypothesis must be labeled and compared against the original result.

Retain plausible alternative paths when costs are close. Mark ambiguous links, especially repeated pitches. Direct event matching is normally one-to-one with gaps. Optional repeat/sustain equivalence needs explicit grouped event links (one-to-many) and its own tests; do not collapse rearticulations in the canonical melody.

Musically informed sequence alignment is supported by [van Kranenburg et al., 2009](https://webspace.science.uu.nl/~veltk101/publications/art/ismir09-kranenburg.pdf); its folk-song results do not establish accuracy on modern vocal transcriptions. [Subsequence DTW](https://www.audiolabs-erlangen.de/resources/MIR/FMP/C7/C7S2_SubsequenceDTW.html) is useful for contour/time-warped retrieval, but a many-to-one warp is not automatically note correspondence. Use it for shape candidates, then a separate event alignment if note links are shown.

### 5.4 Transformation explanations

| Label | Evidence required |
|---|---|
| Exact / transposed recurrence | Event order and rhythm agree within declared tolerances; transposed case additionally has consistent nonzero pitch offset |
| Rhythmic variation | Reliable matched targets with changed duration/IOI/rest residuals after uniform scaling; show which changed |
| Changed interval | Consecutive mapped targets have a residual interval change beyond tolerance; a uniform transposition is not a changed interval |
| Altered ending | Supported shared opening plus observed divergent terminal context; local alignment truncation alone is insufficient |
| Ornamentation candidate | Short inserted/deleted run surrounding preserved anchors; display alternative explanation of transcription fragmentation/missed attacks |
| Repetition / expansion | Explicit repeated subspan or additional mapped material; longer file duration alone is insufficient |
| Fragmentation | Shorter occurrence maps to a coherent subsection of a longer family member; show lost context and coverage |
| Inversion candidate | Matched interval signs reverse consistently; fit pitch reflection and report residuals, coverage and exceptions |
| Rhythmic displacement | Similar beat-normalized pattern with systematic phase shift on confirmed compatible meters; elapsed-time offset alone is not evidence |
| Phrase compression / expansion | Consistent relative scaling of phrase/IOI structure; separate uniform tempo change from added material or changed rests |

Labels can co-occur, carry uncertainty and remain relative to a named member. Human review can dispute a label without altering the source notes.

## 6. Corpus-wide families and the all-pattern requirement

### 6.1 Family levels

Use typed families: exact/transposed target motif; varied motif; contour/phrase gesture; rhythmic vocabulary; section construction/transition. Artist tendency is an aggregate claim over these, not another pair match. A family may occur in several section types and may have both within-song and cross-song occurrences. Require at least two **resolved distinct works** for a cross-song label. One-song families stay useful. Generic rising scales remain accessible as conventional shape/rhythm observations, not distinctive artist signatures.

### 6.2 Avoid nontransitive chaining

Do not use connected components or single-link clustering as motif identity. A–B and B–C edges do not justify A–C membership.

Baseline: deterministic agglomerative grouping with a representative medoid and a complete-link compatibility gate within a family type. Each proposed merge must have adequate pair coverage and distances below the type-specific limits for every member pair; missing comparisons are unresolved, not compatible. Use symmetric compatibility (both directed subsequence coverage checks where needed). This is conservative and may split a broad family: retain a separate “related families” graph rather than merging through a bridge.

For larger groups, medoid/prototype screening can avoid obvious rejects, but full validation is required before a strict family label. A cheaper prototype-only group must be labeled provisional and must disclose untested member pairs. Optional multi-prototype families are a later validated alternative, with subfamilies and bounded diameter, not unrestricted chaining. A fragment can have overlapping candidate memberships; do not force all occurrences into a single partition.

Align each occurrence directly to the representative. Never compose A→B→C maps and present them as observed A→C correspondences. A representative is an actual occurrence, not an averaged invented melody. Changing representatives preserves prior alignments in history.

### 6.3 Coverage semantics and stable access

Atlas rows are families; columns are songs, expandable into recordings/sections. A cell can hold several occurrence links. Detection state and review state are separate:

- **Detected:** candidate occurrences exist; show total/reviewed/uncertain/rejected counts.
- **Not detected in completed scope:** eligible material was searched under a named version/configuration with no qualifying occurrence; not proof of absence.
- **Partially analyzed:** include searched/eligible spans and reasons for skipped work.
- **Not analyzed:** queued, never requested, cancelled before this partition or excluded by the search policy.
- **Unavailable:** missing audio/notes, unsupported edition or invalid context; explain which channel is unavailable. Missing beat data must not make melodic analysis unavailable.
- **Not applicable to filter:** e.g. no annotated chorus, distinct from a searched chorus with no match.

Show all discovered families through server pagination and virtualization, including unreviewed and rejected families via explicit filters. A default high-evidence sort may prioritize results but must state “showing X of Y”; no silent top-12/top-20 storage or UI cutoff. Save search policy, omitted partitions and coverage. The promise is **all discoveries made by the declared search**, not all conceivable musical patterns.

Rank with separately visible attributes: distinct-song coverage, within-song recurrence, evidence quality, transformation diversity, section position/coverage and reference-relative specificity. “Structural importance” is an operational proxy (e.g. repeated section entry or peak-bearing phrase), not a measurement of emotional value. Avoid rewarding many overlapping windows, repeated choruses or more model runs.

Specificity is unavailable without a suitable comparison corpus. Later estimate song-level prevalence differences/log odds with shrinkage and uncertainty, matched for relevant context. Call it specificity **relative to the named corpus**, not universal uniqueness. Generic interval/contour hard negatives must be part of ranking evaluation.

## 7. Fingerprint Engine

### 7.1 Feature families

- **Contour:** target-based and optional expressive-F0 views separately; anchor/median-subtracted pitch, optional range normalization, normalized time, turning points, tied peak regions and ending position. Show individual curves, medoids and contour clusters. Mask rests and uncertain intervals rather than interpolating a melody through silence. Explain whether displayed bands are empirical quantiles or confidence intervals; avoid a mean curve as the artist's “melody.”
- **Intervals:** event-weighted and duration-weighted views explicitly distinguished; signed step/leap bins, direction changes, repeated pitches, interval pairs/triples and leap-recovery sequences. Fractional targets retain precision; bin tolerances are documented. Report transition denominators and phrase-boundary policy.
- **Rhythm:** confirmed beat-phase distributions, meter-conditioned onset patterns, durations/rests in quarters, cross-beat/bar holds, phrase entries/endings and repeated rhythmic cells. Show timing residuals rather than quantizing. Treat syncopation as a defined meter-dependent index/candidate, not every offbeat onset.
- **Phrase construction:** targets, spans, range, relative register, density changes, peak locations, opening/ending and motif/answer relations. Seconds remain available when beat lengths are unavailable. Phrase segmentation sensitivity accompanies comparisons.
- **Sections:** per-occurrence distributions and within-song paired contrasts; separate Chorus 1/2 recurrence from chorus patterns across works. Transition analysis uses adjacent labeled sections, not arbitrary pairings; report missing intervening material.
- **Harmony:** supplied key/mode/chord maps with source/validity. Degree and chord-membership patterns, non-chord connection/resolution candidates; exclude unsupported tonal spans. Isolated vocals do not provide trustworthy chord functions automatically.

### 7.2 Aggregation and uncertainty

Compute phrase/occurrence features first, then section-occurrence summaries, recording summaries and song-level summaries. Default song-conditioned artist features are `mean_s(f_s)` over eligible unique songs, where each `f_s` already averages its eligible occurrences/recordings under the declared policy. For a distribution, normalize within song before averaging bin probabilities. Show raw note/phrase/section/recording counts alongside the number of independent songs; do not conflate them.

For selected artists offer **equal-artist** and **equal-song** aggregation with explicit labels. Preserve cohort composition by genre/era/market. Compare verse→chorus changes within song before aggregating those differences. Report eligibility denominators per feature: a song lacking confirmed beats contributes neither a rhythm zero nor a downbeat-negative example.

Use deterministic song-cluster bootstrap for sufficiently supported descriptive summaries; artist-cluster resampling for population comparisons across artists. Do not resample notes as independent observations. With two songs show both values/range and an exploratory label, not a convincing population interval. A minimum count alone cannot establish representativeness. Record convenience sampling, performance/annotation uncertainty and missingness.

Perturb source timings/pitches within declared error bounds and vary grid origin/BPM within user-supplied alignment uncertainty to report sensitivity ranges. These are **sensitivity analyses**, not probabilistic confidence intervals unless uncertainty distributions are justified. Repeat summaries with alternate transcription editions without adding them to the sample count. Keep review status, model agreement and statistical uncertainty as separate fields.

## 8. Interactive workspace architecture

Keep Study Song, Create Melody and Transcription/Research. Evolve Artist Patterns into **Identity Atlas**, with the current statistical view under Advanced. Use existing DOM/CSS and canvas rolls; add no framework solely for this feature.

| Experience | Default working area | Detail / progressive disclosure |
|---|---|---|
| Identity Atlas | Compact corpus picker, section/type/review filters; virtualized family×song matrix with frozen labels and legend | Cell click selects occurrence; family click opens Explorer; Advanced shows search coverage, histograms and ranking components |
| Variation Explorer | Scrollable aligned occurrence rows with source identity, section/time and quick original listening | Pin 2–4 rows for overlays; all others remain accessible; existing pair view for exact operations; compare contour or rhythm separately |
| Fingerprint Lab | Two or more selected scopes, one feature family at a time, distributions/medoids and contribution counts | Click distribution bin/example to hear source; weighting/uncertainty/missingness controls; no walls of tiny statistic cards |
| Hit Observatory | Research cohort/outcome summary and evidence-quality gates | Effect estimates, controls, splits and diagnostics; unavailable with actionable explanation until lawful cohorts exist |
| Style-Aware Composer / Variation Studio | Existing editable roll, compact reference selector, selected-region transform menu, candidate strip | Reference evidence drawer, original/candidate A/B, ghost changes, acceptance controls and branch history |

Matrix controls: search family notes/tags/song/section, filter family level and quality, sort by support/diversity/specificity; “include unreviewed” is visible. Group columns by artist or song collection. Keyboard-accessible table semantics and a list alternative accompany canvas/virtualized cells; status cannot depend on color alone. Keep filters/sort/scroll in UI state, not as altered scientific data.

Explorer rows share chosen pitch/time axes. Transposition-normalized pitch retains a label for the removed offset. Confirmed-beat mode is available only for eligible spans; incompatible meters get a warning and relative-time alternative. Highlight direct mapped targets, gaps and uncertainty; no precise note links on a contour-only relation. Playhead mapping uses each row's own source transform.

Use the shared audio owner for every occurrence: original-source URL plus original seconds, no pitch/tempo normalization applied to source audio by default. A/B pause/resume/loop stays consistent. Repeated clicking, source loading races, tab changes and unavailable files must not leave orphaned audio. Multi-row display does not mean simultaneous playback. Optional synthesized structural comparison may use piano and must be distinctly labeled.

At 1366×768, keep the main roll/matrix visible with one collapsible evidence/candidate drawer. At 1920×1080 allow a wider comparison panel. Preserve selection, composition draft and transport context on navigation; returning from a source example must not replace the user's melody.

## 9. Intelligent Melody Variation Studio

### 9.1 Scope and reusable foundation

Extend **Create Melody**, its `LearningRoll`, `MelodyEdits` and shared `VocalAudition`; do not create a separate MIDI application. The MVP is a capable **monophonic melody** editor with explicit limitations for polyphonic files, not a full multitrack DAW. The first four deliverables—selective transformations, multi-candidate previews, partial acceptance, complete supported MIDI editing/versioning—require no artist catalog.

Introduce `CompositionDocument v2` as a wrapper around existing notes/configuration: document bounds independent of viewport; named sections/phrases; explicit motif and answer regions; tempo/meter map; selection; branches/revision references; import provenance and optional velocity. Keep v1 ideas readable, upgrading in memory and saving v2 only on the user's next explicit edit/save. Source audio/reference stores are untouched.

### 9.2 Selection and boundary semantics

`SelectionSpec` contains base idea revision/content hash, explicit note IDs, optional beat region, selection kind (notes/group/phrase/bar/section), timebase, anchor and boundary policy. Bar selection uses meter, not fixed four-quarter assumptions. Add marquee and range selection, named motif/answer regions, select-all-in-region and accessible keyboard equivalents. Remove the half-list heuristic when explicit regions exist; legacy ideas without regions show “mark motif and answer” rather than an authoritative assessment.

Default: lock all unselected notes. Notes overlapping a region boundary require an explicit policy: include the full note, leave it locked, or split with preview. Do not silently truncate. Noncontiguous selected IDs are permitted for pitch-only changes; time/order operations apply to explicit contiguous groups or require a region selection so intervening locked notes are not reordered accidentally.

Boundary-continuity constraints are optional and inspect both neighbors: maximum incoming/outgoing leap, available rest, positive duration, range/scale and chord compatibility. Hard collision/range violations reject the candidate with reasons. “Fit within selection” is explicit; ripple editing is off by default and only moves outside notes after a clearly previewed user choice. Never silently clamp pitches or compress time to make a formal transform fit.

### 9.3 Formal operations versus creative heuristics

All operations return proposals on the user's own material, with mathematical parameters, preserved IDs and explicit insert/delete ancestry. Use beats for composition timing. Let selection span be `[a,b)`, anchor pitch `c`, and ordered pitches `p_i`.

| Operation | Precise initial contract / limitation |
|---|---|
| Chromatic transposition | `p'_i=p_i+k`, including fractional `k`; timing unchanged. Reject range violations unless user changes constraints. |
| Chromatic inversion | `p'_i=2c-p_i`; anchor chosen by user or first selected target. Applying twice restores pitches if no projection occurs. |
| Diatonic inversion | Map on-scale pitches to unbounded scale-degree indices, reflect index about selected degree, map back. Off-scale pitches need an explicit reject/preserve-accidental/project policy; projection is a separate, labeled edit. |
| Retrograde pitches | Reverse selected pitch order over unchanged ordered timing slots; preserve note-slot IDs and record pitch provenance. It is not full musical retrograde. |
| Retrograde rhythm | Reflect interval slots: `[start,end]→[a+b-end,a+b-start]`, sort resulting slots and assign original pitch order. This reverses durations and internal rests without reversing pitch order. Leading/trailing rests follow the defined region. |
| Full retrograde | Reflect intervals as above while pitches travel with their original events; both order and timing reverse. All variants are named distinctly. |
| Interval expansion/compression | Scale successive signed intervals by positive factor about the selected anchor/first note. Chromatic result may be fractional; scale projection is optional and separately described. |
| Rhythmic augmentation/diminution | `t'=a+s(t-a)` for starts and ends, `s>0`; rests scale too. Fixed-bound selection can reject overflow; no silent ripple. |
| Rhythmic displacement | Add beat offset to starts/ends; preserve durations. Meter-aware phase change is displayed, not interpreted as better groove. |
| Duration change | Scale/set held durations while keeping attacks; enforce nonoverlap and disclose changed rests. Different from time scaling. |
| Contour preservation / reversal | Heuristic constrained pitch search preserving or reversing interval signs with chosen tolerance; not equivalent to exact inversion. |
| Ornament insertion/removal | Heuristic add/remove explicitly selected or proposed short targets with ancestry; protect anchor targets and timing. Short duration alone is not proof of an ornament. |
| Repeated-note variation / sequencing | Split a held target into attacks or repeat selected own motif with pitch/time shifts; distinguish new attacks from tied holds; unique event IDs. |
| Peak relocation / alternative ending | Heuristic changes within the marked region, chosen peak window or ending region; preserve locked notes and show resulting contour. |
| Question and answer | Transform explicit motif region into explicit answer destination; never infer equal halves. Fit/collision policy and response length are user controls. |
| Chord-aware melodic alternatives | Score new target choices against user-supplied chord spans/voice-leading preferences. Changing the chord progression is a separate optional proposal, never an inferred reharmonization of isolated vocals. |

A formal operation need not sound satisfying. Explain operation correctness separately from optional scale/range/continuity preferences. Return no candidate rather than quietly relaxing a hard constraint.

### 9.4 Candidate generation and controllability

Provide musician-facing controls for strength, pitch/rhythm similarity to **their own selection**, comfortable range, key/scale, contour, density, complexity, phrase length, peak position, section and optional chords. Advanced shows seed, budgets, feature weights and exact limits. “Strength” maps to documented edit budgets (targets changed, semitone limits, time shifts, insert/delete limits), not an opaque quality score.

Pipeline: validate selection → enumerate formal/heuristic operation combinations → bounded seeded search → reject hard-constraint violations → assess pitch/rhythm/structure/boundary changes → diversity selection → resemblance check → present alternatives. Return five genuinely distinct candidates when feasible, otherwise fewer with specific constraints preventing more. Use stable tie-breaking and seed/configuration/input hashes. Keep pitch similarity, rhythm similarity, structural fit and reference tendency as separate dimensions; use Pareto/diversity selection rather than a compulsory “best melody.”

Singability checks concern comfortable range, jump size, target density, duration and breath space. They cannot judge artistic quality or individual vocal ability. Optional subjective directions remain user preferences. Constraint feedback is immediate on edited previews and accepted notes.

In theory-only mode, candidates use only the user's notes and formal rules. Reference-guided mode adds distribution/technique constraints from selected fingerprint/family snapshots; never fetch a source phrase as a replacement template. For multi-artist references provide independent weights for contour, rhythm, phrase construction and supported harmony. Normalize weights over eligible references **per dimension**, disclose missing dimensions, and preserve multimodal alternatives rather than averaging incompatible contours. Two-song or low-quality references produce exploratory suggestions.

### 9.5 Non-destructive proposal, preview and acceptance

`VariationProposal` stores ID/version, base document revision and note hash, selection, operation/parameters, seed, locks, optional reference snapshots, candidate note patch, ancestry links, measurements, warnings and explanation. A patch contains added/updated/deleted note IDs plus dependent operation groups. It does not modify the working idea on receipt or audition.

Display original notes and ghost candidates in the same roll; candidate browser shows 3–5 alternatives with compact contour/rhythm thumbnails. Pin one or two for A/B using named transport sessions. A preview is editable on its own working copy; reject clears it. “Apply selected changes” is one undoable transaction. Partial acceptance selects **valid operation groups**, not arbitrary pieces that break note dependencies: insertion plus shortening its neighboring note may need atomic acceptance together. Revalidate locks, collisions, boundaries and reference snapshot on apply.

If the base idea has changed, do not apply stale IDs/times. Offer recompute or an explicit conflict preview. Accepted patches record provenance; undo restores notes, IDs, regions and relevant configuration together. Previewing/rejecting leaves current revision/export unchanged. Merging fragments from several proposals creates a new validated proposal with ancestry, not silent overwrite. Copy into another bar/idea gives new IDs and a relative-beat origin, preserves the original and previews collisions/scale context.

Persist immutable revisions using existing save guards, plus named branches whose heads reference revisions. Restore creates a new revision based on the selected historical one; it does not erase subsequent work. Multi-parent ancestry can describe merged suggestions while each saved state remains independently loadable. Keep editable region changes, tempo and meter in the transaction history, not only the note array.

### 9.6 MIDI and clipboard interoperability

Add local MIDI inspect/import with track/channel selection and a preview. First support Standard MIDI Files type 0/1 with a selected monophonic melody track; reject asynchronous type 2 and unresolved overlaps with clear guidance. Preserve original file bytes/provenance. Read tempo/meter events and PPQ ticks correctly; the editable representation is quarter beats, not seconds computed at one arbitrary BPM. Do not flatten tempo maps silently. Unsupported controllers, sustain interpretation, pitch bends, polyphonic content and SMPTE timing must be enumerated before import; preserve metadata where supported and provide an explicit lossy-import report otherwise.

Reuse installed MIDI libraries: [Mido's file API](https://mido.readthedocs.io/en/stable/files/midi.html) exposes delta ticks and MIDI messages; `pretty_midi` remains suitable for existing simple exports. If importing `mido` directly, declare it explicitly in a future dependency change rather than relying permanently on transitive availability. No installation is needed for planning.

Round-trip guarantees apply to **supported semantic content**, not identical binary encoding: pitch, onset/end within one output tick, velocity, selected-track tempo/meter and intentional rests. Fractional pitches remain exact in the project; MIDI export either explicitly rounds with a report or later supports a validated bend strategy. Do not claim current integer MIDI export preserves microtonal pitch. Default imported velocity is preserved, default drawn notes receive a documented velocity. Unknown data is not silently advertised as retained.

Implement internal copy/paste first (notes, relative beats, selected regions), then optional user-initiated system clipboard text/custom data plus `.mid` export/import. Browser [Clipboard API](https://developer.mozilla.org/en-US/docs/Web/API/Clipboard_API) permissions, user activation and format support vary. Do not promise universal direct paste into arbitrary desktop DAWs; use file exchange as the reliable fallback and never read clipboard contents automatically.

Separate musical tempo changes from audio processing: changing composition BPM changes piano scheduling, not symbolic beat positions or any original vocal file. Support imported tempo maps in the composition scheduler/export before claiming full tempo-map round trips. Reuse the metronome and original-vocal buses with explicit original/candidate/source context. No vocal synthesis or destructive audio pitch processing is required.

### 9.7 Explanations and resemblance

Each candidate answers: what changed, preserved note IDs, before/after intervals/rests/contour/density, formal rule or measured tendency, exact source examples if referenced, boundary effects, adjustable parameters and limitations. An evidence-linked sentence is generated from typed measurements, not a generic claim that an artist “always” writes this way.

Search resemblance against all selected reference occurrences, including both sources of identity handoffs, plus the user's opted-in earlier ideas. Separate own-motif similarity from reference resemblance. Report general convention, broad structural resemblance, close target/rhythm resemblance and exact matches with evidence; absence of a retrieved match is not originality certification. Support graceful “not assessed” when the reference collection is unavailable or search is incomplete. Preserve the existing warning while replacing its single-source coverage limitation through an additive service.

## 10. Hit Melody Observatory: separate research milestone

### 10.1 Research questions and outcome contract

Separate descriptive questions (“what appears in these successful songs?”) from comparative questions (“what differs from comparable songs?”). A hits-only collection can support the former, never the latter. No universal success formula or causal promise is a product output.

Define one primary outcome before extraction/model fitting: e.g. chart entry or weeks above a prespecified rank in the first 12 weeks after release, in a named market/chart with known eligibility. Alternative studies may use licensed first-period streaming counts, sustained popularity at a fixed later horizon, or within-artist success rank. Do not combine these into an unvalidated universal hit score. Capture release/reissue date uncertainty, chart rule changes, platform exposure, missing observations and right-censoring. “Not in this downloaded table” is not automatically “non-hit.”

### 10.2 Candidate sources and actual limitations

Research checked against primary documentation on 2026-11-05. Availability and terms need rechecking before acquisition; no datasets were downloaded for this plan.

| Source | Useful role | Rights / scientific limitations and decision |
|---|---|---|
| User-authorized recordings and original MIDI | Core product demonstration and own-motif tests | Local processing; no automatic redistribution or human ground-truth labels. Two recordings cannot establish specificity/popularity effects. |
| [MTC](https://www.liederenbank.nl/mtc/) annotated folk melodies | Independent melodic-family retrieval evaluation; explicit family partitioning | MTC-ANN provides 360 annotated melodies; CC BY-NC-SA 3.0 terms require a separate research ingestion path. Folk tune families are not pop artist identity or hits. |
| [SALAMI](https://github.com/DDMAL/salami-data-public) | Section boundaries/functions, annotator disagreement and context validation | Annotation data are CC0; the project cannot distribute its audio. Labels are not lead-vocal notes or commercial outcomes; obtain audio rights separately. |
| Existing Vocadito editions | Sensitivity to actual note/F0 transcription errors | Use frozen published editions/splits; no family relevance or hit labels. Never add it to an artist collection implicitly. |
| [FMA](https://github.com/mdeff/fma) | Broader genre/artist material and a possible platform-specific exploratory cohort | Metadata CC BY 4.0; each audio track retains its chosen license. Metadata includes play counts, but snapshot counts without controlled exposure/horizon are not commercial-hit truth. Check each track's permissions. |
| [Lakh MIDI](https://colinraffel.com/projects/lmd/) | Symbolic scaling/robustness tests and possible metadata linkage | Dataset distributed CC BY 4.0, with author-attribution limitations, invalid files and imperfect matches documented. No guaranteed vocal lead, source ownership clearance or popularity outcome. Do not redistribute copyrighted compositions merely because a MIDI dataset is downloadable. |
| [Million Song Dataset paper](https://www.ee.columbia.edu/~dpwe/pubs/BertEWL11-msd.pdf) | Historical features/metadata and linkage research | Feature/metadata corpus is not an isolated-vocal audio or human-note corpus. Coverage, old identifiers and separately licensed linked resources require audit. Its download page returned a fetch error during this review; acquisition is unverified. |
| [MusicBrainz licenses](https://musicbrainz.org/doc/About/Data_License) | Work/recording/artist identity reconciliation and release metadata | Core and supplementary terms differ; no popularity or audio license. |
| [Official Charts services](https://www.officialcharts.com/our-business-services/our-services/) and [licensing notice](https://www.officialcharts.com/who-we-are/copyright-notice/) | Candidate licensed historical market-specific outcomes | Obtain permission/subscription terms and a complete eligible comparison frame; website visibility is not bulk-reuse permission. No scraper or catalog downloader is proposed. |
| [Spotify Developer Policy](https://developer.spotify.com/policy) | Assess feasibility only | Current policy restricts content/service analysis and ML/AI ingestion. Do not design the research around public API scraping or assume exposed popularity fields may be reused for this purpose. Any authorized alternative requires documented permissions. |

No identified source provides, by itself, lawful original audio, reliable sung-note annotations, section/beat maps, complete success outcomes and matched non-hits. Build a provenance/eligibility manifest and pilot a small explicitly permitted collection before making an Observatory dataset commitment. Provider aggregate listenership is not necessarily comparable across providers or observation dates.

### 10.3 Cohort construction

Start with a defined release population, not search results for famous songs. Match/control on market, genre, release period, pre-release artist popularity, exposure window and recording context where feasible. Use within-artist comparisons as a distinct design, not a substitute for controls across artists. Track label/marketing/playlist exposure when available; residual confounding remains. Do not condition on post-release popularity measurements as if they were pre-release controls.

Declare exact-work, cover, remix, remaster, album/single and excerpt relationships before splitting. Audit excluded/missing audio and transcription-quality differences by outcome: louder production or cleaner stems must not masquerade as melodic success. Show balance tables, overlap/positivity, missingness and censoring. A collection of charted songs alone supports comparisons among charted releases, not chart-entry prediction against all releases.

### 10.4 Statistical baseline and leakage prevention

Use prespecified feature summaries, matched contrasts and regularized regression/conditional or hierarchical models appropriate to binary/count/continuous outcomes. Baselines: prevalence/within-cohort mean, metadata-only, then metadata plus melodic features. Report incremental heldout value, effect sizes and clustered uncertainty, not accuracy alone. Use multiple-comparison correction for exploratory feature screens and distinguish them from preregistered hypotheses.

Two separate evaluation questions: unseen artists (artist/work-grouped split) and future releases of known artists (chronological split with work grouping). Do not claim one split answers both. Fit normalization, imputation, motif dictionaries, clustering, reference distributions, feature selection and hyperparameters inside training folds only. Keep original/transposed/ornamented versions and alternate transcription editions in the same fold. Freeze outcome horizon and split before comparing results; disallow future streams/charts from input features.

For binary outcomes report PR/ROC measures where appropriate, calibration and precision at declared thresholds; for continuous/count outcomes report error and fit against relevant baselines. Use artist/song-cluster bootstrap, permutation controls preserving matched strata, sensitivity analyses and out-of-era/market checks where supported. Plan sample size from independent artist/song counts and plausible effect sizes; no fixed number of tracks guarantees power. If the cohort is too small or imbalanced, return descriptive results and “insufficient evidence,” not a fitted success predictor.

No hit-conditioned recommendation reaches the composer unless its scope and uncertainty are disclosed. It may suggest an observed structural experiment, never promise commercial success.

## 11. Validation strategy and release gates

### 11.1 Separate evaluation targets

1. Candidate retrieval: occurrence recall, precision and false positives by transformation/negative category.
2. Correspondence: correct event/group links, pitch/rhythm residual accuracy, insert/delete attribution and ambiguity handling.
3. Families: pairwise co-membership precision/recall, B-cubed-style scores with an explicit overlapping-membership protocol, coverage and contamination. Purity alone rewards singleton families and is insufficient.
4. Ranking: precision@k, recall@k and NDCG/MAP against independently collected relevance judgments; show full-list discovery separately.
5. Fingerprints: mathematical invariants, weighting/denominators and uncertainty sensitivity, not artistic validity.
6. Creative operations: formal correctness, constraints, diversity, immutability and editing usability; musical relevance is a separate human study.
7. Popularity research: cohort/split validity, out-of-sample effect stability and incremental association, not causality.

Use [mir_eval.pattern](https://mir-eval.readthedocs.io/latest/api/pattern.html) where its conventions fit: it distinguishes establishment, occurrence and ranking metrics, and its strict transposition metric is not a general fuzzy-correspondence metric. Supplement it with explicit synthetic event ancestry and human judgments rather than adapting labels to make one score look good.

### 11.2 Numerical suites

Create a new versioned evaluation area, leaving `docs/identity/`, `evaluation/real/` and prior result files frozen. Seeded development/heldout generators must split at base melody/family, not transformed occurrence. Include varied rests, tuning, target lengths, compound/asymmetric meters, changed ending, multiple insert/delete runs, repeat/sustain alternatives, fragments, inversion and rhythm-only similarity.

Hard negatives: ascending scales, common arpeggios/cadences, repeated-note rhythms, shuffled pitch inventories, rhythm-matched unrelated pitches, contour-matched changed intervals and unrelated excerpts matched for range/length/density. Distinguish synthetic negatives from human-declared unrelated musical examples. Test A–B–C bridge families, nested motifs and three/five-song families; add songs in different orders and measure membership/representative/ID stability.

Transcription perturbations: octave errors, dropped attacks, duplicated vibrato fragments, onset/offset jitter, phrase split/merge and missing confidence. Compare actual alternate model editions without treating them as extra songs. Grid tests cover origin/BPM/meter error, confirmed validity edges, pickups, swing and unconfirmed grids. Evidence-ID tests prove every displayed target resolves to the correct original source edition.

Provisional engineering gates, to be frozen before the new heldout run: exact/transposed controlled retrieval ≥95%; known one-to-one link F1 ≥95%; deliberately nontransitive bridge fixture never merges all members; no regression hidden behind a pooled average. Report rhythm/ornament/fragment and hard-negative results separately with uncertainty; agree release thresholds from development data before evaluation. These are **proposed gates**, not measured performance or perceptual guarantees.

### 11.3 Variation correctness and persistence tests

- Inversion twice, pitch retrograde twice and full retrograde twice restore supported inputs; transpose `k` then `-k` restores; augmentation then inverse restores within numerical tolerance. Test fractional pitches and explicit off-scale policies separately.
- Arbitrary selected pitch edits preserve unselected note records exactly; time operations reject collisions with locked notes. Test empty/single/noncontiguous selections, notes crossing region bounds, odd meters, rests and invalid ranges.
- Explicit unequal motif/answer regions work; adding an unrelated introduction/coda does not change their comparison. Zoom/pan never changes document validation bounds.
- Five candidate requests produce five distinct feasible alternatives or fewer with reasons; equal seeds/inputs/configuration give equal results. Test infeasible key/range/chord combinations without silent relaxation.
- Preview, audition and rejection leave saved/working originals unchanged. Partial acceptance uses dependency groups; undo/redo restores complete transactions. Stale previews cannot overwrite later edits; branch merge/restoration retains histories.
- MIDI fixture round trips verify supported semantic notes/velocities/tempo/meter within one exported tick, unknown-event reports, overlapping-track rejection, tempo-map handling and microtonal loss disclosure. File size/event bounds prevent pathological input.
- Reference-guided proposals pin family/fingerprint revisions and source evidence. Invalid/missing sources yield unavailable checks; all selected reference sides participate. Similarity warning tests include exact/transposed copying and common conventions, without a legal verdict.

### 11.4 Browser and audio tests

Extend the existing Playwright fixtures/server at **1366×768 and 1920×1080**. Use disposable data for all edits/reviews and a read-only snapshot of personal sources. Hash original audio, corrections, references, contexts, ideas and frozen results before/after. Test imported fixture data separately from existing user files; never attest MHS references.

Required journeys:

- Atlas with >12 families and >100 occurrences: pagination/filtering exposes every stored item; status distinguishes unavailable/not-analyzed/no detection; added model variant changes neither song count nor support.
- Family across three synthetic works plus one duplicate version: all occurrences accessible, direct links highlighted, bridge negative separated; stable family links survive added songs and representative changes with revision history.
- Multi-section tests: Chorus 1/2, pre-chorus→chorus, cross-type motifs and unknown sections; filtering retains exact source attribution. Provisional grid never produces confirmed beat/groove statements.
- Explorer: pointer-select occurrence, hear A/B/third source, pause/resume/loop, toggle normalized views, follow note link; source seconds and audio source remain correct. Missing assets and rapid clicks are handled without stale playback.
- Studio: draw/import original melody, marquee/select four bars, generate alternatives, edit ghost notes, invert only one gesture, accept part, copy to another bar, merge compatible suggestions, undo/redo, branch/save/reload/export, return to source and back without draft loss.
- Tempo and meter changes update bars/metronome/piano scheduling while symbolic beats and original audio hashes stay unchanged; text fields suppress global shortcuts.

Audio assertions must measure rendered signals, not only method calls. Use known synthetic note fixtures to estimate fundamental frequency and onset spacing, isolated bus RMS/mute behavior, accented metronome envelopes and source-specific marker segments. Verify no duplicate oscillators after candidate switching and silence after Stop/leave. Use offline rendering for precise DSP assertions and real browser playback for lifecycle/latency behavior; calibrate scheduling tolerances to the test environment. Headless Web Audio samples verify signal generation, not physical speaker audibility or perceptual quality. Human listening feedback remains separately recorded, never fabricated.

### 11.5 Human relevance study

After a working atlas exists, recruit consenting musicians to review blinded candidate and hard-negative pairs/families, with a rubric separating target similarity, rhythm, broad structure and usefulness as a writing exercise. Collect independent judgments, disagreements and “uncertain”; measure inter-rater agreement. Avoid showing algorithm rank/artist labels before the initial judgment. Sample by transformation/score/source, not just attractive top examples. No human assessment is claimed until actually collected; the user's recordings receive no invented reviews.

## 12. Milestones, dependencies and definitions of done

Each milestone includes functional code, unit/numerical tests where applicable, browser/audio regression, a usage update and preservation checks. Names below are proposed file locations, not files created by this plan.

| Milestone | Dependency and implementation slice | Definition of done |
|---|---|---|
| **M0 — Catalog and snapshot integrity** | Extend `library.py`; add `catalog.py`, `identity_schema.py`, catalog persistence/API and a compact reconciliation UI | One work with multiple recordings/editions counts once; unresolved identity stays explicit; source/context snapshots reproduce reads; migration dry run changes no legacy files; research exclusions and stale revisions tested. |
| **M1 — Retrieval and correspondence contracts** | M0. Extend `melodic_identity.py` behind a new version; add `identity_features.py`, indexed candidate generation and new numerical suite | Old run replay remains valid; exact/tempo/ornament/hard-negative metrics reported separately; multiple occurrences and missing-channel/ambiguity behavior verified; all discovered results stored with coverage; no silent output cap. |
| **M2 — Family service and jobs** | M1. Add `identity_families.py`, `identity_store.py`, `identity_jobs.py`; SQLite derived index | Three-plus-song controlled families, bridge-negative rejection, deterministic revisions/lineage and incremental runs work; cancellation/resume and full result counts tested; every family member has direct evidence. |
| **M3 — Pattern Atlas and Explorer** | M2. Extend `web/artist-identity.js`; add `web/pattern-atlas.js` and `web/variation-explorer.js`; reuse rolls/audio | All families searchable/filterable; matrix states accurate; 2/3+ occurrences audible and visually comparable; one-source and no-match states useful; Learn opens independent idea with all evidence pinned; legacy statistics stay Advanced. |
| **M4 — Section/beat relationships** | M3 + existing context. Extend `musical_context.py`, feature service and explorer | Cross-song matching section types, within-song repeated sections and transitions work; unlabeled spans remain analyzable; beat normalization/phase requires full validity; offsets/censoring/swing tests and audible source alignment pass. |
| **M5 — Fingerprint Lab** | M0/M4. Add `fingerprints.py`, `web/fingerprint-lab.js`; adapt `corpus.py` through new service | Song/section/artist views with distributions, medoids, missingness and equal-song weights; one/two-song exploratory examples available; alternate-edition/grid sensitivity shown; no specificity claim without reference corpus. |
| **V1 — Selective theory operations** | M0 schema principles; independent of M1–M5. Extend `learning.py`, `learning-roll.js`, `editor-core.js`; add `variation.py` | Explicit selections/motif-answer regions, document-vs-viewport bounds and locked neighbors; transpose/inversion/retrograde/time scaling mathematically verified; whole-idea legacy tools still work. |
| **V2 — Candidate preview and partial acceptance** | V1. Add `web/variation-studio.js`, proposal API and transaction history | Request five distinct alternatives where feasible; ghost edit, original/candidate A/B, reject, valid partial acceptance, stale guard and full undo/redo work in real browser/audio tests without changing the base on preview. |
| **V3 — MIDI editing and versioning MVP** | V2. Add `midi_io.py`; extend `learning_store.py`, composition schema, shared scheduling and UI | Supported MIDI import/export round trips, copy/paste, cross-idea fragments, branch/save/restore, tempo/meter and long-arrangement editing complete; explicit limitations for unsupported MIDI; first four addendum capabilities delivered without artist data. |
| **M6 / V4 — Evidence-guided advisor** | M3/M5 + V3. Add `advisor.py`; extend technique contracts/learning links and variation scoring | Current own selection compared to pinned reference features; each suggestion explains changes and links sources; all selected sources checked for resemblance; artist guidance optional/exploratory when warranted; no source-template substitution or style-probability UI. |
| **M7 / V5 — Multi-artist reference comparisons** | M6 + lawful sufficiently described collections | Per-dimension artist weights, equal-artist/song choices and section filters; missing feature channels explicit; source-backed contrasts and own-idea library supported; references never silently merged into one artist. |
| **M8 — Hit Observatory research** | Separate lawful cohort/outcome gate; M5 features. Add `research/cohorts.py`, `research/observatory.py`, research UI and isolated result namespace | Authorized input manifest, matched/control population, frozen splits and prespecified outcomes; metadata baseline and incremental melodic effects with uncertainty/leakage audit; descriptive-only mode when evidence insufficient. No commercial-success promise. |
| **M9 — Optional learned retrieval** | Validated M1–M8 needs, not mandatory | Only proceed if external pretrained retrieval improves frozen recall/ranking at acceptable false positives/cost, with code/weight/data rights documented. Detailed explanations still use measured alignment; no singer-specific training on two tracks. |

Suggested execution packages: M0 → M1/M2 → M3/M4 is the first collection-learning release. V1–V3 is the next independent creation release (V1 may start earlier if preferred). M5 → M6 ties them together. M7 expands reference scope; M8 remains separate. Do not build empty Observatory UI shells while waiting for data.

### 12.1 File-level change plan

| Area | Existing files to extend | New files / artifacts proposed |
|---|---|---|
| Identity and schemas | `src/library.py`, `src/schema.py` only where backward-compatible adapters are needed, `src/storage.py`, `src/workspace.py` | `src/catalog.py`, `src/identity_schema.py`, catalog tests |
| Matching/families | `src/melodic_identity.py`, reusable functions in `src/motifs.py` | `src/identity_features.py`, `identity_families.py`, `identity_store.py`, `identity_jobs.py`; new versioned evaluation tool/output directory |
| Context/fingerprints | `src/musical_context.py`, `src/features.py`, `src/corpus.py` | `src/fingerprints.py`, scope/weight/uncertainty tests |
| Atlas/Explorer | `src/web/artist-identity.js`, `app.js`, `index.html`, `learning.css`, `learning-roll.js` | `pattern-atlas.js`, `variation-explorer.js`, `fingerprint-lab.js`; atlas browser fixtures |
| Variation Studio | `src/learning.py`, `learning_store.py`, `src/web/learning.js`, `learning-roll.js`, `editor-core.js`, `audition.js`, `context.js` | `src/variation.py`, `src/midi_io.py`, `src/advisor.py`, `web/variation-studio.js`; operation/MIDI/branch/audio tests |
| Research | Preserve `real_evaluation.py`, published references and frozen benchmarks | `src/research/cohorts.py`, `observatory.py`; licensed manifests, preregistration and new result namespace |
| Validation/docs | Extend `tests/test_melodic_identity.py`, `test_learning.py`, `test_library.py`, `test_musical_context.py`, `tests/browser/identity.spec.cjs`, `learning.spec.cjs`, existing test runner/fixture server | Dedicated family/fingerprint/variation/MIDI/cohort suites; user guide per release, screenshots and machine-readable numerical reports |

Do not rewrite pitch/transcription/annotation services, delete old motif implementations before compatibility adapters are proven, or modify old generation behavior implicitly. Characterization tests should protect legacy reads and saved ideas during migration.

## 13. Performance, dependencies, privacy and failure handling

Naive pair alignment over `W` windows of length `L` and `H` transposition hypotheses costs roughly `O(W²HL²)`; complete-link validation can also be quadratic. A few hundred songs can produce millions of windows/pairs if all overlapping subsequences are materialized. Index broad candidates, partition by optional section/type, cache representations and alignment pairs by edition/configuration, stream results and checkpoint. Do not first compute everything synchronously and then hide most results.

Proposed performance fixtures: 2, 20 and 200 synthetic songs with declared note/window counts; a 10,000-family×200-song sparse matrix fixture; and a 10,000-note monophonic composition fixture. Measure runtime, peak RSS, index size, payload size, candidate recall and rendering/event latency. Proposed interactive budgets on the named Windows test machine: cached atlas page under 1 s, pointer/edit feedback p95 under 100 ms, first five simple variation previews under 1 s for ordinary phrases. These are targets to measure, not current guarantees. Long searches show progress/cancel instead of promising a fixed instant response.

Virtualize rows/columns and visible notes; do not create a DOM roll/audio instance for every occurrence. Cache waveform summaries and request detailed F0/audio only for visible/selected examples. Debounce composer checks, use input revision tokens to drop stale responses, and preserve drafts when a job fails. Limit file size, notes, candidates and work per request with explicit coverage messages rather than silent truncation.

Core work can use current NumPy/SciPy, Python dataclasses/SQLite and existing browser tools. MIDI uses installed libraries with explicit future dependency declarations. Statistical research may justify a separately pinned optional `statsmodels`/evaluation extra after a compatibility check; neural models, vector databases, hosted services and GPU dependencies are not prerequisites. [CLaMP](https://ai-muzic.github.io/clamp/) demonstrates symbolic semantic retrieval, not exact vocal-note alignment; consider it only as a later candidate generator after licensing and domain-transfer validation.

Keep local-first operation and no automatic upload, telemetry, catalog acquisition or voice synthesis. Store source rights/attribution, allowed uses, provider terms snapshot/date and access restrictions. Separate permission to analyze privately, permission to distribute audio, permission to redistribute derived annotations and permission to train a model. User import is not evidence of public redistribution rights. Exports omit private paths and restricted audio by default. Revoking/removing a source makes evidence unavailable with an explanation; do not silently resolve a similar filename or retain unauthorized cloud copies.

Audio samples, hashes and musical fingerprints can identify material; treat them as private project data. Human review records need reviewer consent and minimal personal information. Never delete source data or consolidate “duplicates” as part of identity reconciliation. A derived index can be rebuilt; user-authored labels/reviews/ideas cannot be casually regenerated.

## 14. Feasibility and final acceptance boundaries

| Scope | Feasible with current two recordings / own compositions | Additional evidence required |
|---|---|---|
| Atlas and Explorer | Multi-occurrence candidate discovery, full result access, source A/B and typed transformations; synthetic three-plus-song fixtures exercise scaling | User-confirmed song/artist identity for verified cross-song/artist labels; human relevance for confirmed musical families |
| Sections/beats | Existing manually saved context and local examples; no fabricated labels/grids | More annotated sections and confirmed spans for section/groove coverage |
| Fingerprints | Descriptive per-passage/song distributions and exploratory two-song overlays | Larger independent catalogs for stable tendencies; matched references for distinctiveness |
| Variation Studio MVP | All formal operations, previews, acceptance, versions and supported MIDI exchange using the user's own notes | Human listening to assess musical usefulness; no artist catalog needed |
| Artist/multi-artist advisor | Source-backed local exercises labeled exploratory | Reliable family/fingerprint evidence and broader catalogs for stronger comparisons |
| Hit Observatory | Cohort/schema/tests and synthetic statistical checks only | Lawful outcomes plus comparable controls, aligned music data, adequate independent samples and frozen research evaluation |

Final core acceptance: import/select a catalog; see every discovered family and its analysis coverage; inspect several occurrences with exact source audio and honest correspondence; understand an invariant and a variation; open a technique in the existing composer; select an original four-bar region; request distinct alternatives; audition, reverse only a selected gesture, combine valid fragments, undo, branch/save/reload and export. No annotation attestation, benchmark import, microphone recording or copied source phrase is required.

Known scientific limits remain visible: transcription and phrase-boundary errors, unresolved song identity, ambiguous alignments, nontransitive similarity, incomplete search, generic conventions, sparse/nonrepresentative catalogs, uncertain beat/harmony context, and noncausal popularity associations. Neither a similarity score, constraint compliance, a family label nor a hit association establishes artistic influence, musical quality or legal originality.

**Architecture approval:** the user approved this direction and authorized M0. Its actual completion state follows. M1 and later milestones have not been implemented in this increment.

## 15. M0 completion record — 2026-11-05

**M0 complete. Stop before M1.** Usage and storage details: [Catalog identity guide](CATALOG_IDENTITY.md). Running application: http://127.0.0.1:8783/.

Delivered:

- Stable content-based recording UUIDs, explicitly created artist/work UUIDs and content-keyed analysis editions. Legacy artist/title strings remain unconfirmed suggestions. Different works can share a title; recordings of the same work aggregate by work ID, and model variants remain one recording.
- Independent, append-only catalog revisions with a guarded current head. The reconciliation dialog supports existing/new artists and works, multiple performers, take/version labels, unresolved identities, primary analysis choice and write-free count previews. It does not change the open editor, selected passage or main transport.
- Read-only discovery of existing recordings, without eagerly persisting migration data. Catalog reads resolve working corrections in memory rather than materializing them back into historical reports. Explicit correction saves retain their established behavior.
- Immutable input snapshots with catalog revision/content, one explicit working-analysis edition per source, note/model/configuration fingerprints, source availability, source seconds, supplied context, section and beat-grid revisions. Reads verify the stored snapshot's content ID. Snapshot creation rejects competing model editions, stale catalog revisions and ordinary-corpus research inclusion. Newly built profiles link their input snapshot.
- Sidebar association labels, work/take search and confirmed-work versus unresolved counts. Legacy artist metadata remains filterable with an explicit unconfirmed label. Statistical profiles use catalog work identities for aggregation while keeping unresolved recordings as separate provisional units.

Verified final results: **110 Python tests, 11 JavaScript tests and 114 browser tests passed**, with browser runs at 1366×768 and 1920×1080. The browser suite includes the actual association/save/reload/snapshot journey and existing transport, source/piano audition, note editing, human references, metronome, seek/selection/zoom and composition persistence/export regressions. Catalog interaction measured nonzero original-vocal RMS around 0.122 and 0.158 while preserving the open editor and playback. This is signal/lifecycle verification, not a claim about physical speaker audibility.

Read-only inspection of the actual library succeeded at both sizes with two personal recordings (ten source groups including research). Neither personal source was assigned an artist/work or human attestation by the implementation. **All 809 protected existing data/result files retained their SHA-256 hashes.** Evidence: [validation summary](catalog/validation.json), [actual library checks](catalog/actual-library-checks.json), [1366 screenshot](catalog/actual-library-1366.png), [1920 screenshot](catalog/actual-library-1920.png).

Earlier validation attempts encountered Windows sandbox temporary-directory permissions and unreachable fixture-server processes. After normal-temp access and a clean hidden fixture restart, the clean full runs above passed. A new browser test initially targeted a hidden corpus control and failed to clean up its disposable associations; both test defects were corrected before the final 114/114 run. No failed run was counted as passing.

M0 boundaries: no automatic work/artist inference, destructive entity merging, cross-file timestamp transfer, artist distinctiveness claim, corpus-wide family discovery, new model inference or Variation Studio. A selected primary analysis denotes the current working edition until pinned; human-reference editions retain their independent research workflow and are not made default corpus inputs. Existing section-comparison algorithms remain unchanged. A derived SQLite discovery index is unnecessary for M0 and remains a later scaling concern.

Next recommended milestone: **M1 — Retrieval and correspondence contracts**, using these pinned catalog/snapshot identities, independent positive/hard-negative development and heldout suites, complete result accounting and versioned pairwise algorithms. This release stops at M0.
