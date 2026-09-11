---
id: TKT-0078
title: Merge equivalent claims while retaining all provenance
status: done
priority: P1
milestone: trustworthy-migration
depends_on: [TKT-0072]
created: 2026-08-22
updated: 2026-08-22
---

# TKT-0078: Merge Equivalent Claims While Retaining All Provenance

## Outcome

Equivalent assertions can resolve to one current claim supported by every relevant source span.

## Acceptance criteria

- [x] Review shows both assertions, truth dimensions, and every source span.
- [x] An explicit duplicate decision selects one current claim and attaches all nonduplicate provenance.
- [x] Superseded claims remain queryable for audit.
- [x] Current projections and retrieval return one claim rather than duplicate assertions.
- [x] Conflicting truth dimensions are visibly flagged and require an explicit reviewed choice.
- [x] Tests cover exact duplicates, paraphrases, multiple source documents, and idempotent replay.

## Completion notes

- Duplicate reconciliation copies every distinct evidence span and role from the superseded claim to the surviving claim in the same transaction.
- Reconciliation review displays each evidence path, section, offset range, and role.
- Truth-dimension differences are called out before the reviewer records an explicit decision.
- Regression coverage includes exact matches, paraphrases, separate source documents, supersession audit history, and idempotent replay.
