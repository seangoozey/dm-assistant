---
id: TKT-0001
title: Specify truth states and authority
status: done
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

- [x] Every provisional state has entry, exit, and supersession rules.
- [x] Real play versus preparation resolves automatically.
- [x] Real play versus established history identifies a possible retcon.
- [x] NPC intention does not imply outcome.
- [x] PC campaign direction cannot become future PC action.
- [x] Expected dates remain provenance after observed dates replace them.
- [x] Decision-table examples can be translated directly into tests.

## Validation

Reviewed against the audited Starfall chat dump and the relevant read-only snapshot records, including the promoted Infinite Twilight receipt, Ladir's campaign-sculpting notes, and the 2026-07-18 real-play note. `tests/fixtures/interaction_cases.yaml` parses successfully with nine cases; every case has the required workflow, evidence, expected/forbidden behavior, mutation effect, and enforcement fields. `git diff --check` passes.

## Follow-ups

- TKT-0003 converts the approved specification into a schema.
