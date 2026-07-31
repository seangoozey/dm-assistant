---
id: TKT-0003
title: Define Campaign Core schema
status: backlog
priority: P0
milestone: specification-foundation
depends_on: [TKT-0001, TKT-0002]
created: 2026-07-31
updated: 2026-07-31
---

# TKT-0003: Define Campaign Core Schema

## Outcome

Define the minimal PostgreSQL schema for sources, entities, aliases, claims, relationships, time, workflow sessions, proposals, approvals, change sets, receipts, and derived artifacts.

## Acceptance criteria

- [ ] Schema represents every accepted truth-state fixture.
- [ ] Original source provenance is immutable.
- [ ] Proposal versions and approval scope are enforceable.
- [ ] Canonical application can be one database transaction.
- [ ] Stable identity survives source moves and renames.
- [ ] Derived artifacts cannot masquerade as authoritative claims.
- [ ] Migration and rollback strategy is documented.
