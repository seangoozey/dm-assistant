---
id: TKT-0028
title: Normalize path-aware wiki-link target resolution
status: backlog
priority: P2
milestone: trustworthy-librarian
depends_on: [TKT-0025]
created: 2026-08-01
updated: 2026-08-01
---

# TKT-0028: Normalize Path-Aware Wiki-Link Target Resolution

## Outcome

Resolve ordinary path-qualified Starfall wiki links deterministically while preserving genuinely unresolved or ambiguous references as diagnostics.

## Context

TKT-0025 found seven wiki links in `gm/campaign-bible.md`; all seven are unresolved by the current matcher because it compares complete link targets only with bare admitted-file stems. This is a resolver coverage problem, not permission to invent identities.

Read `docs/migration/markdown-importer.md`, `docs/product/invariants.md`, TKT-0016, TKT-0020, and TKT-0025.

## Scope

- Normalize path separators, optional `.md` suffixes, relative forms, fragments, and display aliases before matching.
- Match exact admitted normalized paths first and unambiguous basename aliases second.
- Preserve ambiguous basename and missing-target diagnostics without guessing.
- Add sanitized resolved, missing, and ambiguous path-qualified fixtures.

## Out of scope

- Fuzzy entity matching.
- Rewriting live Markdown links.
- Treating link resolution as canonical identity approval.

## Acceptance criteria

- [ ] Exact path-qualified links resolve to the admitted source document.
- [ ] Optional suffix, fragment, display text, and separator variants normalize deterministically.
- [ ] Ambiguous basename aliases remain unresolved with an explicit diagnostic.
- [ ] Missing targets remain unresolved and do not create invented sources or entities.
- [ ] Repeated scans do not duplicate diagnostics.
- [ ] Sanitized fixtures cover every normalization and ambiguity rule.

