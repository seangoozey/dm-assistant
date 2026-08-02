---
id: TKT-0021
title: Expose import receipts and review queues
status: done
priority: P1
milestone: trustworthy-librarian
depends_on: [TKT-0020]
created: 2026-08-01
updated: 2026-08-01
---

# TKT-0021: Expose Import Receipts and Review Queues

## Outcome

Add typed, paginated Campaign Core read operations for import receipts, candidate evidence, quarantine items, identity reviews, possible moves, missing sources, and source-removal reviews.

## Context

Imported evidence is durable but currently inspectable only through persistence-layer tests or direct database queries. Human review needs a Campaign Core read boundary before any promotion workflow or UI can be trustworthy.

Read `docs/product/invariants.md`, `docs/architecture/overview.md`, `docs/architecture/domain-model.md`, `docs/migration/markdown-importer.md`, TKT-0016, and TKT-0020.

## Scope

- List and inspect import runs with aggregate outcomes and warnings.
- Filter candidates and reviews by status, classification, state, authority, visibility, source, and run.
- Return exact source span, section, path, revision hash, and provenance needed to review one item.
- Expose quarantine rationale and unresolved-link/move/missing-source diagnostics.
- Enforce deterministic pagination and DM visibility at the API boundary.

## Out of scope

- Candidate approval, rejection, proposal creation, or canonical mutation.
- Bulk raw-source export.
- Model-generated summaries or classifications.

## Acceptance criteria

- [x] Typed endpoints expose import-run summaries and individual immutable receipts.
- [x] Candidate and review queues are deterministically filterable and paginated.
- [x] Candidate detail includes its exact evidence span and immutable provenance without fabricating context.
- [x] Quarantine and missing/move review reasons remain visibly distinct.
- [x] Visibility rules prevent non-DM requesters from receiving DM-only candidate material.
- [x] Reads do not update review state or canonical tables.
- [x] Real imported-data shapes receive sanitized regression fixtures and integration coverage.

## Implementation

- Added typed `GET /imports/runs` and `GET /imports/runs/{run_id}` operations for deterministic summaries and the immutable stored receipt.
- Added typed `GET /imports/candidates` and `GET /imports/candidates/{candidate_id}` operations. Filters cover run, candidate status, classification, state, authority, visibility, and source path.
- Candidate detail decodes the immutable UTF-8 revision and returns only the exact recorded evidence span with path, section, offsets, classification, and SHA-256—not a bulk source export.
- Added typed `GET /imports/reviews` with kind, status, run, classification, candidate state/authority/visibility, and source filters. Review kinds remain unchanged, so quarantine, warning, import review, possible move, and missing source cannot collapse into one label.
- Receipt and review operations require a DM requester. Candidate reads apply requester visibility in SQL; party and character callers cannot request their way around that predicate.
- Added an application-service protocol and PostgreSQL read adapter. No migration, disposition command, or canonical mutation path was added.

## Validation evidence

- Three non-database API tests cover typed pagination/filter propagation, DM-only receipt/review enforcement, character identity validation, and fail-closed missing records.
- A PostgreSQL integration test imports the 17-file sanitized corpus, verifies stable pagination, run/source filters, party visibility, exact excerpt offsets/hashes, distinct quarantine reviews, and an identical database snapshot before and after all reads.
- The full repository gate against a disposable PostgreSQL 16.14 `_test` database passed with 116 Python tests and one environment-dependent skip. The disposable container and its anonymous data were removed afterward.
- The ordinary repository gate passes with 104 Python tests, 13 opt-in environment skips, 10 React tests, 38 retrieval cases, Ruff, strict mypy over 39 source files, strict TypeScript, infrastructure policy, and raw-app build checks.
- A live-shape smoke test against the TKT-0020 development import returned 1 run, 143 admitted files, 405 candidates, 125 reviews, and 8 quarantine reviews. A sample detail contained one bounded excerpt and a 64-character revision hash without printing private prose.
- The live-shape visibility check returned zero party-visible candidates from the currently DM-only corpus and `403 Forbidden` for a party review request. A combined possible/brainstorm/DM-only review filter returned nine source-level review items.

## Migration and rollback

No schema migration is required. The endpoints are read-only over the existing import tables. Application rollback deploys the previous Campaign Core image; imported evidence, candidates, reviews, and receipts remain unchanged and readable again when this version is restored.

## Follow-up

TKT-0022 can now create exact, versioned proposals and dispositions from selected candidate IDs. It must not add bulk approval or bypass the existing atomic change-set boundary.
