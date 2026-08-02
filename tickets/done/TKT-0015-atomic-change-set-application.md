---
id: TKT-0015
title: Implement atomic canonical change-set application
status: done
priority: P1
milestone: trustworthy-librarian
depends_on: [TKT-0005, TKT-0010]
created: 2026-08-01
updated: 2026-08-01
---

# TKT-0015: Implement Atomic Canonical Change-Set Application

## Outcome

Make Campaign Core's version-bound change-set operation the only application path for canonical mutations, with atomic receipts and idempotent retries.

## Context

TKT-0005 scaffolds the service, schema, migrations, and adapter boundary but intentionally exposes no mutation API. `docs/architecture/campaign-core-schema.md` requires exact proposal-version and approval-scope validation followed by all-or-nothing mutation and receipt creation.

Read `docs/product/truth-state-authority.md`, `docs/architecture/campaign-core-schema.md`, `docs/architecture/workflows.md`, TKT-0003, TKT-0005, and TKT-0010.

## Scope

- Implement exact proposal-version, content-hash, and approval-scope validation.
- Lock the change set, approval, proposal version, and mutation targets in one PostgreSQL transaction.
- Apply every authorized item or roll back every item and receipt.
- Return the existing receipt for an already-applied idempotency key.
- Expose one typed Campaign Core operation without granting workers direct table credentials.
- Run the relevant scoped-approval and promotion fixtures through database transaction tests.

## Out of scope

- Model-driven proposal synthesis.
- Importer candidate extraction.
- React approval UI.

## Acceptance criteria

- [x] Approval binds to one immutable proposal version and explicit item scope.
- [x] Inspecting or approving one item cannot mutate siblings.
- [x] A changed version invalidates approval of the prior version.
- [x] Canonical mutations and the receipt commit atomically or all roll back.
- [x] Retrying an applied idempotency key returns the original receipt without duplicates.
- [x] No alternative API or worker credential can bypass the change-set boundary.
- [x] Relevant acceptance fixtures pass through the domain, API, and PostgreSQL layers.

## Implementation

- Added one typed `POST /change-sets/{change_set_id}/apply` operation and an application-service port; stale or unauthorized coordinates fail with `409 Conflict`.
- Added forward-only migration `0002_atomic_change_set.sql`, including a unique approval binding and the transaction-bound `apply_change_set` function.
- The function locks the change set, proposal, immutable version and items, approval, and target identities; validates the latest version, content hash, and explicit item scope; applies its allowlisted mutations; writes change-set items and a receipt; and changes statuses atomically.
- Implemented `create_entity` and evidence-backed `create_claim`; unknown mutation kinds fail closed.
- Exact retries return the original receipt. New versions invalidate unapplied older approvals, while a later edit does not invalidate the historical receipt of an already-applied request.
- Replaced the direct-lore fixture dependency with an executable domain assertion and ran the approval-scope, edited-version, and nested direct-lore cases through real HTTP/database tests.

## Validation

- Repository validation passed: Ruff, strict mypy over 25 source files, 38 non-integration tests, Compose credential policy, and all 38 retrieval fixtures. PostgreSQL integration tests are intentionally skipped unless a disposable `_test` database URL is supplied.
- Six PostgreSQL 16.14 integration tests passed against a fresh disposable Docker container. They covered HTTP-to-database scope enforcement, stale version rejection, content-hash mismatch, evidence-backed nested lore, failure on the second item after the first insert, and two concurrent apply calls.
- Failure injection left zero canonical rows, change-set items, or receipts and preserved the pending change-set status.
- Concurrent calls returned one receipt ID with one initial result and one idempotent replay; database counts remained one entity, one change-set item, and one receipt.
- API tests passed for exact typed-command construction, `409` rejection, strict `422` request validation, and confirmation that the apply route is the only mutating HTTP operation.
- Credential checks passed: Compose supplies the campaign database URL only to Campaign Core, Windmill has no campaign credential, and a source scan found no canonical-table DML in Python outside the migration-backed adapter path.
- Migration `0002` applied cleanly and repeated migration runs were no-ops with checksum verification. It is expand-compatible with the prior health-only application because the new column is nullable; application rollback uses the prior image, while schema recovery uses logical restore into a new database.
- `git diff --check` passed. The disposable PostgreSQL container and its anonymous storage were removed after validation.

## Follow-ups

- TKT-0016 can now submit importer-generated, reviewed entity and claim proposals through this boundary. Additional mutation kinds must extend the database allowlist and receive equivalent transaction tests; they must not add table-specific mutation endpoints.
