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
