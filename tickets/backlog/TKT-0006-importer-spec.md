---
id: TKT-0006
title: Specify incremental Markdown importer
status: backlog
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

- [ ] Re-importing unchanged input creates no duplicates.
- [ ] Templates do not become campaign records.
- [ ] Moves and renames preserve identity when evidence is sufficient.
- [ ] Missing files create review items rather than deletions.
- [ ] Mixed-status documents produce claim-level candidates.
- [ ] Unclassified and unrelated material is quarantined.
- [ ] Every run produces a detailed import receipt.
