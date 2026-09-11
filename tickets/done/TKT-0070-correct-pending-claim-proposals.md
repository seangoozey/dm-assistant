---
id: TKT-0070
title: Correct pending claim proposals before approval
status: done
priority: P0
milestone: trustworthy-migration
depends_on: [TKT-0067]
created: 2026-08-12
updated: 2026-08-12
---

# TKT-0070: Correct Pending Claim Proposals Before Approval

## Outcome

A reviewer can correct an assertion and its truth dimensions while a proposal is pending. Saving a correction creates a new immutable proposal version and makes the prior version ineligible for approval.

## Acceptance criteria

- [x] Pending claim items expose an explicit correction action.
- [x] Assertion, state, authority, visibility, conditional, and subject-action prediction are editable.
- [x] Corrections create a new immutable proposal version; prior versions remain auditable.
- [x] Approval is locked while a correction is being edited and until the new version is displayed.
- [x] Human correction can downgrade incorrectly classified evidence without changing its provenance.
- [x] Invalid state/authority pairs, authority strengthening, and unsafe resolved-PC agency combinations are rejected.
- [x] The proposal review never edits or applies an already approved/applied version.
- [x] Backend, client, and React tests cover correction and stale-version protection.

## Validation evidence

- Repository validator: 286 backend/acceptance tests passed, 26 integration tests skipped.
- React: 32 tests passed; strict TypeScript and Windmill raw-app build passed.
- Ruff, mypy, compose/lifecycle/source policies, and 38 retrieval cases passed.
