---
id: TKT-0074
title: Correct committed claims through reviewed replacement
status: done
priority: P0
milestone: trustworthy-migration
depends_on: [TKT-0072]
created: 2026-08-13
updated: 2026-08-13
---

# TKT-0074: Correct Committed Claims Through Reviewed Replacement

## Outcome

A DM can correct the assertion text of a committed claim from Documents without rewriting or deleting canonical history.

## Acceptance criteria

- [x] Documents presents each projected DM-plan claim separately with an edit action.
- [x] Correction requires changed assertion text and an audit reason.
- [x] Saving creates a new claim, copies truth coordinates and exact evidence, and supersedes the original.
- [x] The original claim remains queryable for audit but leaves current projections.
- [x] Stale and already-superseded claims cannot be corrected.
- [x] Application is idempotent and issues a receipt.
- [x] Automated tests cover the correction transaction and Documents workflow.

## Validation evidence

- Canonical writes are confined to migration function `0023_correct_canonical_claim.sql`.
- Documents renders canonical DM plans as separate cards with `Edit claim` actions.
- Full validation passed: 293 backend/acceptance tests, 35 React tests, strict type checks, Windmill build, and 38 retrieval cases.
- The local stack was rebuilt and the deployed database reports `correct_canonical_claim(uuid,text,text,text)` installed.
