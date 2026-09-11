---
id: TKT-0072
title: Reconcile overlapping claims through reviewed supersession
status: done
priority: P0
milestone: trustworthy-migration
depends_on: [TKT-0067]
created: 2026-08-13
updated: 2026-08-13
---

# TKT-0072: Reconcile Overlapping Claims Through Reviewed Supersession

## Outcome

A reviewer can replace an older canonical claim with a corrected claim without deleting history or presenting both as simultaneously current.

## Scope

- Detect substantially overlapping claims linked to the same source evidence or subject.
- Show the reviewer both claims and their provenance, truth coordinates, and recorded times.
- Offer explicit decisions: retain both, mark duplicate, or supersede one with the other.
- Persist supersession using the existing append-only claim-supersession model.
- Require reviewed proposal, approval, atomic application, and receipt.
- Reconcile Ruhrogue claim `63ca2e5a-0dd6-4df1-8ce1-a8919b0fb01a` as the intended replacement for `9be65e44-aabf-4a06-91b4-e8ac3a08de5b` after human confirmation.

## Acceptance criteria

- [x] No canonical claim is deleted or overwritten.
- [x] Supersession identifies both the superseding and superseded claim IDs.
- [x] The reviewer sees exact assertion text, provenance, state, authority, visibility, dates, and condition details.
- [x] Approval cannot apply to a stale reconciliation version.
- [x] Retaining both claims remains an explicit valid decision.
- [x] Duplicate and superseded claims are excluded from current projections but remain queryable for audit.
- [x] Retrieval and conflict detection prefer the current non-superseded claim.
- [x] Tests cover exact duplicates, paraphrases, legitimate coexistence, stale versions, and idempotent replay.

## Out of scope

- Silent automatic merging or deletion.
- Bulk reconciliation without human review.

## Validation evidence

- Added migration `0022_claim_reconciliation_decisions.sql` and immutable reconciliation snapshots.
- Reconciliation supports `retain_both`, `duplicate`, and `supersede`; application creates proposal, approval, change set, change-set item, receipt, and decision records atomically.
- Current source-document and retrieval projections exclude claims reached by a `claim_supersessions` edge without deleting or rewriting the displaced claim.
- Full deterministic repository validation passed: 294 backend/acceptance tests passed (28 skipped), 35 React tests passed, strict typing/build checks passed, and 38 retrieval cases passed.
- Applied the confirmed Ruhrogue replacement with receipt `646b98f4-7fee-4b9c-9158-051757463ebd`; the current document projection now returns only claim `63ca2e5a-0dd6-4df1-8ce1-a8919b0fb01a`.
- Added the Tools > Claim Reconciliation workspace with automatic same-subject/source overlap discovery, side-by-side provenance review, all three decisions, and a required audit reason.
- Added exact-match, paraphrase, legitimate-coexistence, migration, UI, stale-snapshot, and idempotent-replay tests.
- Deployed contract validation rejected a stale snapshot with HTTP 409 and replayed the Ruhrogue decision with the original receipt and `idempotent_replay: true`.
