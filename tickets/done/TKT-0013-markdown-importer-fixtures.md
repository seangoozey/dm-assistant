---
id: TKT-0013
title: Build sanitized Markdown importer fixtures
status: done
priority: P1
milestone: trustworthy-librarian
depends_on: [TKT-0005, TKT-0014]
created: 2026-08-01
updated: 2026-08-01
---

# TKT-0013: Build Sanitized Markdown Importer Fixtures

## Outcome

Create executable, privacy-safe importer fixtures covering the live-confirmed Starfall structures and repeated-scan reconciliation behavior required by the importer specification.

## Context

TKT-0006 specified the importer, TKT-0006A inventoried the live read-only collection, and TKT-0014 replaced inventory-inferred classifications with the owner-verified path scope. The repository still lacks the importer fixtures required by `docs/migration/markdown-importer.md`, and no retained historical manifest is available to exercise real moved or missing paths safely.

Read `docs/migration/markdown-importer.md`, `docs/migration/current-system.md`, TKT-0006, TKT-0006A, and TKT-0014.

## Scope

- Add minimal sanitized fixtures for a mixed-status NPC, a PC with private campaign direction, a location, reviewed and unreviewed session notes, a promoted brainstorm receipt, campaign-bible-style planning, session preparation, encounter read-alouds, an unknown file inside an admitted path, and stale links.
- Include discovery-scope fixtures for excluded top-level roots, an unlisted root, `gm/location-evidence/**`, and `gm/location-migration-inventory.md`; assert they are skipped before content processing.
- Include hard-exclusion fixtures for templates and navigation indexes.
- Include the live-confirmed legacy `type: session` plus `status: note` form and an invalid-frontmatter warning case.
- Add a synthetic repeated/unchanged/changed/moved/missing scan sequence.
- Assert that missing input never deletes or downgrades canonical records.
- Keep all source text minimal and sanitized; synthetic move/missing cases must be labeled.

## Out of scope

- Reading from or writing to the live Starfall collection during automated tests.
- Implementing the production importer.
- Importing any fixture into a production campaign database.

## Acceptance criteria

- [x] Every required importer-fixture category in the specification has a sanitized fixture and expected classification.
- [x] Excluded top-level and derived-`gm` paths create no source revisions, quarantine entries, entity candidates, or claim candidates.
- [x] Templates and navigation indexes create no entity or claim candidates.
- [x] Campaign-bible-style planning cannot become established or observed based on its path, and promotion receipts cannot reapply canonical claims.
- [x] Mixed-status documents produce separate expected candidate states by source span.
- [x] Legacy session metadata resolves deterministically only under the session-notes path.
- [x] Invalid or missing frontmatter produces warnings without guessed authority.
- [x] Repeated unchanged scans create no duplicate revisions or candidates.
- [x] Moved and missing-source cases preserve stable identity and canonical truth.
- [x] Fixtures run through the repository's standard test command.

## Validation

`python tests/validate_repository.py` passed with Ruff, strict mypy over 20 source files, 31 Campaign Core tests, Compose policy validation, and structural validation of all 38 retrieval cases.

The importer corpus contains 26 deliberately synthetic files: 17 admitted inputs and 9 exclusion sentinels. Instrumented discovery produced exactly 17 content reads, 17 source-revision expectations, 15 claim candidates, 3 entity candidates, and 0 canonical mutations. Every excluded sentinel had zero reads and no discovered file outcome, revision, quarantine entry, entity candidate, or claim candidate.

The typed fixture manifest covers mixed NPC state, PC agency, locations and stale links, reviewed/unreviewed/applied/legacy sessions, promoted brainstorm receipts, campaign-bible planning, session prep, encounter read-alouds, unsupported formats, invalid and missing frontmatter, templates, navigation indexes, every excluded top-level category, an unlisted root, and both excluded derived `gm` paths.

The explicitly synthetic five-scan reconciliation sequence validated `new`, `unchanged`, `changed`, `moved`, and `missing_source`. It retained one source identity, two content revisions, two candidate fingerprints, two canonical facts, and both historical paths after the final missing scan. Unchanged and moved scans created no duplicate revision or candidate.

A focused name/path scan found none of the representative private campaign names, live UNC path, or historical snapshot path in this fixture corpus. No live or historical Starfall collection was accessed. `git diff --check` passed.

## Implementation

- Added typed importer manifest and reconciliation contracts under `dm_assistant_core.acceptance`.
- Added a test-only reference scanner that prunes scope before reads, hashes admitted bytes once, parses fixture frontmatter/sections/links, and makes expected classification behavior executable.
- Added focused assertions for PC agency, mixed states, session authority, applied-delta and promotion-receipt non-reapplication, templates/indexes, warnings, and source reconciliation.
- Added `moved` and `navigation_excluded` to the specified import-receipt outcomes exposed by the fixtures.
- Documented fixture safety and extension in `docs/testing/importer-fixtures.md`.

## Implementation notes

Use aggregate structural findings from TKT-0006A rather than copying private live documents. The moved/missing sequence is synthetic because no retained audited manifest is available in this environment.

## Follow-ups

- TKT-0016 implements the production importer after TKT-0015 supplies the atomic Campaign Core mutation boundary.
