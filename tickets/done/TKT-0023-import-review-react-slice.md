---
id: TKT-0023
title: Build the import review React vertical slice
status: done
priority: P1
milestone: trustworthy-librarian
depends_on: [TKT-0019, TKT-0021, TKT-0022]
created: 2026-08-01
updated: 2026-08-01
---

# TKT-0023: Build the Import Review React Vertical Slice

## Outcome

Give the DM a usable review workspace for import receipts, quarantined material, candidate evidence, exact proposal versions, and scoped approval/application.

## Context

The current librarian shell can Ask and run an operational health job. It cannot inspect imported evidence or drive the mandatory human review and promotion workflow.

Read `docs/product/invariants.md`, `docs/architecture/overview.md`, `docs/architecture/workflows.md`, TKT-0008, TKT-0019, TKT-0021, and TKT-0022.

## Scope

- Add an import-run summary and filterable review queue.
- Show one selected candidate with exact source excerpt, path, section, state, authority, visibility, warnings, and conflicts.
- Support reject, defer, explicit target resolution, and proposal creation.
- Present one immutable proposal version and its exact affected items before approval.
- Show pending, applied, rejected, stale-version, failure, and receipt states across refresh.

## Out of scope

- Broad batch approval.
- Autonomous rewriting, entity resolution, or canon decisions.
- The general Brainstorm/Lore Entry workspace.

## Acceptance criteria

- [x] Receipt totals and queue filters match Campaign Core responses.
- [x] One selected item displays exact evidence and provenance before any mutation action.
- [x] Only one visible, versioned pending confirmation can bind a short confirmation.
- [x] Proposal comparison makes every affected item and resulting truth state explicit.
- [x] Reject, defer, stale approval, apply failure, and successful receipt states are visible and refresh-safe.
- [x] All campaign operations use typed Campaign Core boundaries; asynchronous work remains behind `JobPlatform`.
- [x] Component and deployed-browser tests cover the complete narrow review path.

## Implementation notes

- Added a typed `CampaignClient` review boundary and an allowlisted Windmill backend runnable for import reads, candidate disposition, exact proposals, scoped approval, and atomic application.
- Added a single-candidate React review workspace with run totals, filterable candidates, complete paginated source reviews, quarantine visibility, exact provenance, source diagnostics, explicit target resolution, immutable proposal comparison, exact confirmation, and receipt/failure outcomes.
- Persisted the selected workflow state in versioned session storage. Restored proposal versions are re-read from Campaign Core before approval or application is enabled.
- Kept all asynchronous infrastructure work behind `JobPlatform`; the review flow does not receive database credentials or bypass Campaign Core.

## Validation evidence

- `tests/validate_react_shell.py`: passed with 18 React/adapter/backend tests, strict TypeScript, a successful raw-app bundle, and four validated backend runnables.
- `tests/validate_repository.py`: passed; Ruff, mypy, 107 Campaign Core/acceptance tests with 17 environment-dependent skips, Compose/lifecycle/source policies, the React gate, and 38 retrieval cases were green.
- Scoped Windmill deployment to `dm-assistant-dev`: successful; the authenticated raw-app route rendered successfully and a second deployment preview reported zero changes.
- Read-only Campaign Core inspection confirmed 405 pending candidates, zero applied candidates, and 125 open source-review items, including quarantined classifications. No review disposition, proposal, approval, or canonical mutation was issued against the preserved import during smoke testing.
- Deployed in-app-browser validation at `/apps_raw/get/f/dm_assistant/apps/library` confirmed totals of 143 imported files, 405 candidates, 125 reviews, and 405 pending queue items. The selected candidate displayed assertion, state, authority, visibility, exact source path and excerpt, section, classification, offsets, revision hash, and source diagnostics before mutation controls.
- Selecting `Explicit lore` through the deployed filter returned 253 candidates and all 50 displayed queue entries carried `explicit_lore`; restoring `Any authority` returned the queue to 405. No mutation control was used.

## Migration and rollback

No schema or data migration is required. Rollback is a scoped Windmill redeployment of the prior raw-app and backend source; campaign evidence and canonical data are unaffected by deployment itself.

## Follow-up

- Use a disposable campaign database for any future deployed-browser exercise of reject, defer, proposal, approval, or apply controls.
