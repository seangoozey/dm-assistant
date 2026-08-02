---
id: TKT-0027
title: Re-extract nested planning sections on parser upgrades
status: done
priority: P1
milestone: trustworthy-librarian
depends_on: [TKT-0025]
created: 2026-08-01
updated: 2026-08-01
---

# TKT-0027: Re-extract Nested Planning Sections on Parser Upgrades

## Outcome

Represent substantive nested Markdown headings as independently reviewable evidence spans and safely re-extract unchanged source bytes when the parser version changes.

## Context

TKT-0025 found that the level-two-only parser collapsed three substantive nested planning sections in `gm/campaign-bible.md` into one 6,958-character candidate. The original candidate was independently deferred. Because source revision identity currently includes the source hash but not the parser version, the remediation must explicitly define safe re-extraction of unchanged bytes without duplicating immutable source truth or canonical records.

Read `docs/migration/markdown-importer.md`, `docs/product/invariants.md`, TKT-0016, TKT-0020, and TKT-0025.

## Scope

- Build a heading tree that preserves heading level, ancestry, and exact offsets.
- Emit independently reviewable candidates for substantive nested planning sections.
- Define parser-version-aware re-extraction for an unchanged source revision.
- Reconcile superseded extractor output without deleting provenance or reusing prior dispositions for changed fingerprints.
- Add sanitized nested-section fixtures modeled on the structural shape, not the prose, of the audited file.

## Out of scope

- Promoting any campaign-bible candidate.
- Inferring established or observed authority from a planning file.
- Copying live campaign prose into fixtures or repository documentation.

## Acceptance criteria

- [x] Nested substantive headings produce separate candidates with exact hierarchical section paths and offsets.
- [x] Parent headings with no direct substantive body do not absorb descendant prose into one candidate.
- [x] A parser-version change can re-extract unchanged source bytes idempotently without duplicating source truth.
- [x] Prior candidates and dispositions remain auditable; changed fingerprints require new independent review.
- [x] Planning candidates remain `possible`, `prepared`, or `intended` according to explicit section rules and never default to established support.
- [x] Sanitized tests cover nested headings, repeated headings, empty parents, ordinary retry, and parser-upgrade re-extraction.

## Implementation notes

- Parser 2.0 recognizes Markdown heading levels one through six, retains hierarchy and exact direct-body offsets, and separates repeated headings by span.
- The append-only `source_extractions` ledger records which parser version extracted each immutable source revision.
- `--reextract-path` explicitly scopes parser upgrades. A full-root scan remains mandatory for missing-source safety, but unchanged unselected files are not reparsed into the database.
- Reconciliation marks superseded candidate fingerprints `source_removed`; it retains prior review dispositions and creates new pending review state for new fingerprints.
- Import review creation now reuses identical open source reviews. Duplicate rows discovered during the live run were retained as `superseded` audit history and linked to their prior review; default queues omit them unless `status=superseded` is requested.

## Validation evidence

- Deterministic repository validation passed: Ruff; Campaign Core and Windmill mypy; 110 Python tests with 20 environment-dependent skips; 18 React tests; strict TypeScript; raw-app build; Compose, lifecycle, and Windmill source policies; and 38 retrieval cases.
- Disposable PostgreSQL validation passed all nine importer and review integration tests, including scoped two-file re-extraction, disposition preservation, exact retry, ordinary retry, review reuse, and superseded-review filtering. Each exact disposable container and its anonymous test-only volume was removed afterward.
- The pre-migration logical backup restored successfully with 143 source documents, 143 source revisions, 405 candidates, one entity, one claim, zero relationships, and one receipt. SHA-256: `A332DDBE4B9C3D3F577C14E88CF44C3BFF636E99A08BBB788F83E0BDE2A1493A`.
- A second validated post-import/pre-review-reconciliation backup was retained. SHA-256: `67D2F1D1BDDD825558F673F35F68E7784FD5DC5FE0E0516649557E24125B4D3C`.
- Live scoped import run `3a442f3a-5e2d-4ead-af40-896b62db3c73` produced 142 `unchanged` outcomes and one `reextracted` outcome. An exact retry returned the same run ID with `idempotent_replay=true`.
- Final live state: 143 source documents, 143 revisions, 144 extraction ledger rows with exactly one parser-2.0 extraction, and 408 candidates. The campaign-bible source has one deferred/source-removed parser-1.0 candidate plus three active pending parser-2.0 candidates: two `possible`/`brainstorm` and one `intended`/`npc_intention`.
- Default review total remains 125. The 125 accidentally reopened rows are preserved and explicitly queryable as `superseded`; no review row was deleted.
- Canonical state did not change: one entity, one claim, zero relationships, and one canonical receipt.

## Migration and rollback

- Migration `0005_source_extractions.sql` is additive, backfills the prior parser version, and makes extraction records immutable.
- Parser-upgrade effects are provenance-preserving: restoring the pre-migration backup is the full rollback path; ordinary operation can leave parser-2.0 candidates unapproved without altering canonical truth.
- Both logical backups were validated with `pg_restore --list`; the pre-migration backup was also restored into and queried from an isolated database before removal of that temporary database.

## Follow-up work

- TKT-0028 covers path-aware wiki-link target resolution. No parser-2.0 candidate in this ticket was promoted.
