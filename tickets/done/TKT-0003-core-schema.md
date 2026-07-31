---
id: TKT-0003
title: Define Campaign Core schema
status: done
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

- [x] Schema represents every accepted truth-state fixture.
- [x] Original source provenance is immutable.
- [x] Proposal versions and approval scope are enforceable.
- [x] Canonical application can be one database transaction.
- [x] Stable identity survives source moves and renames.
- [x] Derived artifacts cannot masquerade as authoritative claims.
- [x] Migration and rollback strategy is documented.

## Validation

`git diff --check` passed. A Python structural check parsed the nine accepted interaction fixtures and verified that each fixture ID appears in the schema coverage matrix; it also verified all 12 required core record types are specified.
