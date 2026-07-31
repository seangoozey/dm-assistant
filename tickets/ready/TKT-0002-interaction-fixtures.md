---
id: TKT-0002
title: Build interaction acceptance fixtures
status: ready
priority: P0
milestone: specification-foundation
depends_on: []
created: 2026-07-31
updated: 2026-07-31
---

# TKT-0002: Build Interaction Acceptance Fixtures

## Outcome

Convert representative interactions from the partial legacy chat dump into structured acceptance cases with expected and forbidden behavior.

## Scope

- Unauthorized whole-promotion after selecting Jace.
- Invented Sorin and Roccid lore.
- Explicit read-aloud permission.
- Direct lore update inside an active brainstorm.
- Claim edit followed by exact promotion.
- PC campaign-shaping correction.
- Unknown noble names.
- Real-play ingestion and durable consequences.
- At least one synthetic audio claim-revision case until a real recording is available.

## Out of scope

- Committing the complete private chat dump.
- Model benchmarking.

## Acceptance criteria

- [ ] Every case states active workflow, input, prior evidence, expected output, forbidden output, and mutation effect.
- [ ] Fixtures contain only the minimum private campaign text needed for the behavior.
- [ ] Cases distinguish model quality failures from violations Core can enforce.
- [ ] Fixtures are usable by TKT-0001 and future automated tests.

## Validation

Manually compare each fixture with `E:\studio\starfall\DND Chat Dump.txt` without modifying that source.

## Follow-ups

- Add a real long-form audio fixture when one becomes available.
