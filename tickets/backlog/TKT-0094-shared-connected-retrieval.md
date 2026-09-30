---
id: TKT-0094
title: Implement ranked passage and connected evidence retrieval
status: blocked
priority: P0
milestone: shared-campaign-knowledge
depends_on: [TKT-0091, TKT-0092, TKT-0093]
created: 2026-09-06
updated: 2026-09-28
blocked_by: the final decision on graph infrastructure and implementation (TKT-0105's track; ADR-0014 remains proposed)
---

# Outcome

Implement the shared Campaign Core knowledge query contract — the **graph service** — and make existing retrieval/query a compatibility adapter.

## Context (ruling 2026-09-28)

Sean's ruling: **the graph service is foundational to the completion of this project.** It is not optional polish and not merely a shared-campaign-knowledge milestone — connected, ranked evidence retrieval over the relationship graph is the end-state retrieval architecture. The ONLY unresolved question is concrete implementation: which infrastructure carries it (Cognee as-is, Neo4j after TKT-0105's decision, or a Postgres-native index after TKT-0103) and how the contract is implemented on top. This ticket is therefore BLOCKED on that final infrastructure/implementation decision — not on importance, not on the contract's design (ADR-0014 + the shared-campaign-knowledge doc define it), and not on its dependencies (0091/0092/0093 are done). Current direct-read retrieval (lexical /ask + evidence search) remains the working baseline until this lands.

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
