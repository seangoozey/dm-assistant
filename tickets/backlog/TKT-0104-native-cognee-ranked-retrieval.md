---
id: TKT-0104
title: Evaluate native Cognee relationship retrieval against the current walker
status: backlog
priority: P0
milestone: shared-campaign-knowledge
depends_on: [TKT-0102, TKT-0103]
created: 2026-09-10
updated: 2026-09-10
---

# TKT-0104: Evaluate native Cognee relationship retrieval against the current walker

## Outcome

Determine whether supported Cognee retrieval yields useful ranked relationships. Delivery slice of TKT-0094/TKT-0096; grouping remains deferred.

## Scope

- Compare lexical baseline, current exported-graph walker, and native semantic node/edge/triplet retrieval on the same corpus.
- Retrieve a broad candidate set before truncating; evaluate supported neighborhood controls and best-path selection instead of first-path/iteration-order selection.
- Apply TKT-0102 task-aware scoring. Verify actual native score semantics, including whether a value is similarity or distance; do not treat feedback_weight or an arbitrary edge weight as universal relevance.
- Preserve structured source and path identifiers. Resolve source text and eligibility through Campaign Core before returning results. Raw model edges can suggest evidence, not independently support answers.
- Expose complete paths and a developer-inspectable score breakdown so Aris-like indirect associations are understandable without implying unobserved orders or causation.
- Pass ranked results/scores through shared API and UI without client-side arbitrary reordering. Keep explanation detail unobtrusive for normal campaign use.
- Measure latency, provider usage, repeat-run variance and failure behavior. No answer-generation call is required merely to list source-backed discoveries. Cache only with identity, visibility, purpose and source-generation boundaries.

## Acceptance

- [ ] Reproducible comparison satisfies frozen relative-relevance thresholds on held-out fixtures without named boosts.
- [ ] Path explanations identify supporting passages and retain limitations/modality.
- [ ] Read-time freshness and visibility gates hold; provider outage leaves baseline usable.
- [ ] Browser order matches ranked API order; grouping does not mask poor ranking.
- [ ] Cost, latency, configuration and remaining failures recorded, including coverage failures separately.

## Rollout

Feature-gated evaluation first. Do not replace live retrieval until measured acceptance; retain rollback to baseline. A failed evaluation triggers TKT-0105, not endless local heuristics.

## Prep complete (2026-09-13, free/local)

- **Bundle v5** (`deploy/evaluation/build_canonical_bundle.py --generation live-pilot-v5`, compose mount switched): 448 records / 118 entities / 4,325 edges — adds **23 `member_of` edges** (audited rosters, role titles as attrs) and **2 `leader_of` edges** (unique seats: Grand Inquisitor; Leader of the Rebellion) to the existing contains/co_mention graph. Oracles→Merghana membership retained as audited truth.
- **Traversal fix** (`graph_pilot.py`): adjacency previously required a shared claim for every entity-entity edge — right for co-mentions, wrong for roster seats, which stand on their DM decision receipt. `member_of`/`leader_of` now traverse without shared text, with self-describing hops ("Romulus holds Grand Inquisitor in Inquisitors"). Test `test_roster_edges_traverse_without_shared_claims`; 461 local tests pass.
- **Verified live**: "Inquisitors" query reaches 18 evidence records through roster edges (both seated hops); Brainstorm retrieval healthy on v5.
- Remaining before the paid re-index: confirm the frozen v3 relevance judgments (or re-score against the completed identity set), then the budget-gated run itself (needs Sean's spend authorization).

### Comparison completed on confirmed judgments (2026-09-13/14)

Judgments confirmed by Sean (corpus `judgment_status` → `confirmed_by_sean_2026-09-13`). Arms measured on the six cases:

| Arm | Pair-correct | Notes |
| --- | --- | --- |
| Deployed stack (lexical + v5 walker) | 2/6 | loses causality + plans to the lexically dense tower distractor; graph context ranks behind lexical hits |
| Native Cognee weighted-manifest join | **4/6** | wins causality and plans (semantic ranking beats lexical density); retrieves the pronoun-subject claim with zero graph edges |
| Repeat-run variance (native) | 0 | 6/6 identical rankings across two runs |
| Run cost | — | search-only pass: $0.000008; cumulative ledger $0.503758 |

Both arms fail identically on `core-complaint` and `organization`: the grand-inquisitor record (semantically the top answer for bare "Romulus") ranks ~20th in both — recorded as the residual failure class. Limitation stands: small judged-pool diagnostic (40 records, 6 cases), not production acceptance. Next options: expand the judged pool for a stronger gold standard, or advance to the TKT-0105 backend decision with this diagnostic as evidence.

### Free-arm measurement (2026-09-13, deployed stack vs draft judgments)

Scored the six draft v3-live judgments against the **deployed** retrieval stack (full 448-record corpus — a harder test than the 40-record slice the protocol designed): **2/6 satisfied**. Passes: layout-counterexample (38 vs 153), monastery (11 vs 109). Failures are all ranking losses to the designated distractor `tower-description` (ranks 18–20) over the preferred Romulus records (27–73). Diagnosis: lexical density dominates — the long tower lore record matches Romulus queries strongly, while graph-traced context arrives appended behind lexical hits rather than interleaved by relevance; `romulus-shadow-rule` (whose text never names Romulus — "He…") has **zero graph edges** (whole-word linking cannot anchor pronoun-subject claims) and only surfaces at rank 73 via an Infinite Twilight hop. These are precisely the cases the native semantic arm (paid, awaiting confirmed judgments) is meant to test. Scoring artifact fixed en route: corpus records were length-capped at export, so record matching now anchors on tail slices. Budget ledger: $0.503750 recorded against the ~$3 key / $2 gateway guard. The six judgments remain `draft_pending_sean` — extracted in full in the 2026-09-13 session for confirmation.

### Ruling (Sean, 2026-09-14)

The graph question is parked as **promising, but not fully ready for a real test yet**. No semantic re-index spend, no TKT-0105 advancement, and no judged-pool expansion for now. The diagnostic stands as recorded (native 4/6 vs deployed 2/6, zero variance, $0.503758 cumulative); the recall-for-consideration lens is the product bar. Revisit after the DB-completeness front settles (descriptions/TKT-0111, rosters, identities through normal use) — every DB improvement strengthens the derived graph for free on rebuild.
