---
id: TKT-0095
title: Connect every campaign workflow to shared knowledge
status: blocked
priority: P0
milestone: shared-campaign-knowledge
depends_on: [TKT-0094]
created: 2026-09-06
updated: 2026-09-28
blocked_by: TKT-0094 (the graph service implementation, itself blocked on the infrastructure decision)
---

# Outcome

Connect every campaign workflow — Ask, the encounter runner, Lore preparation, Brainstorm, the Library, and session-note navigation — to the shared knowledge service (the graph service, TKT-0094).

## Context (ruling 2026-09-28)

Sean's ruling: the graph service is **foundational to the completion of this project**; the only unresolved question is its concrete implementation. This consumer-integration ticket follows the engine: BLOCKED behind TKT-0094, which is itself blocked on the final graph infrastructure/implementation decision (TKT-0105's track). Note for when it unblocks: Lore creation now goes through the Promotion Pipeline's mandatory review (ADR-0018; the retired TKT-0040's "conflicting Lore input" scenario is a retrieval scenario, never an auto-application one) — retrieval feeds the review; it never writes.

## Required reading

- [Shared Campaign Knowledge](../../docs/architecture/shared-campaign-knowledge.md)
- [ADR-0014](../../docs/decisions/ADR-0014-shared-campaign-knowledge.md)
- [ADR-0012](../../docs/decisions/ADR-0012-provenance-first-claims.md)

## Scope

Remove page-specific ranking/path logic. Preserve excerpt highlighting and exact evidence pins. Encounter context preserves reading and note state. Lore comparison uses shared retrieval but keeps write rules in Core. Canonical state stays unobtrusive in normal pages; explain evidence paths on demand.

## Acceptance and validation

Run end-to-end scenarios for all consumers, including encounter participants/location/intentions, Ask across sources, a conflicting Lore input, Brainstorm pins and linked session notes. Workflow purpose may tune ranking but never authority or visibility.

## Migration and rollback

Roll out per consumer behind a flag with existing navigation fallback; no canonical migration. Lore UI delivery coordinates with the Promotion Pipeline surfaces (ADR-0018; TKT-0040 retired).
