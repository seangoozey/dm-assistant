---
id: TKT-0026
title: Display complete proposal item state before approval
status: done
priority: P1
milestone: trustworthy-librarian
depends_on: [TKT-0023]
created: 2026-08-01
updated: 2026-08-01
---

# TKT-0026: Display Complete Proposal Item State Before Approval

## Outcome

Ensure the immutable proposal comparison displays every consequential structured field needed to review an entity or claim before exact approval.

## Context

TKT-0024's first live proposal retained `entity_type: location` in Campaign Core, but the React comparison displayed only the entity name and generic target kind. That omission makes the visible approval comparison incomplete even though the underlying proposal is correct.

Read `docs/product/invariants.md`, `docs/architecture/overview.md`, TKT-0023, and TKT-0024.

## Scope

- Show entity type for `create_entity` proposal items.
- Show claim predicate, state, authority, and visibility for `create_claim` proposal items.
- Preserve the immutable version and exact selected item scope across ordinary refreshes while the review session remains open.
- Add component coverage and repeat the deployed-browser comparison check.

## Out of scope

- Editing or replacing the pending proposal.
- Approving or applying TKT-0024's proposal.
- A generic arbitrary-JSON proposal renderer.

## Acceptance criteria

- [x] An entity item visibly names its canonical name, entity type, target ID, and mutation kind.
- [x] A claim item visibly names its assertion, predicate, state, authority, visibility, target ID, and mutation kind.
- [x] Existing exact-scope confirmation behavior is unchanged.
- [x] Component tests and the deployed source demonstrate the complete comparison.

## Validation evidence

- `ProposalReview` now renders entity type and the consequential claim fields, including predicate, state, authority, visibility, subject/object IDs, confidence, condition/action flags, and relevant timestamps.
- The React component suite verifies the visible entity type, predicate, authority, and visibility while preserving exact checked-item approval scope; all 18 React tests pass.
- Strict TypeScript validation and the Windmill raw-app build pass. Full repository validation passes with 107 Python tests passed, 17 environment-dependent tests skipped, 18 React tests passed, and 38 retrieval fixtures validated.
- The exact source was deployed to `dm-assistant-dev`, and a follow-up deployment preview reports zero differences.
- Closing and reopening the Codex browser cleared its stale blob-backed iframe and restored the deployed app. Because Windmill stores the active proposal view in tab session storage, closing the tab also discarded the historical view of the already-applied proposal. The closed proposal was not recreated: its immutable database record, exact receipt, deployed renderer source, and component comparison coverage provide the durable validation evidence.
- No migration or rollback action is required; the change only expands the read-only comparison rendered before future approvals.
