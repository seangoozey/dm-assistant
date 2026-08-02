---
id: TKT-0016
title: Implement incremental Markdown importer
status: done
priority: P1
milestone: trustworthy-librarian
depends_on: [TKT-0005, TKT-0013, TKT-0015]
created: 2026-08-01
updated: 2026-08-01
---

# TKT-0016: Implement Incremental Markdown Importer

## Outcome

Implement the read-only, repeatable Starfall Markdown connector against the sanitized TKT-0013 fixtures and Campaign Core's atomic mutation boundary.

## Context

TKT-0006 defines importer behavior, TKT-0014 establishes the owner-verified source scope, and TKT-0013 makes the required structures and reconciliation behavior executable. TKT-0015 owns the only canonical mutation path that an importer may call.

Read `docs/migration/markdown-importer.md`, `docs/migration/current-system.md`, `docs/testing/importer-fixtures.md`, TKT-0006, TKT-0013, and TKT-0015.

## Scope

- Discover from an explicitly configured read-only root and reject escapes.
- Apply the versioned path allowlist and exclusions before content reads.
- Hash admitted files once and submit immutable source revisions through Campaign Core.
- Parse frontmatter, sections, links, classification, visibility, time, and candidate provenance.
- Reconcile unchanged, changed, moved, possible-move, and missing paths idempotently.
- Produce complete import receipts and review/quarantine outcomes.
- Pass every TKT-0013 fixture without fixture-specific production logic.

## Out of scope

- Rewriting or cleaning the live Starfall collection.
- Granting Windmill workers direct canonical-table credentials.
- Automatically deleting or downgrading truth after source removal.

## Acceptance criteria

- [x] Excluded paths are never read, hashed, parsed, quarantined, or stored as source revisions.
- [x] Every admitted byte is preserved with path, hash, time, importer version, and path-policy version.
- [x] Classification and section-aware candidate output match the sanitized fixture manifest.
- [x] Repeated scans are idempotent and exact-hash moves preserve source identity.
- [x] Ambiguous moves and missing sources create review items without canonical deletion.
- [x] Templates, indexes, receipts, applied deltas, and planning material obey their authority boundaries.
- [x] Import runs produce durable receipts through Campaign Core and no direct canonical database access exists outside Core.
- [x] Live-source verification remains read-only and requires an explicitly reviewed runtime configuration.

## Implementation

- Added a production read-once Markdown scanner with a versioned allowlist, derived-path exclusions, symlink/path escape rejection, strict UTF-8/frontmatter handling, section spans, wiki-link diagnostics, and an explicit `read_only=True` runtime acknowledgement.
- Added a no-database CLI with aggregate-only dry-run output and typed submission to `POST /imports/markdown/scan`.
- Added typed source, candidate, batch, outcome, and receipt contracts. Exact bytes use transport-safe base64 serialization and Campaign Core re-verifies every SHA-256 before persistence.
- Added migration `0003_markdown_import.sql` for source path history, revision path/time/parser/policy metadata, non-canonical candidates and evidence, import-opened reviews, and immutable import runs/observations.
- Added transactional PostgreSQL reconciliation for stable external IDs, prior paths, exact-hash moves, changed content, ambiguous high-overlap possible moves, missing-source confirmation, candidate fingerprint retention, and source-removed candidate provenance.
- Templates, navigation indexes, applied deltas, promotion receipts, read-alouds, campaign planning, PC private notes, and classification conflicts have explicit fail-safe behavior. The import operation has no code or schema path to create canonical entities, claims, or relationships.
- Added support for the live collection's `canon_status`, `review_status`, `delta_status`, and `promotion_status` metadata without treating operational NPC/location status as truth authority.

## Validation

- Repository validation passed with Ruff, strict mypy over 31 source files, 52 standard tests, Compose credential policy validation, and all 38 retrieval-corpus structure checks. Twelve PostgreSQL/symlink-environment tests skip intentionally when their external prerequisites are absent.
- The production scanner matched every one of the 17 admitted sanitized fixture records: 17 reads, one read per path, 17 exact hashes, 15 claim candidates, 3 entity candidates, and zero reads for all nine excluded sentinels. The independent test-only reference scanner remains separate.
- Eleven PostgreSQL 16.14 integration tests passed against a fresh disposable Docker database, including the six atomic change-set tests and five importer tests. Import tests covered HTTP-to-database persistence, exact and concurrent retries, unchanged/changed/moved/missing reconciliation, ambiguous possible moves, and tampered-hash rollback.
- The fixture import created 17 source documents, 17 immutable revisions, 15 non-canonical candidates, one immutable import run, and 17 observations, while creating zero canonical entities or claims. An exact retry returned the same run ID; two concurrent calls produced one run and one replay.
- Tampered input created zero source documents, revisions, or receipts. Exact-hash moves retained one source identity and two historical paths; ambiguous different-hash moves retained two identities and opened review rather than merging. Missing input opened review without deleting evidence or canonical truth.
- A live dry run against the explicitly configured `\\HOMESERVER\projects\projects\starfall` root was read-only and was not submitted to Campaign Core. It admitted 143 files with exactly 143 reads and a maximum of one read per path, pruned nine excluded entries before reads, classified 57 durable-evidence, 44 real-play, 9 preparation, 5 brainstorm, 4 handout, 3 session-prep, 1 campaign-planning, 10 template, 2 navigation, and 8 quarantine records, and produced 405 non-canonical candidates in memory only.
- Static safety checks confirmed the scanner contains no filesystem mutation calls or PostgreSQL imports. Compose still gives the campaign credential only to Campaign Core and declares the source-check mount read-only.
- The pinned Python 3.13.14 Alpine production image rebuilt successfully with PyYAML 6.0.3. Migration `0003` applied transactionally and repeated migration runs were checksum-verified no-ops.
- Migration `0003` is additive and the previous application can run against it. Application rollback uses the prior image; persisted immutable source/import evidence is recovered by logical restore into a new database rather than destructive reversal.
- `git diff --check` passed. The disposable PostgreSQL container and its anonymous storage were removed after validation.

## Follow-ups

- TKT-0012 should execute the grounded retrieval corpus against the now-durable evidence and candidate boundary.
- TKT-0007 can later schedule the no-database connector CLI through Windmill with a read-only source mount and Campaign Core URL.
