---
id: TKT-0005
title: Scaffold Campaign Core service
status: done
priority: P1
milestone: trustworthy-librarian
depends_on: [TKT-0003]
created: 2026-07-31
updated: 2026-08-01
---

# TKT-0005: Scaffold Campaign Core Service

## Outcome

Create the Python/FastAPI service, typed configuration, migrations, database access boundaries, health endpoint, and initial domain test harness.

## Acceptance criteria

- [x] Service starts locally and in Compose.
- [x] Type checking, linting, and tests run from documented commands.
- [x] Canonical database writes are unavailable outside the Core credential.
- [x] Domain and adapter packages are separated.
- [x] One acceptance fixture runs through the domain layer.

## Implementation

- Added the pinned Python 3.12/3.13 development toolchain and Python 3.13 production image under `campaign-core/`.
- Added typed Pydantic settings, a FastAPI application factory and health contract, a pure domain package, and a narrow PostgreSQL adapter package.
- Added a transactional, advisory-locked, checksum-verifying migration runner and `0001_initial_schema.sql`, covering the TKT-0003 records, immutable evidence guards, and a database PC-agency trigger.
- Replaced the Compose health placeholder with the real non-root Campaign Core image while preserving internal-only networking and credential separation.
- Ran the sanitized `pc-directions-are-not-predicted-actions` fixture through the pure domain policy.

## Validation

- `python -m ruff check .` — passed.
- `python -m mypy` — passed in strict mode for 13 source files.
- `python -m pytest` — 6 tests passed, including API, architecture-boundary, migration-structure, and interaction-fixture coverage.
- Local bootstrap with migrations disabled served `GET /health` on `127.0.0.1:8011` and returned the versioned `ok` contract.
- Docker Engine 29.6.2 built `dm-assistant-campaign-core:0.1.0` from the pinned Python 3.13.14 Alpine base and pinned Python requirements.
- A fresh disposable Compose deployment reached healthy state against PostgreSQL `16.14-alpine3.23`; Campaign Core ran as non-root UID 100, applied one migration, and created 24 public tables including the migration ledger.
- Restarting Campaign Core retained exactly one applied migration. A live database probe confirmed the immutable-source trigger rejected an update and preserved the original path.
- `python tests/validate_compose_policy.py` and `python tests/validate_retrieval_cases.py` passed.
- Both named disposable validation stacks, their networks, and their database volumes were removed after validation. The built local application image remains available for development.
- `git diff --check` passed.

## Migration and rollback

Migrations are forward-only, transactional, advisory-locked, and checksum verified. Applied files cannot be edited. Expand-compatible application rollback and restore-to-a-new-database recovery are documented in `campaign-core/README.md`; destructive change-set behavior is not present in this scaffold.

## Follow-ups

- TKT-0010 provides the reusable acceptance-fixture harness.
- TKT-0013 builds sanitized importer fixtures on this service boundary.
- TKT-0015 implements the exact, version-bound, atomic canonical mutation and receipt path; Campaign Core exposes no mutation API until then.
