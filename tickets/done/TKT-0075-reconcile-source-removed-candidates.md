---
id: TKT-0075
title: Reconcile source-removed candidates through audited dispositions
status: done
priority: P1
milestone: trustworthy-migration
depends_on: [TKT-0067]
created: 2026-08-22
updated: 2026-08-22
---

# TKT-0075: Reconcile Source-Removed Candidates Through Audited Dispositions

## Outcome

A DM can reject or defer an obsolete source-removed candidate without deleting its evidence or bypassing the candidate disposition audit trail.

## Acceptance criteria

- [x] The disposition API accepts `source_removed` candidates that have no proposal binding.
- [x] A required audit reason is stored in `candidate_dispositions`.
- [x] The candidate review status changes to `rejected` or `deferred` while source status remains `source_removed`.
- [x] Candidates bound to immutable proposals cannot be dispositioned through this path.
- [x] Repeated identical disposition requests are idempotent.
- [x] Tests cover source-removed disposition and idempotent replay; existing API tests cover authorization.

## Validation evidence

- Targeted Ruff and mypy checks passed.
- Seven non-database API/import tests passed; PostgreSQL tests were collected but skipped because the shell lacked a disposable test DSN.
- Rebuilt local stack accepted audited rejection of all 31 obsolete parser-v1 candidates; both active and source-removed pending counts are zero.

