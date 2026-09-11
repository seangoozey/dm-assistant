---
id: TKT-0089
title: Design the shared campaign relationship and retrieval layer
status: done
priority: P0
milestone: shared-campaign-knowledge
depends_on: [TKT-0088]
---

# Outcome

Define one Campaign Core knowledge contract for Ask, encounters, Lore, Brainstorm, and library browsing. Inspect existing relationships, mentions, provenance, and retrieval; establish an ordered implementation tranche without requiring SPO for claims.

## Acceptance

- Concrete architecture specification and proposed ADR document authority, time, visibility, identity, traversal, lifecycle, and backend boundaries.
- Tickets cover benchmark, policy correction, graph projection, evidence links, retrieval, all consumers, and optional backend evaluation.
- Each implementation ticket identifies dependencies, validation, and rollback.
- Existing Lore Entry work references the shared service instead of duplicating retrieval.

## Validation

Documentation and dependency review; no runtime changes or deployment in this design ticket.

Completed 2026-09-06: audited existing retrieval policy/adapter, relationship schema, mention links and prior assertion/plan ADRs. Added the shared specification, proposed ADR-0014 and ordered tickets TKT-0090 through TKT-0096. Lore Entry now depends on shared comparison and retrieval. No runtime changes were made; implementation validation belongs to the subsequent tickets.
