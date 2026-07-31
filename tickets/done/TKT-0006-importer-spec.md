---
id: TKT-0006
title: Specify incremental Markdown importer
status: done
priority: P1
milestone: trustworthy-librarian
depends_on: [TKT-0001]
created: 2026-07-31
updated: 2026-07-31
---

# TKT-0006: Specify Incremental Markdown Importer

## Outcome

Define deterministic discovery, classification, identity matching, parsing, source versioning, warning, and deletion-review behavior for repeated Starfall imports.

## Acceptance criteria

- [x] Re-importing unchanged input creates no duplicates.
- [x] Templates do not become campaign records.
- [x] Moves and renames preserve identity when evidence is sufficient.
- [x] Missing files create review items rather than deletions.
- [x] Mixed-status documents produce claim-level candidates.
- [x] Unclassified and unrelated material is quarantined.
- [x] Every run produces a detailed import receipt.

## Validation

Read-only review covered Starfall templates, a promoted brainstorm receipt, a mixed-status NPC record, session prep with recap and expected outcomes, wiki links, and the unrelated `memory/2026-06-08.md` note. `git diff --check` passed, and a structural check verified the specification covers unchanged re-imports, template exclusion, possible moves, missing sources, section-aware parsing, quarantine, and import-run receipts.
