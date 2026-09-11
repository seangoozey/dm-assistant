---
id: TKT-0098
title: Compact Brainstorm search categories and discovery cards
status: in-progress
priority: P1
depends_on: []
created: 2026-09-09
updated: 2026-09-09
---

# TKT-0098: Compact Brainstorm search categories and discovery cards

## Outcome

Search categories start collapsed. Search card controls remain at the upper right and all content stays inside the card.

## Acceptance criteria

- [x] Direct matches and Related discoveries expand independently and start closed.
- [ ] Pin and expand controls occupy the upper-right corner, including entity-free results.
- [ ] Long discovery context remains contained; full text can be expanded.
- [x] Existing search, highlighting, and pin tests pass.

## Scope

Possible conflicts also uses the shared collapsible category treatment, initially closed with its count visible. Conflict evidence is unchanged.

Search cards now include ellipsized source/section titles to the left of their controls. Match library names/aliases by normalized filename when possible; otherwise humanize the filename without inventing proper spelling. Remove presentation-only Canonical and trailing Layout labels; retain the original citation in the tooltip and evidence. Title formatter tests cover both requested examples and preservation of meaningful dash suffixes. Typecheck and 54 tests pass; deployed locally, visual confirmation pending.

Presentation only. Unmatched mentions must not silently create canonical records; discuss explicit creation/linking separately.

## Validation

Typecheck and all 52 App tests pass, including independent initially closed categories and per-card expand controls. Local test-stack deployment completed successfully. Upper-right positioning and overflow CSS implemented; live visual acceptance remains pending refresh. No canonical data changed.
