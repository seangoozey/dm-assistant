---
id: TKT-0006A
title: Confirm Markdown importer specification against live Starfall data
status: backlog
priority: P1
milestone: trustworthy-librarian
depends_on: [TKT-0006]
created: 2026-07-31
updated: 2026-07-31
---

# TKT-0006A: Confirm Markdown Importer Specification Against Live Starfall Data

## Outcome

Confirm that the incremental Markdown importer specification remains correct against the current live Starfall collection after this repository is moved to the environment where that collection is held.

## Context

TKT-0006 was specified and reviewed using the local `E:\studio\starfall` snapshot. That snapshot is not current campaign data. The live collection is authoritative for importer confirmation, but remains strictly read-only throughout this work.

## Scope

- Configure the live Starfall path outside domain logic.
- Perform read-only inventory and representative sampling of live files.
- Compare live folder/type/frontmatter patterns against `docs/migration/markdown-importer.md`.
- Confirm template exclusion, mixed-status parsing, PC-agency treatment, promoted brainstorm receipts, unclassified-content quarantine, stale-link warnings, and missing-source review behavior.
- Record any specification discrepancy as a targeted amendment or follow-up ticket.

## Out of scope

- Writing to, cleaning up, or reorganizing the live Starfall collection.
- Importing live data into a canonical campaign database.
- Changing importer implementation before the confirmation findings are reviewed.

## Acceptance criteria

- [ ] Live source path and access mode are documented; access is read-only.
- [ ] Live inventory is compared with the snapshot assumptions used by TKT-0006.
- [ ] Required representative categories are sampled from live records.
- [ ] Every difference affecting importer behavior has a documented resolution, specification amendment, or follow-up ticket.
- [ ] Validation evidence identifies the live snapshot/revision without copying private source content into this repository.

## Validation

Run only read-only inventory, hashing, classification, and parsing checks against the live source. Record commands, summary counts, and sanitized findings here.

## Follow-ups

- Reopen or supersede TKT-0006 only if live-data confirmation changes the importer specification.
