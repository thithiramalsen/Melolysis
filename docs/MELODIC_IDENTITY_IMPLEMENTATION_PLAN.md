# Melodic Identity Analysis: implementation plan

**Planning and research only · 2026-11-05 · audited revision `7ee9efa` (`playhead fix`).**

This task adds this document only. Application code, dependencies, recordings, note editions, saved ideas, context revisions and evaluation artifacts are unchanged. No models or datasets were downloaded. Proposed algorithms, thresholds and release targets below are design decisions to evaluate, not implemented features or measured accuracy claims.

## 1. Product decision and recommended order

Build an **Artist Identity** workspace around selecting two songs, examining a small set of candidate corresponding passages, hearing the originals, inspecting their differences, and choosing **Learn this pattern** to develop an independent idea. One song remains useful in Study Song; two songs enable exploratory cross-song evidence, not an established artist signature.

Implement in this order:

1. Establish stable song identities, pinned note editions and a reproducible benchmark contract.
2. Implement an interpretable pairwise matcher with explicit correspondence and abstention.
3. Deliver the complete two-song listening/comparison interface.
4. Add family discovery, phrase construction and section-conditioned aggregation.
5. Connect those findings to original-motif exercises in the existing composition editor.
6. Validate retrieval, false positives, musical usefulness and preservation together.

The first useful release is a reliable two-song comparison, not another large profile report. Do not start by training embeddings or changing transcription. Keep existing motif and resemblance APIs as the frozen compatibility baseline until a versioned replacement has measured benefits.

## 2. Repository audit: what exists and what it actually does

Inspected README, technical/product audits, evaluation and real-vocal reports, learning/transport documentation, the section/beat plan and implemented usage guide, and the current playhead guide. Inspected the files below, relevant unit/browser tests, requirements and Playwright configuration. Earlier planning documents describe capabilities beyond the delivered section/beat increment; current source and usage documentation take precedence when describing implemented behavior.

### 2.1 Representations, analysis and persistence

| Component | Implemented behavior / reuse | Gap for melodic identity |
|---|---|---|
| `src/schema.py:112–149`, `NoteEvent`, `notes_from_dicts` | Source-second start/end; fractional MIDI pitch; confidence, flags, raw-frame span, phrase ID; ID and monophonic-overlap validation. | IDs are scoped to an edition, not globally unique across songs/models. Confidence may be unavailable via flags and is not calibrated. Need composite event references and explicit uncertainty availability. |
| `src/transcription.py:8`, `assign_phrases` | Phrase candidates segmented by rests, default 0.35 s. | These are neither verified musical phrase boundaries nor sections. Longer connected singing can become one phrase; short rests can split a motif. |
| `src/features.py:43`, `analyze_notes` | Phrase-local intervals, contour, range, first peak position, density, durations, IOIs, rests, leap/recovery; separate expressive contour estimates. Supplied chords and tonal context enable limited observations. | No phrase-construction correspondence; first-peak selection loses tied peaks; no matched-note explanation; scale degrees are distributions rather than aligned sequences. Acoustic delivery is not compositional identity. |
| `src/musical_context.py:9–32` | Fixed beat map, explicit pulse unit/meter/swing, source-to-quarter-note mapping, confirmed validity coverage, event durations and grid residuals. | No variable-tempo map; no calibrated alignment tolerance; no complete rhythm sequence including rests, phrase starts/ends and carry notes. Legacy feature beat arithmetic is a different, weaker contract. |
| `src/musical_context.py:34`, `MusicalContext` | Source-hash-owned sections/grid with independent append-only revisions and stale-write checks. Non-overlapping sections with types and occurrence IDs. | No stable artist/song catalog, multiple maps or correspondence review store. Reuse revision patterns; do not put motif review into reference annotations. |
| `src/library.py:23,47` | Hash-based model grouping, explicit research exclusion, unique-recording selection; deterministic preferred model in library. | Song identity still depends on artist/title text. Different takes/excerpts need an explicit common song ID; metadata changes must not change support counts. |
| `src/corpus.py:8` | Deduplicates source hashes, averages recordings within artist/title song groups and weights songs equally. Histograms, example phrases, caveats, reference-corpus comparison. | Legacy section summaries use recording-level metadata, not timed sections. Cross-song matcher groups by song string alone. Global profile endpoint does not establish a common singer merely from its title. |
| `src/workspace.py:101–119`, `section-compare` | Filters saved section occurrences, rejects unresolved/mixed artists and research material; source playback links, per-section ranges and equal-song mean. | Lists occurrences without ranking or matching them. Returns attack-onset membership, omits carry-ins, retains full offsets beyond section end; no complete-span/censor flags or edition-pinned comparison artifact. |
| `src/learning.py:21`, `passage_study` | Evidence-backed local findings and source fingerprints, candidate motif examples, optional context. | Clips overlapping notes to passage bounds before feature/motif extraction; this can manufacture an apparent attack or duration change. Identity matching must use original event timing and separate visible clipping. |
| `src/learning_store.py`, `LearningStore` | Immutable studies and bookmarks, source-note snapshots, independent idea revisions, optimistic concurrency, export. Study identity incorporates current section/grid revisions. | Links currently point to one study/finding. Need a versioned multi-source identity link, immutable correspondence snapshots and independent human relevance reviews. |
| `src/storage.py` | Atomic JSON replacement, deterministic keys, immutable correction histories. | Reuse small helpers; add identity-specific schema/config hashes rather than changing pipeline version or raw caches. |

### 2.2 Current matching: both within-song and cross-song, with important limits

`src/motifs.py:5` represents a sequence as pairs:

`(pitch[i+1] − pitch[i], log2(duration[i+1] / duration[i]))`.

`sequence_distance` at line 13 computes global edit distance with unit insert/delete cost and substitution cost `0.75 × min(1, interval_difference/4) + 0.25 × min(1, duration_ratio_difference)`, normalized by the longer representation length. It returns only a scalar. It does not expose the dynamic-programming path. The interval representation has one fewer element than the note sequence; aligning interval tokens cannot automatically identify note correspondences after an insertion.

| Existing path | Actual scope | Consequence |
|---|---|---|
| `discover_motifs`, line 43 | Within one input recording/passage; whole rest-delimited phrases plus 4/6/8-note windows every two notes; first 180 distinct windows; greedy grouping; threshold 0.16; at most 20 displayed families. | Misses some start positions/lengths; early phrases dominate the cap; overlap suppression can hide valid nested patterns. |
| `discover_corpus_motifs`, line 108 | **Genuine cross-song code exists**: compares 4–32-note whole phrases from different song-name strings, first 100 phrases, length difference at most two, same distance/threshold. | No cross-song subphrase search, beat phase, onset gaps or section-aware matching. An exact motif inside a longer phrase may never be considered. Song-name equality is not trustworthy identity. |
| `variation`, line 26 | Any extra note becomes “expansion,” any missing note “contraction”; equal lengths use interval and adjacent-duration-ratio tolerances. | Added ornaments, missing transcription targets and structural extension are conflated. “Exact repetition” ignores unequal rests and global duration scaling. Changed-ending label ignores whether an aligned opening is sufficiently supported. |
| `source_similarity`, line 89 | Sliding equal-length 6–12-note windows by default; direct positional distance, no edit alignment. Learning calls it with minimum four. | Reuses useful transposition/rhythm checks but misses insertions/deletions and longer structural copies. Keep its current warning contract; do not silently replace the generator's behavior. |

The uniform-pattern filter rejects constant-interval, low-duration-variation candidates. This is useful but not a model of musical commonness. Two different small intervals, or a transcription artifact, can pass. Greedy membership depends on traversal order; scalar thresholds are not calibrated probabilities or evidence of distinctiveness.

### 2.3 UI/audio/composition reuse and specific integration hazards

- `src/web/app.js:122–131`: profile is still interval/statistic cards, within-song families and cross-song occurrence buttons. Keep the data in Advanced Statistics.
- `src/web/context.js:comparisonUI`: selectable section A/B, normalized `LearningRoll`s, original-tempo playback. It explicitly asserts **no note correspondence**. Its display checks `grid.confirmed` rather than the full validity-coverage result; the new comparison must gate normalization on both sides' eligible spans.
- `src/web/learning.js:showComparison`: one-study A/B, first-pitch normalization and equal-array-index change highlighting. Equal note count does not prove alignment. Replace that assumption only in the new correspondence path; retain old study snapshots as historical outputs.
- `src/web/learning-roll.js`, `editor-core.js`: reusable Canvas notes, zoom/pan, selected highlights, edit history and original-idea manipulation. Add a read-only correspondence layer instead of a separate editor framework.
- `src/web/audition.js`, `VocalAudition`: original-source playback, separate gains, one AudioContext, resumable sessions, seeking, temporary note audition and metronome. Reuse one owner for A/B; no duplicate audio engines.
- `src/web/learning.js:wireRuler`, `wireSelection`: recently separated playhead and selection lanes must remain intact. Comparing songs must not repurpose these gestures.
- `src/learning.py:develop_idea`: already changes the user's rhythm/ending and creates a repeated answer. `assess_idea` checks local constraints; its motif check splits the whole note list in half. Explicit user-marked motif/answer ranges are needed for meaningful new exercises.
- `LearningStore.link` and frontend technique navigation assume one source. Extend the link contract; preserve unsaved compositions when visiting either source.
- `Workspace.dispatch` generally holds a shared lock during analysis. New pair searches must snapshot inputs under a short lock and compute outside it, so playback/import status and saves stay responsive.
- `section-compare` can deduplicate reports using the last supplied version while resolving its `analysis_id` from the first same-source input. The new path must bind the selected edition and playback evidence consistently, not combine two variants.

### 2.4 Read-only checks performed in this planning task

` .venv\Scripts\python.exe -B -m unittest tests.test_analysis -v `: **12/12 passed**. These existing tests cover simple transposition, source attribution, equal-song weighting, basic exercises and generation constraints. They do not validate ornament correspondence, cross-song retrieval precision or artist specificity. No full suite, browser/audio run or new accuracy benchmark was performed for this plan.

Executed in-memory probes against the existing functions with `python -B`; no artifacts or source data were written:

| Probe | Actual output | Interpretation |
|---|---|---|
| `[60,62,65,64]` versus transposed `[67,69,72,71]`, doubled onsets/durations | distance `0.0`; `transposed_repetition` | Correct invariance, but tempo scaling is not identified separately. |
| Same pitches and 0.4 s durations; starts `[0,.5,1,1.5]` versus `[0,1,3,5]` | distance approximately `1.87e-16`; `exact_repetition` | Rest/onset rhythm changes are invisible. |
| `[60,62,65,64]` versus `[60,62,63,65,64]` | distance `0.296875`; `expansion` | Fails default 0.16 cutoff; no distinction between an added passing target and structural expansion. |
| Same opening, final 64 changed to 66 | distance `0.125`; `changed_ending` | A simple supported baseline to retain. |
| Four-note phrase versus `[50,53,67,69,72,71,68,60]` in another song | zero corpus families | Embedded transposed motif excluded by whole-phrase/length restriction. |

The first source uses starts `i×0.5`, duration 0.4 and confidence 0.9; the doubled version uses starts `i×1.0`, duration 0.8. Probe identities are synthetic strings, never real annotation labels.

Personal analysis inventory was inspected read-only: MHS Chorus has three model versions for one 33.812494 s source, artist “Unspecified singer”; the other 42.353197 s source has one version and blank artist. Neither source currently has saved section/grid revisions. These are **two recordings, not verified two songs by one singer**. Filenames containing a key/BPM are not confirmations. No correspondence or artist claim about them was established here.

## 3. Four levels of evidence and claim policy

| Level | Question / admissible output | Required evidence | Must not imply |
|---|---|---|---|
| A: motif recurrence | Does this specific short melodic pattern recur, exactly or approximately? | Explicit monotonic note alignment, pitch/interval/rhythm differences, covered targets and source spans. State all permitted normalization. | A contour resemblance is an exact melody; shifted rhythm is unchanged rhythm. |
| B: motif family | Which occurrences develop a related motif by changed intervals, rhythm, insertion or ending? | Pairwise alignment edges and interpretable transformation evidence; conservative family membership. | Every member of a chain is mutually similar; an extra note is necessarily a grace note. |
| C: phrase construction | Does a phrase reuse an opening, delay a peak, change an ending or repeat an attack pattern? | Ordered motif roles, peak positions, duration/rest and density measurements over explicit phrase spans. | Note-for-note correspondence where only structural properties agree; inferred emotional intention. |
| D: section habits | How do these properties differ between verses, pre-choruses and choruses? | Saved timed sections, eligible phrase/occurrence evidence, paired within-song contrasts and equal-song aggregation. | A rest-delimited phrase is a chorus; different songs' isolated sections establish a transition. |

Track independent fields for `scope` (local / within-song / cross-song), `level` (A–D), `match_kind` (melodic / rhythmic / combined / structural), and `claim_status` (candidate / human-reviewed similarity / measured aggregate). “Human-reviewed similarity” is a listening judgment in a separate store, not a transcription attestation.

Cross-song means at least **two distinct confirmed song IDs**, regardless of recording/model/section counts. Always show support as “2 of 2 analyzed songs,” recording count, non-duplicate occurrences and coverage. More songs provide broader observed support but do not automatically make a pattern artist-specific. Different works by shared songwriters, covers, takes and arrangements are confounds; musical choices in a performance cannot be attributed solely to the singer.

Artist-specific comparisons require an explicitly chosen, sufficiently comparable reference corpus, with section/genre/era/coverage caveats. A generic rising step pattern can be a useful local exercise but should not lead the identity workspace as a distinctive motif. No default “signature” label, influence inference, emotional explanation, originality verdict or artist-classification accuracy.

## 4. Research assessment and algorithm selection

These sources inform the design; none supplies measured Melolysis performance on the user's material.

| Approach | Strength / failure modes | Decision |
|---|---|---|
| Relative interval and duration-ratio sequences | Cheap, interpretable, invariant to constant pitch shift and uniform time scale; local insertion changes multiple interval tokens; duration alone ignores silence. | Preserve current baseline. Use for candidate retrieval and feature ablations; add IOI/gap features. |
| Scale-degree sequences | Can reveal diatonic variants across keys/modes. Wrong tonic or modulation creates misleading equivalences; pitch-class folding loses register. | Optional secondary channel only with explicit local tonal context and provenance. Retain chromatic alterations and octave/register; never infer a key from the filename. |
| Contour abstractions | Direction, turning points and coarse interval bins capture gestures with different interval sizes. Many unrelated melodies share them. | Candidate retrieval / Level C channel; contour alone cannot earn Level A identity. |
| Event sequence alignment | Allows gaps and substitutions, with a traceback suited to explaining added/omitted targets. Musical scoring must be validated. | Primary v1: transposition-search plus affine-gap local alignment, followed by anchored context comparison. |
| Subsequence DTW | Finds a shorter pattern in a longer sequence and tolerates temporal stretching; many-to-one paths can erase attacks and over-warp unrelated contours. | Controlled baseline for contour/rhythm retrieval. Constrain steps/warp and never turn its repeated indices directly into exact note correspondences. |
| Geometric onset/pitch matching | Useful exact transposition/time-shift control; harder for performance timing, added targets and semantic phrase changes. | Optional later exact-pattern baseline, not required runtime. |
| Multi-feature ranking and clustering | Separates pitch, rhythm and structure; supports explainable families. Poor normalization or transitive chaining creates false families. | Required, with separate channel scores, conservative graph grouping and context-specific thresholds. |
| Learned embeddings | Could improve high-recall candidate retrieval on larger diverse corpora. A scalar embedding distance does not expose note correspondence and may reflect genre, timbre or notation artifacts. | Defer. Any future encoder is a retrieval ablation followed by explicit alignment, never proof of a motif or a two-song-trained singer model. |

Musically informed sequence alignment has been evaluated on annotated folk melodies, including pitch, rhythm and segmentation scoring. That motivates an interpretable baseline; reported results on that domain do not transfer to modern isolated vocals. [Van Kranenburg et al., ISMIR 2009](https://webspace.science.uu.nl/~veltk101/publications/art/ismir09-kranenburg.pdf).

Subsequence DTW explicitly searches for an aligned interval inside a longer sequence. Existing librosa 0.11 supports a cost matrix, subsequence mode, step constraints and path backtracking, so a comparator needs no new runtime package. [AudioLabs FMP](https://www.audiolabs-erlangen.de/resources/MIR/FMP/C7/C7S2_SubsequenceDTW.html), [librosa 0.11 DTW API](https://librosa.org/doc/0.11.0/generated/librosa.sequence.dtw.html).

CLaMP is a useful example of pretrained symbolic/music-text retrieval, but its authors note limitations with performance MIDI. Its semantic search objective is different from local note correspondence. Any future evaluation needs pinned code/weights, license review, preprocessing and held-out motif retrieval tests; no pretrained embedding is selected or installed by this plan. [CLaMP author project](https://ai-muzic.github.io/clamp/).

### 4.1 Baseline experiment matrix

Compare on identical candidates and separately end-to-end:

1. Existing `sequence_distance` and current whole-phrase corpus search, unchanged.
2. Exact chromatic-interval search with onset/IOI ratios.
3. Contour-only and rhythm-only subsequence DTW.
4. Event local alignment with pitch only, then pitch + duration/IOI, then added rest/attack channels.
5. Full retrieval + alignment + family pipeline with uncertainty/coverage gates.

Report candidate recall independently from reranker precision. Otherwise a better scoring function may hide candidates lost during retrieval. Evaluate event-level versus interval-edge alignment explicitly. Keep scale degree, simplification and reference-corpus specificity as optional ablations, with their own eligible denominators.

## 5. Data and identity contracts

### 5.1 Stable identities and edition selection

Add the catalog sidecar deferred by the section/beat plan: `artist_id`, `song_id`, recording source hashes, explicit memberships, display names, aliases and optional work/cover/arrangement relationship. Reading existing data must not migrate it. Offer artist/title grouping suggestions for explicit confirmation. Unknown songs can still be compared as recordings, with cross-song support withheld until identity is established.

One recording contributes one deliberately selected note edition per run. Preserve raw prediction ID, analysis ID, working-correction revision or reference edition/revision, note fingerprint, model name and review state. Alternative models are sensitivity comparisons, never extra occurrences/songs. Identical re-encoded/cropped audio may evade content-hash deduplication: warn and support manual same-song/recording-family association; never consolidate files automatically.

For experimental research comparisons, apply `validate_corpus_sources` using all catalog versions' category provenance, not just selected report metadata. Explicit research mode remains visibly distinct from an artist identity. Reject mixed known artists for artist-wide claims; allow a clearly labeled cross-artist comparison as a separate user choice.

### 5.2 Proposed immutable records

| Record | Minimum fields |
|---|---|
| `IdentityRun` | schema/algorithm/config version; catalog revision; sorted source/edition fingerprints; query scope; section/grid/tonal-context revisions; candidate/search budgets; random seed if used; package/code hashes; status; truncation; timings/resource measurements. |
| `PassageOccurrence` | run-local ID; artist/song IDs; source hash and analysis ID; edition reference; original start/end; ordered composite event IDs; parent phrase IDs and boundary origin; section occurrence/revision; grid revision/coverage; source title snapshot; quality and censor flags. |
| `EventProjection` | original start/end/pitch/confidence/flags; display intersection; onset membership; carry-in/out; interval and direction; duration, IOI and rest; optional quarter-note onset/duration/bar phase; tonic-relative degree with context status. |
| `PairMatch` | A/B occurrence IDs; level/kind; transformation parameters; ordered alignment operations; feature costs; matched coverage on both sides; gap/warp counts; second-best ambiguity; sensitivity; null/commonness diagnostics; decision and limitations. |
| `AlignmentOperation` | match/substitute/insert/delete/ambiguous-group; A/B composite IDs (arrays only for explicitly grouped operations); source-time spans; pitch, interval and rhythm deltas; uncertainty reasons. “Insert/delete” describes B relative to A, not compositional history. |
| `MotifFamily` | member occurrence IDs; medoid; supporting accepted edges; rejected/uncertain edges; shared core and variable roles; unique supporting/eligible songs; within/cross-song counts; section context; stability; human relevance reviews. |
| `ConstructionFinding` | measured property or role sequence; exact supporting event/phrase spans; eligible and missing samples; local/aggregate scope; conditions/exceptions; comparison IDs; linked exercise specification. |
| `IdentityReview` | pair/family + run ID; author/time; useful similarity / unrelated / uncertain; optional correspondence corrections and rationale; independent revision lineage. Never a reference-review status. |

Use `(source_hash, edition_fingerprint, event_id)` as event identity. Store original fractional pitches and source seconds at full precision. Display rounding is not persisted quantization. A normalized pitch/time coordinate must never replace source coordinates used for playback or exports.

### 5.3 Representations and boundary semantics

- Preserve original event sequence. Derive pitch intervals, sign/coarse contour, adjacent duration ratios, IOI ratios, gap-before/gap-after, articulation ratio and attack count. Rest duration zero is valid: use bounded absolute/relative differences rather than `log(0)`; define epsilon only for positive ratios and record it.
- Confirmed beat maps project `q(t)=(t-origin)×BPM×unit/60`. Duration in beats is `q(end)−q(start)`. Require full relevant span coverage; a confirmed flag alone is insufficient. Missing/provisional maps retain second-based relative rhythm, labeled “tempo-normalized duration/onset pattern; beat phase unavailable.”
- Separate **rhythmic shape** (relative IOIs/durations/gaps) from **placement** (bar/subdivision phase). A motif can keep its rhythm while entering half a beat later; report the displacement, do not normalize it away invisibly.
- Mismatched meters allow shape comparison but not an assumed same-beat role. Preserve quarter-note units, meter and pulse unit in evidence. Swing is supplied context, not inferred; unknown alignment tolerance remains unknown.
- A clipped note retains its real onset/end and an occupancy intersection. Carry-ins are not new attacks; incomplete notes are excluded from complete-duration comparisons. Pair interval edges only within admissible continuous sequences, never across unrelated fragments.
- Default phrase candidates use existing IDs, but add sliding subphrases so an inaccurate rest boundary does not entirely control retrieval. Windows spanning phrase boundaries must be explicitly marked and penalized, not silently stitched.
- Repeated pitches remain separate attacks. An optional collapsed-target projection can suggest sustained-versus-reattacked similarity, retaining every original ID and rhythm difference. It cannot promote the two sequences to exact recurrence.
- No automatic ornament deletion. A secondary simplification can bypass a short intervening target as an alignment hypothesis; show the omitted target and its cost. “Grace note,” “melisma” and syllable boundaries require supplied labels/listening review.
- Structural descriptors use first/last/all tied peaks, normalized time location, range, direction segments, length, attack density trajectory, long-note placement, rests and opening/ending relationships. “Tension” is only a creative interpretation unless supplied harmony supports a narrower measured claim.

## 6. Proposed correspondence pipeline

### 6.1 Candidate retrieval

1. Resolve catalog, selected sections/passages and note editions; snapshot every dependency.
2. Extract whole phrases and contiguous subphrases (initial search lengths 4–16 targets, all start positions; whole phrases up to 64 targets as a separate bounded class). These are initial engineering limits, exposed in configuration and benchmarks.
3. For each song pair, index coarse interval/contour shingles and normalized IOI/duration shingles. Use multiple channels so pitch-different rhythm matches are not discarded by a pitch filter. Include an exhaustive small-fixture mode to measure retrieval losses.
4. Rank seeds with inexpensive features, with separate melodic/rhythmic/structural queues and quotas per song pair/section. Default same-section comparison where labels exist; allow cross-section search explicitly. Section equality is context, not additional musical evidence.
5. Expand seeds locally, align bounded windows, then suppress redundant heavily overlapping results on both sources. Retain meaningful nested motifs as parent/child evidence rather than deleting them all.

Never take only the first N phrases in catalog order. Use deterministic budgets and tie-breaks on stable IDs, disclose available/considered counts by song/section, and test reordering invariance. Progress/cancel must remain available for large requests. A canceled run must not masquerade as complete; partial results require an explicit label.

### 6.2 Event alignment with interpretable transformations

Initial preferred method:

- Enumerate a bounded set of constant transposition hypotheses from candidate note-pitch differences. Retain fractional tuning residuals; do not fold octaves or assume first notes correspond. Rank hypotheses by coherent support, not one pair.
- Run affine-gap **local event alignment** for each hypothesis. A bounded substitution cost uses transposed pitch residual and positive-duration/IOI ratio differences. Start with normalized channel costs and explicit missing-feature masks. Local IOI around an inserted ornament is unreliable: downweight that context and use the subsequent matched-anchor rhythm check below.
- Initial experimental reward `0.6 − substitution_cost`, affine gap penalty `0.5 + 0.15×(gap_length−1)`, and pitch/duration/IOI weights `0.6/0.2/0.2` are hypotheses for the development grid, **not product defaults or verified parameters**. Also test uniform gaps and global/semi-global alignment. Freeze the chosen values before held-out scoring.
- Trace back matched/substituted events and gaps. Require at least four matched targets for ordinary motif candidates; retain shorter gestures only as weak local/structural examples. Check aligned coverage against each reported motif span, not against the entire recording. Count matched fraction by targets and occupied time; long held notes must not hide missing attacks.
- Estimate the robust constant time scale from matched-anchor onset spacings and compare elapsed time, rests and held durations between successive anchors. Do not silently permit arbitrary local warping. Confirmed grids additionally provide beat-duration/phase deltas. Store both observed values and transformation residuals.
- Local alignment can discard a changed ending. Once an opening/core is supported, compare bounded surrounding phrase context with a constrained semi-global pass. Label a changed ending only if the opening has support and the divergent tail is visible. “The middle matches” must not become “the entire phrases match.”
- Return alternative near-optimal paths/transpositions when repeated tones or ornaments make correspondence ambiguous. Deterministic tie-breaking enables reproducibility but does not resolve musical ambiguity. Show uncertain links, not invented precise matches.

After a path is chosen, compute interval differences between **successive matched anchors**, naming skipped targets. This avoids treating an interval-token deletion as a proven note deletion. Forward/backward consistency and path margins are diagnostics, not calibrated correspondence probabilities.

DTW comparator: use `librosa.sequence.dtw` with custom multi-feature costs and bounded warp/steps. A contour-time warp is represented separately from event alignment. Many-to-one regions may show translucent spans/ambiguous groups; no fictitious one-to-one connectors. Pure rhythm alignment is its own lane and may link attacks while reporting differing pitches.

### 6.3 Scoring, quality and false-positive control

Expose a vector before any ranking scalar:

- Pitch residual and matched-anchor interval agreement.
- Contour direction/turning-point agreement.
- Relative IOI, duration and rest differences; beat-unit differences where eligible.
- Attack-count, insertion/deletion and matched-span coverage.
- Transposition, uniform time-scale and rhythmic displacement.
- Section/phrase role context, available context and unknown fields.
- Correspondence ambiguity and stability under perturbation/edition changes.

Choose separate ranking weights/thresholds for melodic, rhythmic and structural modes on development data. Report the final method/config ID. A missing rhythm grid is not a zero error, and a rhythm-only match cannot compensate for poor pitch agreement to become an exact melodic match. Low note confidence cannot make mismatches disappear: retain costs, flag quality and require enough supported anchors. Distinguish unavailable confidence from a genuinely low estimator score.

Do not display “87% confidence” from `1−distance`. Use observed match strength, transcription status, alignment ambiguity and supporting songs as separate labels. Exactness requires no gaps and agreement within declared numerical/tuning tolerances in the named representation. Global tempo scaling, changed rests and displaced entries must receive their own labels.

Control false positives using hard negative pairs matched for length, scale, range, interval inventory and rhythmic complexity; sample unrelated real melodies where labels permit. Also use constrained permutations preserving local distributions as diagnostic nulls, not proof of perceptual unrelatedness. Select a threshold using the **maximum candidate score per song pair/search**, not millions of correlated windows treated as independent tests. Report false discoveries versus search size, precision–recall and uncertainty at the song/family level. Reserve a separate exploratory list rather than guaranteeing every pair yields a match.

Musical commonness needs a reference corpus. With one, report song-level prevalence, sample sizes, missing sections and uncertainty; compare similarly sampled contexts and avoid treating each phrase as independent. Without one, show “commonness not assessed,” apply only a transparent low-complexity filter, and avoid “distinctive.” No finite sample-count rule alone establishes an artist signature.

### 6.4 Families, phrase construction and section habits

Represent occurrences as nodes and accepted interpretable matches as edges. Start with deterministic complete-link grouping or a medoid-plus-diameter bound over small candidate sets. Avoid unrestricted connected components: A≈B and B≈C does not imply A≈C. Keep bridge edges visible without merging dissimilar cores. Permit overlapping family membership where different submotifs justify it; report a shared core rather than pretending every occurrence has identical length.

Family ranking favors distinct-song support, alignment quality, meaningful coverage, stability and a limited number of representative occurrences per song. Repeated choruses in one song remain within-song evidence. Retain per-edge transformations; motifs can undergo several changes at once, so replace the single mutually exclusive `variation` label with a list of supported operations.

Level C combines motif roles and measured trajectories: opening recurrence plus changed tail, earlier/later peak, rhythm preserved with altered intervals, repetition followed by extension. Peak placement alone is a structural resemblance, not a motif family. Level D conditions these results on saved sections, averages occurrences/recordings within song first, and compares songs equally. Verse–chorus differences and pre-chorus→chorus transitions require paired eligible sections in the same song, chronological adjacency for transitions, and explicit missing-pair counts. Resample songs, not note windows, for uncertainty; two-song results stay descriptive.

## 7. Persistence, APIs and runtime architecture

Proposed new files, with narrow integrations:

- `src/song_catalog.py`: versioned explicit artist/song/source associations; reuse library classification and atomic writes.
- `src/melodic_identity.py`: input contracts, projections, candidate retrieval, correspondence and orchestration. Split into `identity_alignment.py` only if its tested DP code warrants a separate module.
- `src/identity_store.py`: immutable run snapshots, independent match/family reviews, cache validation and evidence lookup.
- `src/web/artist-identity.js` and scoped CSS: focused comparison controller; use `LearningRoll` and the existing transport.
- `tools/evaluate_identity.py`, `evaluation/identity/` manifests/config/splits, `tests/test_melodic_identity.py`, `tests/test_identity_store.py`, `tests/browser/identity.spec.cjs`.

New sidecars under `outputs/melodic-identity/{runs,cache,reviews}`; catalog under `outputs/musical-context/catalog`. Use versioned schemas, immutable result objects and append-only review revisions with optimistic concurrency. Keep current pointers as conveniences, not evidence identity. Unavailable/corrupt historical evidence must be shown explicitly; never fall back silently to the latest correction.

Cache keys include source hashes, exact note-edition fingerprints, phrase/boundary settings, selected passage bounds, section/grid/tonal revisions, catalog revision, algorithm/scoring version, search budgets and seed. Source title snapshots are for readable history; renamed titles must not merge identities. Changing context or corrections marks a run historical/stale; explicit recomputation creates a new run. Bookmarked findings/ideas retain their original evidence links.

Proposed actions following existing API style:

| Action | Contract |
|---|---|
| `identity-catalog-get/save` | Explicit associations, base revision, validations; reads never write. |
| `identity-start/status/cancel` | Selected editions, song pair/corpus scope, sections, method configuration; returns job/run ID and progress. Snapshot under lock, compute outside lock. Reuse import-job lifecycle concepts, not audio-import payloads. |
| `identity-run-get`, `identity-pair-get` | Immutable result and provenance, normalized views plus original source times, limitations and completeness state. |
| `identity-review-save/list` | Separate relevance/correspondence judgment and revision history. No change to reference review flags. |
| `identity-technique-save` | Evidence-pinned structural principle/constraint specification; allowed only from an actual finding, never a client-supplied fabricated conclusion. |

Keep legacy `profile`, `section-compare`, studies and saved ideas loadable. New `LearningStore` link union: legacy study link **or** identity run/finding link, versioned and server-resolved. No mass conversion. If a shared helper changes legacy behavior, retain compatibility mode and regression fixtures. No generator, model, transcription, raw audio, frozen benchmark or reference-schema changes are needed for the first release.

Performance targets to validate, not promises: first usable bounded two-song results within 5 s warm on the recorded Windows CPU for two ≤5-minute monophonic songs; progress within 250 ms; cancellation within 500 ms; warm cached open within 500 ms; bounded additional memory target 256 MiB. Publish exact note/candidate counts, hardware, median/p95 timings and truncation. Large corpora use pair-level cached background work; do not allocate an all-song unbounded distance matrix or hold the workspace lock during search.

## 8. Artist Identity UI and audible correspondence

### 8.1 Default workspace

Replace the default statistical profile presentation with a focused workspace, retaining the old data under **Advanced Statistics**:

1. Compact artist/song A/song B selectors, same-section filter, note-edition/quality summary and Find patterns action.
2. Short candidate list grouped as melodic families, rhythmic gestures, phrase construction and section contrasts. Show support and match kind before scores. Strongest evidence first; no tall stack of raw sequences.
3. One active comparison with song/section/source timestamps, concise similarity and difference statements, A/B controls, and **Learn this pattern**.
4. Side-by-side rolls; optional normalized contour overlay; collapsed diagnostics and provenance.

Empty states are actionable: one song → within-song study; unknown artist/song → confirm associations or compare recordings descriptively; no sections → whole-song/subphrase search still works; no grids → relative time/rhythm only; poor notes → review the affected passage; no matches → explain the thresholds/coverage and offer independent phrase comparison. Never populate an empty result with generic artist claims.

### 8.2 Visual semantics

- Every note retains its source ID. Hover/select a pair operation highlights both sides, original timestamps, pitch/interval and rhythm deltas. Insertions/deletions show on one side; ambiguous groups get dashed/shaded regions rather than confident connectors.
- Default pitch view: original pitches, with a switch to a declared estimated transposition. Do not anchor both first pitches automatically when an opening ornament is unmatched. Scale-degree view is eligible only with supplied local tonal context.
- Time modes: original source seconds; relative elapsed time; confirmed quarter-note beats; explicitly labeled phrase-progress/relative-duration normalization. Align matched core anchors. Show bar-phase displacement separately. Neither normalized drawing nor a DTW path modifies playback times.
- Contour overlay leaves rests as gaps and marks low-quality spans. A continuous F0 overlay must retain source timing and unvoiced gaps; symbolic target contour is distinct from vibrato/bends. Structural-only comparisons highlight relevant regions/peaks, not invented note pairs.
- Show the shared core and unmatched lead-in/tail, with an option to hear context. A local match should not visually imply the whole phrase is shared.
- Use labels/shapes alongside color, accessible keyboard selection and focus, shared zoom commands, sensible initial fit and side-specific source clocks. Test both 1366×768 and 1920×1080. Keep the editor visible while reading one finding.

### 8.3 Audio and navigation contracts

Use `VocalAudition` with source-aware A/B session keys. Before switching, cancel pending segment/metronome scheduling, resolve the exact audio source and await metadata/seek readiness. Use a generation token to prevent stale async A playback after choosing B. Snapshot/restore the main Study selection, source, viewport, paused position and independent composition state. Avoid replacing the user's open editor merely to audition a comparison if a read-only source context suffices.

Default A/B is sequential **original pitch and tempo**, with optional pre/post context and loop. Switching normalized visual modes does not alter sound. Side-specific source playheads use the inverse display transform. Matching scores cannot set playback speed implicitly. Common-tempo or pitch-shifted vocal playback is deferred; if later added, label it as transformed listening and validate artifacts separately.

Space and Play pause/resume the active context; Stop resets that context. Input focus suppresses shortcuts. Clicking piano keys stays clean reference audition. No delayed B playback after Stop, source change or tab exit. Section grid/metronome state is specific to the source, not inherited accidentally from the other song. Device latency remains a limitation, not something a visual alignment can certify.

## 9. Learn This Pattern: evidence to independent composition

Carry an immutable principle/exercise link containing the match/family/structural finding, both source examples, observed transformation, limitations and optional user-accepted meter/tempo. Start with a blank idea or the user's selected existing motif; never insert source notes. The user's key, phrase length, range and chords remain independent.

| Supported finding | Original-motif experiment | Immediate measured feedback |
|---|---|---|
| Similar opening, changed ending | Mark an original motif and answer; preserve some opening motion, change the tail. | Align the user's own two regions; show stable opening and changed intervals, rather than splitting the note list in half. |
| Same contour, different interval sizes | Draw own gesture; widen/narrow one leap within comfortable range. | Direction/turning-point retention and changed leap size; no quality grade. |
| Related rhythm with different pitches | Keep own attack-spacing pattern; choose a different contour or ending. | IOI/duration/rest comparison, separate from pitch similarity. |
| Later peak / extended phrase | Move the peak or extend an original answer; add a rest if desired. | Peak position, range and extra attacks/beats; tied peaks displayed honestly. |
| Repeated targets versus sustained target | Try repeated attacks and one longer held version of own pitch. | Attack count and occupied duration differ; do not erase the distinction. |
| Section-specific build with actual support | Choose own phrase length and create the observed general density/peak progression. | Explicit windowed density/peak constraints and missing-context warnings. |

Reuse existing draw/drag/resize, keyboard reference, undo/redo, saved idea revisions, export, range/key/chord settings and user-motif transforms. Add marked motif/answer regions and optional operations for interval scaling, moving a peak, extending/shortening and changing an ending. Preview and undo transformations; never silently quantize or force a scale when the user has chosen otherwise.

Provide **Hear source A**, **Hear source B**, **Hear my idea**, and **Return to comparison** without losing unsaved work. Compare structural descriptors rather than rewarding proximity to the source. If harmony is absent, key adaptation is a creative choice, not a source-derived harmonic analysis.

Retain existing `source_similarity` warnings and, after separate validation, add optional new matcher warnings for insertions/ornamented resemblance against **all linked sources**. Show the excessive-similarity passage and invite changes to both rhythm and contour, rather than suggesting transposition alone makes it independent. No similarity check establishes legal originality or artistic quality. Do not change legacy generation algorithms as part of this work.

## 10. Scientific validation plan

### 10.1 Data tiers, provenance and licensing

| Tier | Purpose and available evidence | Limits / handling |
|---|---|---|
| Controlled synthetic symbolic motifs | Known event correspondences under exact transposition, timing scale, insertions/deletions, ornament-like targets, repeats and changed endings. Construct diverse bases and matched-complexity negatives. | Tests the specified transformation, not perceptual identity or singing accuracy. All variants of one base stay in one split. |
| MTC-ANN 2.0.1 | 360 annotated melodies in 26 tune families; melody similarity and motif annotations make this the preferred external symbolic family/retrieval benchmark. | Folk tune families are not contemporary singer identity. CC BY-NC-SA 3.0; keep optional research artifacts and attribution separate, do not bundle into a commercial product by default. Inspect actual annotation coordinates before claiming exact note-link truth. [Publisher documentation](https://www.liederenbank.nl/mtc/). |
| JKU/MIREX repeated-pattern material | Optional within-piece recurrence benchmark and established pattern/occurrence metrics. | Within-piece task does not validate cross-song identity; small classical symbolic/synthesized examples differ from vocals. Download availability and archive-specific redistribution permission remain unverified; no package is approved for bundling. [Official task/results description](https://music-ir.org/mirex/wiki/2013%3ADiscovery_of_Repeated_Themes_%26_Sections_Results). |
| Existing Vocadito references/predictions | Sensitivity of matching/features to real transcription errors and disagreement between two published note editions. Publisher supplies 40 solo-vocal excerpts, F0 and two musician note annotations. | No cross-song motif truth; do not invent family or artist labels. Use existing pinned local license/provenance (documented CC-BY-4.0) and frozen splits; new experiments write separate artifacts. [Publisher record](https://zenodo.org/records/5578807), local `docs/REAL_VOCAL_VALIDATION.md`. |
| User-authorized songs with musician review | Real A/B relevance and selected correspondence checks, section labels and beat confirmation. | No labels currently establish matches between the two personal recordings. Annotation must be provided by humans; absence blocks a human-validity claim, not implementation of the review workflow. |

MTC offers precomputed feature sequences as a possible lightweight adapter input; inspect license, note order, timing and motif-ID mapping before deciding between those and MIDI/**kern. Do not require music21 or another large parser for the first baseline. [Author-maintained MTCFeatures documentation](https://pvankranenburg.github.io/MTCFeatures/basicusage.html).

`mir_eval.pattern` provides establishment and occurrence evaluation, but its conventions and transposition handling differ by metric. Use it only with compatible pattern inputs; do not claim it directly measures fuzzy cross-song alignment. Add explicit event-pair precision/recall and retrieval metrics for this task. [mir_eval pattern API](https://mir-eval.readthedocs.io/latest/api/pattern.html).

### 10.2 Splits and reproducibility

- Freeze manifests by original musical work/base motif and tune family before tuning. All crops, transpositions, performers, encodings, reference editions and model variants of related material stay together. Use family-disjoint development/validation/test for generalization; keep multiple members of each held-out family together for retrieval evaluation.
- Define query/gallery and eligible positives explicitly; remove identical-source and same-work duplicates from “cross-song” evaluation. No first-N file selection or best-model/reference-edition cherry-picking.
- Version configuration, thresholds, split seed, transformations, candidate budgets, ground-truth conventions and licenses. Hold out entire bases, not randomized windows. Log dependencies/hashes and all failed ablations.
- Published family labels are not exhaustive negative motif labels: different families may share a local conventional pattern. Distinguish unannotated from confirmed negative; use graded musician review for top-ranked false positives.
- Existing transcription heldout data can be reused only as a fixed retrospective sensitivity report without further tuning. A new motif benchmark needs its own predeclared heldout split. Do not overwrite frozen results.
- Blind relevance review should include candidate rank/algorithm hidden, random negatives, an uncertain option and separate ratings for melodic/rhythmic/structural similarity. Two reviewers where feasible; report agreement and disagreements. This task performs no human review.

### 10.3 Test matrix and metrics

| Case | Required check / metric |
|---|---|
| Constant pitch shift, fractional tuning, uniform tempo changes | Retrieval recall@K, correct transposition/time scale, invariant feature path, exact composite source IDs. |
| Contour same but interval sizes different | Classified as contour/structural or melodic variation, not exact recurrence. |
| Duration changes, rests and displaced entries | Separate duration/IOI/rest costs; zero-score unequal-rest regression; shift in bar phase visible only with eligible grids. |
| Insert/delete targets, short ornaments, repeated versus held notes | Event-pair precision/recall/F1, insertion/deletion classification, matched coverage, ambiguous-group handling. |
| Changed ending, expansion/contraction, different phrase lengths | Recover shared core while showing divergent context; do not force tail alignment or call every insertion expansion. |
| Rhythm same, pitch different | Rhythm retrieval precision/recall, pitch differences exposed, no false melodic label. |
| Unrelated and generic hard negatives | Pair-level false-positive rate, precision@5/@10, PR curve, false discoveries versus search budget; show high-scoring errors. |
| Families | Pairwise/B-cubed family precision/recall as appropriate, overmerge/split rates; correctly count songs/works, not versions; nested motif behavior. |
| Partial passages/sections | Boundary localization and source-time error; retrieval overlap/rank stability with ±50/100/250 ms and ±1-note perturbations; censor flags and abstention. |
| Transcription uncertainty | Compare reference-edition and prediction retrieval lists, path changes and false matches; pitch ±semitone/octave, fragmentation, merges and missing rests tested separately. |
| Grid uncertainty | Offset/BPM perturbation sweeps over declared scenarios; provisional/out-of-coverage grids never produce beat-phase claims; preserve relative-rhythm availability. |
| Attribution and deduplication | Correct song/source/edition/revision for every occurrence; 100% on deterministic fixtures; same work/take/model never inflates cross-song support. |
| Structural and section claims | Known synthetic role/peak/density contrasts recovered; paired denominators, exceptions and equal-song weights tested; no harmony/intent invention. |
| Runtime | CPU wall time, peak process memory, candidate counts, cache hit, progress/cancel latency; deterministic ordering under input permutation. |

For ambiguous human alignments, score against annotated acceptable links/groups or exclude explicitly uncertain regions with coverage reported. Do not grade a chosen deterministic path as the only truth. Use song/family-level confidence intervals where sample size allows; report counts and raw error cases for small sets.

### 10.4 Proposed release gates

These are targets to freeze before implementation evaluation, not results:

- All contract/invariance/identity/coverage/preservation fixtures pass; exact synthetic transposed copies recover all annotated core targets under declared search bounds.
- Development selects an operating point targeting at least 90% precision among surfaced candidates. Held-out results must report both uncertainty and retrieval recall; if precision cannot be supported, keep discovery labeled experimental and expose manual comparisons instead of strong ranked claims.
- For controlled single insert/delete and timing transformations: initial target ≥0.90 event-correspondence F1 and ≥0.90 recall@5, reported per transformation rather than pooled to conceal failures. Difficult compound transformations have separate stress results.
- On a preregistered negative pair set, target ≤5% of unrelated pairs producing any strong candidate at the configured budget. Generic conventions and uncertain real negatives are reported separately. Never retune the threshold after reading heldout failures.
- No claim of perceptual relevance or artist specificity passes without appropriate human/reference-corpus evidence, regardless of synthetic scores.
- A failed optional matcher/embedding ablation cannot delay the functioning interpretable pairwise baseline; document its failure rather than presenting its adapter as validated.

## 11. Unit, integration, browser and audio acceptance

Add tests in the repository's current unittest/Node/Playwright setup; use disposable isolated fixtures for all mutations. Browser tests remain muted/headless and never disturb the desktop. Run both existing desktop sizes. Preserve the full existing suite, including the independent playhead/selection tests.

1. Select two fixture songs with known inserted/transposed motifs, choose editions, search, and display exact source IDs/timestamps. Repeat with two model versions and with two recordings assigned to one song; support does not increase.
2. Select a candidate by real pointer interaction. Matched notes highlight on both rolls; insertions, omissions and changed tails display correctly. Structural-only pairs show regions, not fabricated note connectors.
3. Toggle original/transposed/relative-time/beat views and zoom/pan; source events and playback bounds remain unchanged. Out-of-coverage confirmed maps cannot enable beat-normalized claims. Different meters and pickup phases are explicit.
4. Hear A then B, loop either, pause/resume mid-excerpt, Stop during loading/transition, seek, switch song and change workspace. Measure actual decoded/audio-bus signals: fixture sources with distinguishable known content verify correct source and segment; RMS/signal capture verifies no duplicate engine or leftover playback. Test timestamp routing separately from subjective listening quality.
5. Keep A and B voices at original pitch/tempo in normalized views. Reference piano remains independent. Metronome uses the active source's saved map and does not leak across contexts. Retain existing audio-latency caveats.
6. Open Learn this pattern, draw own motif/answer with pointer gestures, alter intervals/rhythm/ending, hear/check it, save/reload/export. Verify source notes were never inserted, constraints refer to the user's marked regions, and return to either source preserves unsaved/saved ideas.
7. Review a candidate as unrelated/uncertain, reload and inspect history. Reference attestation, model predictions and artist membership remain unaffected. Stale writes fail with a useful recovery path.
8. Changing correction/section/grid/catalog revision invalidates current derived results but leaves a saved run and linked idea reproducible. Missing original audio shows unavailable playback without substituting another recording. Dirty editor state is not discarded during A/B.
9. Keyboard commands ignore text input; selected passage survives seeking; no JS exceptions; short candidate list and active rolls remain usable at both sizes. Empty/failed/canceled jobs show actionable state.
10. Read-only personal integration: open MHS and the other recording, load actual events and audition original spans, with mutating API calls blocked. Do not assert a match, identity, section or beat confirmation that has not been established. Demonstrate the full labeled journey on disposable fixtures until the musician supplies real associations/context/reviews.

Before implementation, record a fresh preservation manifest for originals, predictions, corrections, references, context revisions, ideas, profiles and frozen evaluation outputs. Compare hashes after tests; use existing integrity tooling and frozen re-scoring where appropriate. No scientific benchmark is regenerated merely to update a UI test. Record screenshots of actual application states, browser reports, audio measurements, failures and remaining limitations; unit tests alone do not validate musical/audio behavior.

## 12. Manageable implementation stages and completion criteria

| Stage | Deliverable and affected files | Completion gate |
|---|---|---|
| **I0 — Identity and benchmark contracts** | New catalog/identity schemas; adapter over `schema.py`, `library.py`, `musical_context.py`; benchmark manifests and tests. Preserve legacy motif baseline. | Explicit two-song versus same-song/variant distinctions; edition/carry/coverage contracts; read-only legacy loads; frozen split/config and integrity manifest. |
| **I1 — Pairwise correspondence engine** | `melodic_identity.py` / optional `identity_alignment.py`; compare exact/interval/edit/DTW baselines; new unit and evaluation runner. | Transposition, rests, inserted targets and embedded motifs yield traceable paths; hard negatives and abstention measured; no changes to old model/generator APIs. |
| **I2 — Two-song comparison vertical slice** | `identity_store.py`, narrow workspace actions, `artist-identity.js`, `LearningRoll` overlay, transport/session integration, markup/scoped CSS. | Choose two songs → ranked candidate → correct original A/B → visible correspondence works at both sizes, with actual signal verification and progress/cancel. This is the first useful product milestone. |
| **I3 — Families and musical context** | Family grouping plus Level C/D descriptors; integrate `features.py`, context store, source-identity adapter and read-only profile views. | Within/cross-song counts correct; no chaining overmerge; supported phrase-construction and section contrasts with equal-song weights, beat gating, exceptions and meaningful empty states. |
| **I4 — Learn This Pattern** | Versioned multi-source links in `learning_store.py`; explicit own-motif regions and narrowly scoped checks/transforms in `learning.py`/frontend. | Blank/user-owned idea, structural experiment, live feedback, original-source return, save/reload/MIDI export and unsaved-state preservation all pass. Legacy ideas/generation behavior preserved. |
| **I5 — Validation and release** | Benchmark reports, human review protocol, usage guide, screenshots/audio/browser results; default Artist Identity presentation with Advanced Statistics. | Frozen heldout scoring and limits published; full regressions/integrity checks pass; human claims reflect actual review; responsive end-to-end workflow demonstrated. |
| **I6 — Optional later investigations** | Larger licensed reference corpus; variable-tempo support from section/beat roadmap; learned retrieval/advanced target grouping if justified. | Measured benefit over frozen baseline on new heldout data, licenses/resources documented, interpretable correspondence retained. No two-song neural training. |

Dependencies: I0 → I1 → I2. I3 relies on stable pairwise evidence and context coverage, then I4 uses those findings; a simple Level A/B learning handoff can be validated during I2 without waiting for all structural aggregations. I5 includes regression checks throughout, not only at the end. Do not postpone source-pair listening until after corpus-scale clustering.

Existing NumPy/SciPy/librosa, stdlib JSON/dataclasses, Web Audio/Canvas and installed Playwright are sufficient for the baseline. `mir_eval` remains evaluation-only. No new server framework, vector database, GPU runtime, embeddings package or dependency installation is required by the proposed first release.

## 13. Risks, unresolved questions and honest limits

| Risk | Mitigation / release boundary |
|---|---|
| Incorrect notes create convincing recurring artifacts | Pin editions, show quality/unknown confidence, compare sensitivity, permit review; do not infer accuracy from agreement. |
| A cappella timing or imperfect fixed grids imply false groove | Separate rhythm shape/placement; require saved confirmed coverage; report perturbation and onset-definition limitations. Variable tempo remains later work. |
| Added ornamental note destroys interval adjacency | Event-level path with gaps and matched-anchor interval explanations; retain alternatives and original targets. |
| Trivial scales/repeats dominate retrieval | Multi-channel hard negatives, minimum evidence/coverage and commonness caveat; optional reference corpus rather than unsupported distinctiveness. |
| Pairwise similarity overmerges unrelated families | Complete-link/diameter constraints, explicit graph edges, medoid and bridge inspection; stable IDs/tie handling. |
| Multiple versions or naming changes inflate songs | Explicit catalog membership, one edition per source, work/take relationships, independent occurrence and song denominators. |
| A/B plays the wrong recording or loses an idea | Source-aware session tokens, pinned evidence, audio signal tests, dirty-state snapshots and no independent audio engine. |
| Large search blocks uploads or returns early-file bias | Snapshot outside long locks, deterministic per-pair budgets, progress/cancel, cached projections and disclosed truncation. |
| Public family annotations are treated as modern singer truth | Keep dataset/domain/label type explicit; synthetic and symbolic results separate from vocal/human relevance. |
| Unreviewed similarity becomes an emotional or authorship story | Structured measured/interpretive/creative categories; explanations generated from verified operations, no unsupported narrative. |

The current personal recordings need musician-confirmed song/artist associations, optional sections and beat coverage before section-specific artist conclusions are possible. They can still be opened and compared descriptively without a reviewed transcription. A human judgment that two passages are meaningfully related cannot be manufactured from a similarity threshold.

The desired completion demonstration is: choose two confirmed distinct songs → discover a defensible candidate (or receive an honest no-match result) → hear both exact source passages → see matched, changed and uncertain targets → understand a bounded musical principle → develop and save an independent motif using it. Establishing artistic influence, authorship, recognizable copying or legal originality remains outside the system's evidential scope.
