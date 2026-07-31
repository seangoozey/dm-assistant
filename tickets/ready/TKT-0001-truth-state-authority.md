---
id: TKT-0001
title: Specify truth states and authority
status: ready
priority: P0
milestone: specification-foundation
depends_on: []
created: 2026-07-31
updated: 2026-07-31
---

# TKT-0001: Specify Truth States and Authority

## Outcome

Produce an implementable decision table for claim states, source authority, conflicts, temporal changes, PC agency, and automatic versus reviewed behavior.

## Context

The current Markdown corpus assigns authority too broadly at the document level. Campaign Core cannot be designed safely until individual assertions have deterministic treatment.

Read `docs/product/invariants.md` and `docs/architecture/domain-model.md`.

## Scope

- Define each claim state and transition.
- Separate truth state, authority, confidence, visibility, and time.
- Define conflict outcomes for every source category.
- Define suspected-retcon handling.
- Define NPC intention and failed-plan behavior.
- Define PC-agency constraints.
- Define expected versus observed dates.

## Out of scope

- Physical database schema.
- Prompt design.
- UI implementation.

## Acceptance criteria

- [ ] Every provisional state has entry, exit, and supersession rules.
- [ ] Real play versus preparation resolves automatically.
- [ ] Real play versus established history identifies a possible retcon.
- [ ] NPC intention does not imply outcome.
- [ ] PC campaign direction cannot become future PC action.
- [ ] Expected dates remain provenance after observed dates replace them.
- [ ] Decision-table examples can be translated directly into tests.

## Validation

Review against the audited Starfall examples and every fixture in TKT-0002.

## Follow-ups

- TKT-0003 converts the approved specification into a schema.
