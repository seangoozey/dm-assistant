---
id: TKT-0095
title: Connect every campaign workflow to shared knowledge
status: backlog
priority: P0
milestone: shared-campaign-knowledge
depends_on: [TKT-0094]
created: 2026-09-06
---

# Outcome

Use the common knowledge service in Ask, encounter runner, Lore preparation, Brainstorm, library and session-note related navigation.

## Required reading

- [Shared Campaign Knowledge](../../docs/architecture/shared-campaign-knowledge.md)
- [ADR-0014](../../docs/decisions/ADR-0014-shared-campaign-knowledge.md)
- [ADR-0012](../../docs/decisions/ADR-0012-provenance-first-claims.md)

## Scope

Remove page-specific ranking/path logic. Preserve excerpt highlighting and exact evidence pins. Encounter context preserves reading and note state. Lore comparison uses shared retrieval but keeps write rules in Core. Canonical state stays unobtrusive in normal pages; explain evidence paths on demand.

## Acceptance and validation

Run end-to-end scenarios for all consumers, including encounter participants/location/intentions, Ask across sources, a conflicting Lore input, Brainstorm pins and linked session notes. Workflow purpose may tune ranking but never authority or visibility.

## Migration and rollback

Roll out per consumer behind a flag with existing navigation fallback; no canonical migration. Coordinate Lore UI delivery with TKT-0040.
