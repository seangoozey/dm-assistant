---
id: TKT-0102
title: Define truth-aware relevance scoring and comparative benchmarks
status: in-progress
priority: P0
milestone: shared-campaign-knowledge
depends_on: []
created: 2026-09-10
updated: 2026-09-10
---

# TKT-0102: Define truth-aware relevance scoring and comparative benchmarks

## Outcome

Executable retrieval policy and comparative tests, before more ranking heuristics or grouping. Delivery slice of TKT-0090, TKT-0091 and TKT-0094, not a replacement for them.

## Scope

- Define a versioned score-components dictionary separating semantic relevance, relationship/path strength, evidence support, independent-source support, task-dependent truth suitability, and feedback. Document missing-value handling and normalization; feedback absence is neutral, not negative evidence.
- Keep truth state, authority, visibility, temporal scope, attribution and source identity as categorical metadata. Calculate truth suitability at query time, not as a permanent hierarchy attached at ingestion.
- Define purposes for factual Ask, brainstorm, encounter preparation/run, and conflict comparison. Distinguish hard eligibility rules from soft ranking: hidden/stale evidence cannot be rescued by any score; planned outcomes cannot support an answer about completed events.
- Preserve each supporting passage's dimensions along a path. A mixed-state path has no automatically promoted overall truth state. Relevance never constitutes authority or conflict confirmation.
- Freeze a baseline and pairwise relevance fixtures: organizational and causal evidence should outrank incidental room-layout associations when the question warrants it. Include Romulus/Sorin/Eustice and Arkin/Monastery examples, unrelated-name equivalents, paraphrases, high-degree entities, ambiguous identity and counterexamples. Do not require particular names in positions 1 or 2 or even a fixed top ten.
- Separate missing-index coverage from ranking failure; include gold support passages but never feed gold paths or expected rankings to the extractor.
- Inspect interrupted, undeployed graph_relevance heuristic changes before implementation; retain only changes justified by this contract and tests. Do not silently deploy them.

## Acceptance

- [x] Purpose/eligibility/score contract documented with missing-value behavior and provenance.
- [ ] Pairwise ranking, recall@k and precision@k baseline recorded; numeric success thresholds frozen before tuning, with held-out cases.
- [x] Tests prevent hidden-path score leakage and mixed-state promotion; existing Core authority checks still own factual support.
- [x] Grouping is explicitly excluded as a ranking substitute.

## Validation and documentation

Extend existing shared-knowledge benchmark and policy tests; record baseline artifacts. Read shared-campaign-knowledge.md and ADR-0014/ADR-0012 before implementation. Propose any architectural amendment separately; this ticket does not change existing canonical rules.

Implemented isolated relevance-v1 scorer and 11 passing policy tests; no live integration. Eight-case synthetic pairwise corpus and frozen lexical diagnostic added, with four held-out cases. Existing larger shared-knowledge corpus remains required for acceptance. A real exported-walker/native comparison is still required; this small lexical diagnostic must not be called the current app baseline. See docs/architecture/relevance-contract.md.

Clean isolated native Cognee diagnostic completed: all 13 synthetic records indexed, but held-out pairwise performance is 3/4, below the frozen 80% gate. Organizational two-hop retrieval still misses the target passage. The returned ten edges include structural/type/chunk edges: this is not evidence that the desired relationship was absent from the graph. See docs/architecture/relevance-native-diagnostic.md. Conservative budget accounting now $0.549507 against $2 cap (increment $0.013311), 1,447 attempts, no unsettled reserve. No live deployment or canonical writes.

Follow-up: isolated `deploy/evaluation/evidence_paths.py` exercises bounded two-hop traversal with evidence on every edge, inverse navigation without predicate reversal, structural-edge exclusion, cycle/fanout/total limits, and fail-closed visibility/revision/time/identity checks. Ten traversal cases plus existing isolated tests: 32 passed. This is a known-link safety harness, not model-discovered path validation or a replacement for the current app baseline. V1 organization fixtures still need explicit bridge evidence before they can measure path recall. No additional provider calls in this follow-up.

2026-09-10 offline follow-up (no provider calls, budget unchanged at $0.549520 accounted against the $2 cap): inspected the interrupted `graph_relevance` cluster (`application/graph_pilot.py` target scoring, `RetrievedEvidence.graph_relevance`, `campaignClient.ts` type, `App.tsx` ranking term) and removed it as not accepted by the relevance contract. Trace selection is deterministic first-match; the pilot traversal, traces, shared-source context, and the tested React graph-context behavior are retained. Campaign Core suite now 446 passed/36 skipped (previously 440 passed plus the path-expectation failure in `test_graph_pilot.py::test_reverse_two_hops_find_text_without_search_name` — resolved); React 72 passed with `tsc --noEmit` clean; the 18 isolated projection/chunk/path tests still pass. Added versioned explicit-bridge corpus `tests/fixtures/relationship_relevance_cases_v2.json` (17 records, 10 cases, 5 held out; explicit `company-bridge`/`warden-bridge` records; three absent-bridge negative pairs; explicit entity tokens per record) plus `evaluate_v2`/`fixture_v2_invariants` in `campaign-core/tests/support/relevance_benchmark.py`. Record coverage, bridge coverage, returned-path coverage, and false-bridge claims are now separate reported signals, with five new tests proving the separation. Frozen lexical v2 baseline recorded at `tests/fixtures/relationship_relevance_baseline_v2.json`; lexical still fails both organizational pairwise cases and returns no paths — an honest diagnostic, not a production baseline. The exported-walker/native comparison on this corpus (TKT-0104) and weighted indexing (TKT-0103) remain outstanding, so the second acceptance criterion stays open until that comparison is recorded against these frozen fixtures.
