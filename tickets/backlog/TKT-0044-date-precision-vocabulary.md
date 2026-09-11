---
id: TKT-0044
title: Date-precision vocabulary and approximate-date handling
status: backlog
priority: P2
milestone: trustworthy-librarian
depends_on: [TKT-0030]
created: 2026-08-04
updated: 2026-08-05
---

# TKT-0044: Date-Precision Vocabulary and Approximate-Date Handling

## Outcome

Approximate dates deferred from TKT-0030 (`~290CE`) gain a structured precision dimension (`exact`/`approximate`/`range`/`era`) rather than being stored as-given only.

## Context

TKT-0030 documented that approximate dates are preserved as-given at promotion time, with a structured precision vocabulary explicitly deferred. The live corpus uses `~290CE` and CE ranges. This ticket adds the precision dimension so approximate and era-level dates are first-class rather than flattened.

Read `docs/decisions/ADR-0007-campaign-chronology.md`, TKT-0030, and TKT-0041.

## Scope

- A controlled precision vocabulary on campaign dates: `exact`, `approximate`, `range`, `era`.
- The `CampaignDate` model carries an optional precision value.
- Retrieval and display preserve precision so an approximate date is not presented as exact.

## Out of scope

- A full fuzzy-date parser for free text.
- Cross-calendar precision conversion.

## Acceptance criteria

- [ ] A campaign date carries an optional precision value from the controlled vocabulary.
- [ ] Approximate and era-level dates are stored and displayed with their precision intact.
- [ ] Retrieval does not present an approximate date as exact.
- [ ] Sanitized tests and full repository validation pass.
