---
id: TKT-0014
title: Correct live Starfall import scope
status: done
priority: P1
milestone: trustworthy-librarian
depends_on: [TKT-0006A]
created: 2026-08-01
updated: 2026-08-01
---

# TKT-0014: Correct Live Starfall Import Scope

## Outcome

Replace inventory-inferred import classifications with the campaign owner's verified path scope for the live Starfall collection.

## Context

TKT-0006A classified every discovered path conservatively because owner-verified import boundaries were not yet available. The owner subsequently confirmed which top-level folders contain relevant live data and identified two derived paths inside `gm` that need no import consideration. `gm/campaign-bible.md` is part of v0.1 and may contain uningested data, so it remains explicitly in scope.

Read `docs/migration/markdown-importer.md`, `docs/migration/current-system.md`, TKT-0006, TKT-0006A, and TKT-0013.

## Scope

- Define the owner-verified top-level allowlist for live import discovery.
- Exclude irrelevant top-level folders and the two identified derived `gm` paths before content processing.
- Preserve the template invariant without treating templates as campaign records.
- Record corrected live inventory counts without copying campaign content.
- Align the importer-fixture ticket with the corrected policy.

## Out of scope

- Writing to or importing from the live Starfall collection.
- Deciding canonical claims contained in `gm/campaign-bible.md`.
- Implementing the production importer.

## Acceptance criteria

- [x] The importer specification names the verified included and excluded paths.
- [x] `gm/campaign-bible.md` remains an import candidate and is not treated as derived evidence.
- [x] Excluded paths are skipped before content hashing, parsing, quarantine, or candidate creation.
- [x] Templates never create live campaign records.
- [x] TKT-0006A clearly distinguishes its raw inventory from the corrected owner-verified import scope.
- [x] TKT-0013 requires fixtures for the corrected path-boundary behavior.

## Validation

Read-only path enumeration against `\\HOMESERVER\projects\projects\starfall` confirmed 221 total paths: 177 under the nine included top-level roots and 44 outside them. Within the 177, `gm/location-evidence/**` contained 33 files, `gm/location-migration-inventory.md` contributed 1 file, and `templates/**` contained 10 files. This leaves 133 paths admitted to ordinary classification; later rules may still exclude navigation indexes or quarantine ambiguity. No live source file or metadata was changed.

The exact live paths `gm/location-evidence`, `gm/location-migration-inventory.md`, and `gm/campaign-bible.md` were verified. The campaign-bible file's own framing is planning rather than official lore, supporting section-aware review without granting canonical authority from its path.

Validation commands passed:

- `python tests/validate_retrieval_cases.py` — 38 cases validated.
- `python tests/validate_compose_policy.py` — six-service policy passed.
- A structural scope check found every required include, exclude, and path-policy marker in `docs/migration/markdown-importer.md`.
- `git diff --check` — passed.

## Follow-ups

- TKT-0013 implements sanitized fixtures for early path exclusion, template handling, campaign-bible-style planning, and admitted-path quarantine.
