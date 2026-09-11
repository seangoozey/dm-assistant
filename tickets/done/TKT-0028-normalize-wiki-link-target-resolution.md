---
id: TKT-0028
title: Normalize path-aware wiki-link target resolution
status: done
priority: P2
milestone: trustworthy-librarian
depends_on: [TKT-0025]
created: 2026-08-01
updated: 2026-08-03
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

- [x] Exact path-qualified links resolve to the admitted source document.
- [x] Optional suffix, fragment, display text, and separator variants normalize deterministically.
- [x] Ambiguous basename aliases remain unresolved with an explicit diagnostic.
- [x] Missing targets remain unresolved and do not create invented sources or entities.
- [x] Repeated scans do not duplicate diagnostics.
- [x] Sanitized fixtures cover every normalization and ambiguity rule.

## Implementation

- Added a shared, pure-function resolver at `dm_assistant_core.importer.links` (`LinkIndex`, `LinkTarget`, `LinkTargetStatus`, `build`, `normalize_target`, `classify_target`) used by both the production scanner and the independent test harness so normalization cannot diverge. The resolver models wiki links as Obsidian file references: the bracket path is authoritative.
- Path-qualified links (`[[lore/medallions]]`) resolve to the exact admitted file (`lore/medallions.md`) only; the `.md` extension Obsidian drops is restored, an explicit `.md` suffix is accepted, backslashes normalize to POSIX separators, and a display alias (`[[target|Label]]`) and fragment (`[[target#Section]]`) bind to the same target. A path-qualified link is never rescued onto a same-named file in a different directory; a wrong-directory or absent target stays `unresolved_link`.
- Bare links (no directory) resolve to a basename when exactly one admitted record shares that stem. Two or more admitted records sharing a basename report `ambiguous_link`; none report `unresolved_link`. Relative targets (`./`, `../`) resolve against the linking document's directory.
- Templates and navigation indexes are scaffolds and index pages, not records, so they are excluded as link targets. Links originating from them remain source diagnostics (`unresolved_link_diagnostic_only` / `ambiguous_link_diagnostic_only`).
- Added `AMBIGUOUS_LINK` and `AMBIGUOUS_LINK_DIAGNOSTIC_ONLY` to `ImportWarning`. Added `AMBIGUOUS_LINK` to `REVIEW_WARNINGS` in the Postgres import adapter so an ambiguous link opens a review item deduplicated by the existing `_open_review_exists` check, satisfying repeated-scan idempotency.
- Restructured the production scanner and the test harness into two phases: read and classify each file (without link warnings), build the `LinkIndex` from the classified records excluding templates and navigation indexes, then apply link warnings as a deterministic post-pass. A file emits at most one of each link-warning kind regardless of link count.
- Added sanitized fixtures: an ambiguous shared basename across `npcs/shared-vault.md` and `locations/shared-vault.md` (two real durable-evidence records), a `gm/brainstorming/cross-references.md` exercising both ambiguity and a missing target, and path-qualified resolving variants (`[[npcs/mixed-npc]]`, `[[npcs/mixed-npc.md]]`, `[[mixed-npc|The Archivist]]`, `[[../npcs/mixed-npc]]`) alongside the existing missing target in `locations/example-location.md`.
- Updated the importer specification and fixture-coverage documentation to state the Obsidian file-reference model, normalization rules, template-as-target exclusion, and the ambiguity diagnostic.

## Validation

- Resolver unit tests (`tests/test_link_resolver.py`, 21 cases) cover exact path resolution, explicit `.md` suffix, nested subdirectories, wrong-directory rejection, case-insensitivity, backslash separators, unique and ambiguous bare basenames, three-way ambiguity, relative `./` and `../` resolution with source-directory anchoring, empty targets, non-Markdown exclusion, and empty-index behavior.
- Production scanner tests (`tests/test_markdown_scanner.py`) add end-to-end cases proving path-qualified links resolve to their exact file, a path-qualified link to a wrong directory stays unresolved, an ambiguous bare basename reports `ambiguous_link`, and a link to a template stays unresolved because templates are not resolvable targets.
- The manifest-driven production and harness parity tests pass for 20 admitted fixture files, including the new ambiguous and resolving-link fixtures. Existing fixture warnings are unchanged because the new stems do not collide with any prior link target.
- Full repository validation passed: Ruff, strict mypy over 50 source files, 141 Python tests with 25 environment-dependent skips, 20 React tests, strict TypeScript, the Windmill raw-app build, infrastructure policy checks, and all 38 retrieval fixtures.
- No schema migration is required. The change is additive: new warning enum values, a new pure resolver module, and sanitized fixtures. No canonical entity, claim, or relationship is created by link resolution.

### Live validation

The live `gm/campaign-bible.md` at `\\HOMESERVER\projects\projects\starfall` was read once against the new resolver and the live 143-file admitted Markdown set, without submission to Campaign Core. All seven wiki links that TKT-0025 found unresolved now resolve to their exact admitted files:

- `[[lore/medallions-of-the-golden-dawn]]`, `[[lore/hidden-truths]]`, `[[lore/timeline]]`, `[[lore/the-raven-king]]`, `[[gm/plot-threads]]`, `[[encounters/Ishirala/ishirala-perch]]`, `[[npcs/ishigo-dan]]`.

The nested subdirectory path `[[encounters/Ishirala/ishirala-perch]]` — the exact shape the prior bare-stem matcher could not resolve — now matches `encounters/Ishirala/ishirala-perch.md`. The live collection was read-only for this check; no live bytes, paths, or metadata were changed.

## Follow-up work

None.


