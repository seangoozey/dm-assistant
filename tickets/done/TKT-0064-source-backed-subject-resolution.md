---
id: TKT-0064
title: Resolve source-backed principal subjects
status: completed
priority: P1
milestone: planning-workspace
depends_on: [TKT-0063]
created: 2026-08-11
updated: 2026-08-11
---

# TKT-0064: Resolve Source-Backed Principal Subjects

## Outcome

Extraction supplies a source-backed subject mention and Campaign Core resolves it to the focal entity, an existing named entity, a proposed named identity, or an explicit non-entity participant. Arbitrary noun phrases cannot silently become entities.

## Acceptance criteria

- [x] Subject mentions are grounded in cited source segments or explicit document context.
- [x] Principal subject identity is resolved by Campaign Core, not accepted as an arbitrary model string.
- [x] Focal-entity, existing-entity, new-identity, and non-entity outcomes are explicit.
- [x] Possessive phrases such as `Ruhrogue's village` do not silently create entities.
- [x] Unresolved identity decisions remain human-controlled.
- [x] Tests cover pronouns, independent named subjects, possessives, aliases, and ambiguity.
