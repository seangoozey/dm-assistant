---
id: TKT-0077
title: Split and reclassify committed claims through reviewed replacement
status: done
priority: P1
milestone: trustworthy-migration
depends_on: [TKT-0074]
created: 2026-08-22
updated: 2026-08-22
---

# TKT-0077: Split and Reclassify Committed Claims Through Reviewed Replacement

## Outcome

A DM can replace a coarse committed claim with one or more claims whose truth dimensions are independently correct.

## Acceptance criteria

- [x] Review supports editing assertion, state, authority, visibility, dates, and explicit conditions.
- [x] One source claim may be split into multiple reviewed replacements.
- [x] Every replacement retains exact source provenance.
- [x] Applying the replacement supersedes the coarse claim without deleting history.
- [x] Possible, intended, prepared, observed, and established material can be split into independently reviewed replacements instead of remaining bundled under one state.
- [x] Tests include the mixed campaign-bible Romulus sections.

## Implementation sequence

1. Replace the assertion-only correction command with a reviewed replacement payload containing all editable truth dimensions and campaign-calendar date parts.
2. Add a forward-only PostgreSQL migration for atomic one-to-many replacement, provenance copying, supersession, approval, receipt, and replay.
3. Expand the Documents claim editor to edit dimensions and add or remove replacement rows before confirmation.
4. Render the immutable before/after replacement set and require one audit reason before applying it.
5. Cover single correction, split correction, stale snapshots, replay, observed-date validation, explicit conditions, and the Romulus mixed-state fixture.

## Constraint discovered

Migration 0023's `correct_canonical_claim` function copies all existing dimensions and only changes assertion text. It also requires the assertion itself to change. TKT-0077 therefore needs a new forward-only database operation; updating the replacement after calling the old function would make its immutable proposal and receipt inaccurate.

## Progress

- Campaign Core now applies one-to-many replacements atomically with one immutable proposal, approval, change set, and receipt.
- Each replacement independently controls assertion, truth dimensions, explicit prerequisite, and campaign-calendar date parts.
- The Documents editor supports adding and removing replacement rows before applying the reviewed split, and blocks observed replacements until an observed campaign date is supplied.
- `deploy/test-campaign-core-postgres.ps1` builds a reusable pytest image, creates only `campaign_core_integration_test`, runs inside the private database network, and removes the database in `finally`.
- PostgreSQL integration tests pass for stale snapshots, reconciliation replay, split dimensions, copied provenance, supersession history, and replacement replay.

