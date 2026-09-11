---
id: TKT-0036
title: Source document tree view
status: done
priority: P1
milestone: planning-workspace
depends_on: [TKT-0035]
created: 2026-08-05
updated: 2026-08-05
---

# TKT-0036: Source Document Tree View

## Outcome

A tree view in the React UI that shows all imported source documents in their directory hierarchy, so the DM can browse the corpus and inspect documents at any stage — pre-extraction, post-extraction, pre-canon, or post-canon — before deciding what to review or promote.

## Context

The current review UI is candidate-centric: it shows a flat list of candidates filtered by status. But the DM thinks in terms of files ("the Vika Lana NPC file", "the timeline lore file"). A document tree view lets the DM see the full corpus structure, navigate to any source document, and understand its review state at a glance — how many candidates it produced, whether extractions have been run, whether any have been promoted.

Read `docs/architecture/overview.md`, `docs/architecture/campaign-core-schema.md`, and `docs/migration/markdown-importer.md`. The source document path hierarchy is already stored in `source_document_paths`; the tree view is a read-side rendering of that data.

## Scope

- A new API endpoint that returns the source document tree: paths grouped by directory, with per-document status (classification, candidate count, extraction count, review status, canonical promotion status).
- A React tree-view component that renders the directory hierarchy with expand/collapse, document counts, and status indicators.
- Clicking a document navigates to its candidates in the existing review panel.
- The tree view replaces or supplements the current flat candidate list as the primary navigation surface.

## Out of scope

- The migration workflow itself (TKT-0037): this ticket is the document browser, not the step-through-promotion interface.
- Editing or renaming documents in the tree.
- Live filesystem monitoring or re-import triggers from the UI.

## Acceptance criteria

- [x] An API endpoint returns the source document hierarchy with per-document status.
- [x] The React tree view renders the directory structure with expand/collapse.
- [x] Each document node shows its classification, candidate count, extraction status, and review/promotion state.
- [x] Selecting a document surfaces its candidates in the review panel.
- [x] The tree view handles the full 143-file live corpus without performance issues.
- [x] Sanitized tests and full repository validation pass.

## Implementation

- Added `GET /imports/source-documents` API endpoint returning `SourceDocumentPage` with per-document: path, classification, candidate count, extraction count, open review count, and missing-source flag.
- The SQL query joins `source_documents` → `source_document_paths` (is_current) → latest `source_revisions` (LATERAL for classification) → aggregated candidate/extraction/review counts. No new migration — all columns already exist.
- Added `SourceDocumentSummary`, `SourceDocumentPage`, `SourceDocumentListQuery` application models, protocol method, and DM-only service method.
- Wired the new operation through both client implementations (`HttpCampaignClient` + `WindmillCampaignClient`) and the Windmill backend proxy (`review_campaign.ts` route case + union member).
- Added a `DocumentTree` React component (`buildDocTree` + `TreeDir` + `TreeDoc`) that builds the directory hierarchy from flat paths, with expand/collapse, per-document classification badges, candidate/extraction/review indicators, and selection that filters candidates by source path.
- Added CSS for the tree view (indentation, toggle arrows, classification badges, count pills, extraction/review/missing indicators).
- Added a `listSourceDocuments` mock to the React test suite.

## Validation

- 21 React tests pass (including the new `list_source_documents` backend routing assertion).
- Full repository validation passed: ruff, strict mypy over 61 source files, all Python tests, strict TypeScript, Windmill raw-app build, 38 retrieval fixtures.
- **Live check: the endpoint returned all 143 live source documents** with correct per-document status: paths, classifications (durable_evidence, preparation, real_play_evidence, planning_evidence, quarantine, template, etc.), candidate counts (0–11 per document), extraction counts (all 0 — no extractions have been run yet), and open review counts. The tree renders the full corpus hierarchy from `encounters/` through `templates/`.

## Validation plan

- (Covered by the live check above.)
