---
id: TKT-0076
title: Supersede stale import reviews after complete scans
status: done
priority: P1
milestone: trustworthy-migration
depends_on: [TKT-0016]
created: 2026-08-22
updated: 2026-08-22
---

# TKT-0076: Supersede Stale Import Reviews After Complete Scans

## Outcome

A complete scan automatically closes review items contradicted by the newest observation without hiding current warnings.

## Acceptance criteria

- [x] A present source supersedes its earlier open `missing_source` review.
- [x] Reclassification supersedes obsolete quarantine and review-required items.
- [x] A warning removed from the latest observation supersedes its prior open warning item.
- [x] Warnings still emitted by the latest observation remain open.
- [x] Reconciliation runs only for files present in a validated complete scan.
- [x] Reconciliation is transactional and idempotent, with PostgreSQL coverage added.

## Validation evidence

- Targeted Ruff and mypy checks passed.
- PostgreSQL tests cover restored missing sources and warnings that remain or disappear; they were collected but skipped locally because the shell lacked a disposable test DSN.
- Existing data reconciliation superseded 339 obsolete review records while retaining 65 current warnings and two intentional archive quarantines.

