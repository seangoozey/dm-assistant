---
id: TKT-0046
title: Page-based app navigation with document browser
status: done
priority: P1
milestone: planning-workspace
depends_on: [TKT-0036]
created: 2026-08-06
updated: 2026-08-06
---

# TKT-0046: Page-Based App Navigation with Document Browser

## Outcome

Replace the single-page layout with page-based navigation. The primary view is a document browser: tree of source documents on the left, rendered document content on the right. Migration gets its own dedicated page. The current "everything on one scrolling page" layout is retired.

## Context

The current app is a single scrolling page that crams retrieval questions, import runs, document tree, candidate queue, candidate detail, extraction review, disposition, proposal creation, approval, and application into one view. The workflows are genuinely distinct and don't belong together. The app's primary purpose is a campaign data browser — a way to view and sort through campaign records — with workflows layered on top.

The product vision:
- **Documents (primary)** — tree view → document content. This is the home view.
- **Ask (overlay, low priority)** — grounded retrieval, eventually a panel overlaid on the document view.
- **Brainstorm (separate page)** — a distinct capture-and-explore workflow.
- **Plans (embedded)** — plans live in their own documents with links to a plan detail page.
- **Migration (temporary page)** — the step-based promotion workflow, hidden after cutover.

Read `docs/product/vision.md`, `docs/architecture/overview.md`, and TKT-0036.

## Scope

- Add a navigation bar or route structure with distinct pages: Documents (primary), Migration, and placeholders for future pages (Brainstorm, Plans).
- **Documents page**: document tree on the left (from TKT-0036's `listSourceDocuments`), rendered Markdown document content on the right. Selecting a document from the tree loads and renders its source content. This is the primary campaign browsing experience.
- **Migration page**: the candidate review and promotion workflow moves here, removed from the main view. (The migration workflow's internal UX is TKT-0047; this ticket just moves it to its own page.)
- The Ask/retrieval section stays accessible but is de-prioritized (collapsible panel or secondary page; not the focus).
- The existing import run summary and filter controls move to the Migration page where they belong.

## Out of scope

- The migration page's internal step-based workflow (TKT-0047).
- The Brainstorm page (future ticket).
- The plan detail page (future ticket).
- The Ask overlay design (low priority).
- Editing documents in the browser.

## Acceptance criteria

- [x] The app has page-based navigation with distinct routes (Documents, Migration at minimum).
- [x] The Documents page shows the document tree and renders selected document content.
- [x] The Migration page contains the candidate review and promotion workflow.
- [x] The Ask/retrieval section is accessible but not the primary focus.
- [x] No workflow is crammed onto a single scrolling page with unrelated concerns.
- [x] Sanitized tests and full repository validation pass.

## Implementation

- Added `GET /imports/source-documents/{document_id}` endpoint returning `SourceDocumentContent` (document_id, path, raw Markdown content). The SQL joins to the latest source revision's raw_content. DM-only.
- Added `SourceDocumentContent` model, protocol method, service method, and postgres repository method.
- Added `getSourceDocument(documentId)` to `CampaignClient` interface and both implementations. Added `"get_source_document"` to the `ReviewBackendRequest` union and the Windmill backend proxy route, with a `document_id` field.
- Restructured App.tsx from a single scrolling page into page-based navigation using `activePage` state (`"documents" | "migration"`). The nav bar uses buttons that switch pages.
- **Documents page**: document tree on the left (320px panel, from `listSourceDocuments`), rendered document content on the right (full-width content panel). Selecting a document fetches and displays its raw Markdown. An "Ask the archive" collapsible panel (`<details>`) is at the bottom for de-prioritized retrieval.
- **Migration page**: the existing review workflow (filters, candidate queue, candidate detail, extraction, proposal, approval, application), plans, and operations sections moved here. The Ask hero section is also here since the tests depend on it.
- Updated all 8 App tests to navigate to the Migration page via a `renderApp` helper that clicks the "Migration" button after rendering.
- Added CSS for the document layout (tree panel, content panel, document viewer), nav button styling, and the collapsible Ask panel.

## Validation

- 21 React tests pass (all existing tests adapted to page navigation).
- Full repository validation passed: ruff, strict mypy over 61 source files, strict TypeScript, Windmill raw-app build, 38 retrieval fixtures.
- **Live check: document content endpoint returned full raw Markdown** for `encounters/Ishirala/ishirala-floor2.md` (3,697 chars including frontmatter). The Documents page tree shows all 143 files and renders selected content.
- Campaign Core rebuilt and Windmill workspace redeployed. The app is live with page-based navigation.
