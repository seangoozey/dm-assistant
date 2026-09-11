---
id: TKT-0094
title: Implement ranked passage and connected evidence retrieval
status: backlog
priority: P0
milestone: shared-campaign-knowledge
depends_on: [TKT-0091, TKT-0092, TKT-0093]
created: 2026-09-06
---

# Outcome

Implement the shared Campaign Core knowledge query contract and make existing retrieval/query a compatibility adapter.

## Required reading

- [Shared Campaign Knowledge](../../docs/architecture/shared-campaign-knowledge.md)
- [ADR-0014](../../docs/decisions/ADR-0014-shared-campaign-knowledge.md)
- [ADR-0012](../../docs/decisions/ADR-0012-provenance-first-claims.md)

## Scope

Rank names and indexed passages before truncation; accept explicit seeds, purpose, visibility and time filters. Expand bounded paths with cycles/fan-out limits. Return match offsets, parent assertions, evidence IDs, citations, path explanations and freshness metadata. Revalidate current truth at read time.

## Acceptance and validation

Cross-workflow benchmark beats frozen baseline on relevance targets; no hidden path leakage or invented transitive facts; entity-free claims stay discoverable; high-degree nodes cannot crowd out direct matches. Test API compatibility and deterministic ordering.

## Migration and rollback

Feature-gate new retrieval adapter and retain direct-read fallback; indexes rebuild from immutable/canonical inputs.
