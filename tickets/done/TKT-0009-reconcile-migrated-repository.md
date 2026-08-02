---
id: TKT-0009
title: Reconcile repository metadata after migration
status: done
priority: P1
milestone: specification-foundation
depends_on: []
created: 2026-08-01
updated: 2026-08-01
---

# TKT-0009: Reconcile Repository Metadata After Migration

## Outcome

Make repository documentation and ticket state accurately distinguish the current checkout, the historical audited snapshot, the old OpenClaw system, and the live read-only Starfall collection.

## Context

The repository moved from its originally documented location. The historical snapshot at `E:\studio\starfall` is no longer the live source. The current live campaign collection is `\\HOMESERVER\projects\projects\starfall`, while `\\HOMESERVER\openclaw\.openclaw\dnd-workspace` is historical system evidence that may contain older workflows, scripts, and a stale Starfall copy.

Read `README.md`, `AGENTS.md`, `docs/migration/current-system.md`, `tickets/done/TKT-0002-interaction-fixtures.md`, and `tickets/in-progress/TKT-0004-truenas-stack.md`.

## Scope

- Document `E:\dm-assistant` as the current checkout without embedding it in domain logic.
- Label `E:\studio\starfall` as the previously audited snapshot.
- Label `\\HOMESERVER\projects\projects\starfall` as the current live, strictly read-only legacy collection.
- Label `\\HOMESERVER\openclaw\.openclaw\dnd-workspace` as historical-system evidence rather than campaign truth.
- Reconcile TKT-0002's unchecked acceptance boxes with its recorded validation evidence.
- Determine whether TKT-0004 has recoverable uncommitted work elsewhere; either restore it for review, resume it, or move the ticket back to `ready`.
- Triage dependency-satisfied backlog tickets and update their state only when they are genuinely actionable.

## Out of scope

- Reading or copying private campaign content beyond the minimum metadata needed for path validation.
- Modifying either network share.
- Confirming the importer specification against live data; that remains TKT-0006A.
- Implementing the TrueNAS stack or Campaign Core.

## Acceptance criteria

- [x] Documentation unambiguously distinguishes checkout, audited snapshot, old system, and live campaign paths.
- [x] Source-safety language explicitly requires read-only access to both historical and live Starfall material.
- [x] No environment-specific path is introduced into domain logic.
- [x] TKT-0002 criteria are checked only where its existing evidence demonstrates completion; otherwise the ticket is reopened with the gap recorded.
- [x] TKT-0004's state matches the actual location and status of its implementation work.
- [x] Every ticket moved during reconciliation has matching frontmatter, directory placement, and `tickets/index.md` state.
- [x] No private source content is added to the repository.

## Validation

Partial validation on 2026-08-01:

- Confirmed both UNC locations are reachable without writing to them.
- Updated repository guidance to distinguish the current checkout, audited snapshot, live collection, and historical OpenClaw workspace.
- Rechecked all nine cases in `tests/fixtures/interaction_cases.yaml`: each contains the fields required by TKT-0002, uses enforcement ownership to distinguish Core from model/output validation, and retains only the fixture text needed to identify the tested behavior.
- Reconciled TKT-0002's acceptance checkboxes with its existing validation record.

- Confirmed the user intentionally returned TKT-0004 to `ready`; reconciled its directory, frontmatter, and index entry.
- Moved dependency-satisfied TKT-0005 and TKT-0006A to `ready` after confirming their scope and prerequisites are present.
- Validated ticket directory/frontmatter states and index links, and ran `git diff --check`.

## Implementation notes

Both UNC locations were reachable from the migrated checkout on 2026-08-01. Reachability does not authorize writes or establish that historical copies are current.

## Follow-ups

- TKT-0006A performs the read-only live Starfall confirmation.
