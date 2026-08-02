---
id: TKT-0025
title: Audit campaign-bible planning coverage
status: done
priority: P1
milestone: trustworthy-librarian
depends_on: [TKT-0020, TKT-0023]
created: 2026-08-01
updated: 2026-08-01
---

# TKT-0025: Audit Campaign-Bible Planning Coverage

## Outcome

Review `gm/campaign-bible.md` section by section to identify previously uningested planning material, verify parser coverage, and record an explicit disposition for every candidate without granting authority from the file path.

## Context

The campaign owner identified this file as part of v0.1 and potentially containing uningested material. It is planning evidence, not a canonical shortcut, and must not ride along with unrelated live promotions.

Read `docs/product/invariants.md`, `docs/product/truth-state-authority.md`, `docs/migration/markdown-importer.md`, TKT-0014, TKT-0020, and TKT-0023.

## Scope

- Compare imported section spans and candidates with the admitted source revision.
- Identify parser omissions, duplicate promotion receipts, unresolved references, and classification ambiguity.
- Record each candidate as possible, prepared, intended, rejected, deferred, quarantined, or explicitly proposed.
- Create focused parser follow-up tickets for genuine coverage gaps.

## Out of scope

- Treating the file or any whole section as established by default.
- Bulk promotion or approval through a single confirmation.
- Predicting PC decisions or inventing reactions to failed plans.

## Acceptance criteria

- [x] Every substantive admitted section has a candidate, diagnostic, or explicit no-candidate rationale.
- [x] Planning states remain labeled and excluded from established retrieval support.
- [x] Prior promotion receipts do not create duplicate claims.
- [x] Each reviewed item receives an independent, auditable disposition.
- [x] Exact proposals, if any, are versioned and approved separately from the audit itself.
- [x] Parser gaps and unresolved identity/retcon questions become scoped follow-up tickets.
- [x] No private campaign prose is copied into repository documentation or tickets.

## Audit record

### Source and section coverage

- The read-only live file and its one stored source revision both contain 7,651 bytes. The source remains classified `planning_evidence`; no second revision or source document exists.
- The Markdown contains seven headings: one document heading, three level-two headings, and three substantive nested level-three headings. Structural metrics found 80 nonblank body lines without recording their prose.
- The document-level framing is not an independent campaign assertion and has an explicit no-candidate rationale.
- The short overview is intentionally excluded by the planning parser's overview rule and has an explicit no-candidate rationale as orientation rather than an independently reviewable plan.
- The planning container has no direct body, but the level-two-only parser absorbed all three substantive descendants into one 6,958-character `possible` / `brainstorm` / `dm_only` candidate. That over-broad candidate was independently deferred through Campaign Core because it cannot be reviewed item by item.
- Each of the three substantive nested sections is recorded as a parser coverage gap under TKT-0027. The reference section is evidence-only rather than a planning assertion and is covered by the existing unresolved-link diagnostic.

### Diagnostics, receipts, and dispositions

- The source has one open import-review item plus `missing_frontmatter` and `unresolved_link` warnings. Missing frontmatter does not authorize a classification guess; the explicit path rule supplies only `planning_evidence`.
- The file contains seven wiki links, all unresolved by the current bare-stem matcher. TKT-0028 scopes path-aware normalization while preserving missing and ambiguous targets.
- No promotion-receipt or promoted marker occurs in the source. The database contains no applied campaign-bible candidate and no canonical claim evidenced by this source, so there is no duplicate promotion to suppress in the audited revision.
- Exactly one imported candidate existed. Its state/authority/visibility remained `possible` / `brainstorm` / `dm_only`, and it received one auditable `deferred` disposition with a structural audit reason. No sibling disposition, proposal, approval, or canonical mutation was inferred.
- No exact proposal was created during this audit. Any future candidates produced by TKT-0027 require their own visible version, disposition, and—only if explicitly requested—separate exact approval.

### Safety

- The live collection was read only for file metadata, heading structure, section-size metrics, link-resolution counts, and marker counts. No live bytes, timestamps, paths, or metadata were changed.
- No source excerpt, heading title, link target, hash, candidate UUID, disposition UUID, or receipt identifier is committed in this record.

## Validation evidence

- Final database checks found one campaign-bible candidate, zero pending, one deferred, zero applied, one disposition, zero proposal bindings, and zero canonical claims evidenced by this source.
- Overall canonical totals remained one entity, one claim, and zero relationships; the audit performed no canonical mutation.
- Full repository validation passed: Ruff, mypy, 107 Python tests with 17 environment-dependent skips, 18 React tests, strict TypeScript, the raw-app build, infrastructure policy checks, and all 38 retrieval fixtures.
- Follow-up work is recorded in TKT-0027 and TKT-0028. No schema or application rollback is needed for the audit; the only durable campaign change is the explicit candidate defer disposition preserved by Campaign Core.
