# Native Cognee relevance diagnostic

Status: isolated diagnostic, not production acceptance. TKT-0102/0104.

## Setup

Cognee 1.5.3, 13 clean synthetic records, eight frozen queries (four held out), native GRAPH_COMPLETION with only_context=True, verbose=True, top_k=10. Expected judgments were not included in provider input. This uses default extraction, not the future weighted projection. Source ranking maps returned edge endpoints to shared original passages; co-occurrence alone does not prove a semantic relationship.

Full local artifact: `.local/cognee-evaluation/relevance-v1-report.json`. Isolated store: `.local/cognee-evaluation/relevance-v1`. No live graph replacement.

## Results

All 13 records were indexed. Development pairwise: 2/4. Held-out pairwise: 3/4 (75%, below 80% gate). Causal and layout examples worked; both organizational examples missed the second-hop passage. These small judged-pool results cannot establish production quality or justify a backend replacement.

For the organization query, nine of ten returned edges did not map to a shared original passage. Returned edges included chunk/entity links and Romulus-to-type links (person, entity, character). The remaining edge was Romulus-to-Inquisition, mapping to the command passage. The Sorin/company passage exists in the index but was not returned. Therefore the observed failure is not missing record coverage: structural edges consume retrieval capacity, and semantic seeding alone does not establish useful multi-hop traversal.

## Next controlled comparison

1. Preserve this unfiltered baseline; do not silently relabel it as weighted or production retrieval.
2. Retrieve a bounded larger candidate pool, distinguish semantic relationships from structural/type edges using actual graph metadata, then traverse supported semantic paths. Record raw ranks, edge properties, direction and every supporting passage.
3. Compare identical queries and indexed evidence against the exported walker. Do not inject expected paths or character-specific boosts.
4. Validate edge-level provenance separately: shared endpoint co-occurrence is an association, not sufficient relationship evidence.
5. Repeat held-out evaluation without retuning against its labels; expand the corpus before acceptance.

Cost increment was $0.013311 in the conservative ledger, taking total accounted usage to $0.549507 against the existing $2 cap. No unsettled reserve at completion. This is local accounting, not a fresh provider account balance.

## Expanded candidate-pool diagnostic

A second search-only run used top_k=100 against the same store, without re-ingestion. Development pairs became 4/4; held-out pairs remained 3/4. Many irrelevant passages also entered the top ten. Increasing the candidate pool recovers the company passage but is not a quality fix by itself. Cost accounting increased to $0.549520 (eight additional requests).

Graph inspection exposed a fixture limitation too: the company passage names Inquisitor Eustice, but never explicitly connects his company to the Inquisition. The Wardens example similarly relies on a Warden/Wardens interpretation. Indexed-record coverage therefore does not establish complete *path* evidence. Preserve v1 as a diagnostic; before testing traversal, create a versioned corpus with explicit, independent bridge evidence and separate absent-bridge cases. Do not fabricate a live campaign relationship or treat title similarity as a proven link. The organizational pair scores above are relevance judgments, not demonstrated graph-path recall.

That versioned corpus now exists as `tests/fixtures/relationship_relevance_cases_v2.json` (explicit `company-bridge`/`warden-bridge` records, three absent-bridge negative pairs, per-record entity tokens, offline fixture-invariant tests), with the record-versus-path coverage distinction reported separately by `evaluate_v2` and a frozen lexical v2 baseline. The native/traversal arms must be re-run against this corpus before any path-recall claim.
