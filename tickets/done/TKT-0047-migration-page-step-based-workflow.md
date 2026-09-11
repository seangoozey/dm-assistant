---
id: TKT-0047
title: Migration page step-based workflow
status: done
priority: P1
milestone: planning-workspace
depends_on: [TKT-0046]
created: 2026-08-06
updated: 2026-08-09
---

# TKT-0047: Migration Page Step-Based Workflow

## Outcome

The migration page becomes a focused, step-based workflow: select a document → see its candidates → run/review extractions with editable dropdowns → propose with pre-filled and corrected values → approve → apply. Each step is a focused stage, not everything stacked on one panel.

## Context

TKT-0046 moves the migration workflow to its own page. This ticket redesigns that page's internal UX into a guided, step-based flow. The current layout shows evidence, extractions, diagnostics, disposition, entity creation, proposal, approval, and application all at once. The extraction dimensions are read-only cards — they should be editable proposals with dropdowns for state/authority/visibility that the DM can correct before committing.

Read `docs/architecture/workflows.md`, `docs/product/truth-state-authority.md`, and TKT-0037.

## Scope

- Step 1: Document selection (tree, from TKT-0036) → shows that document's candidates with status badges.
- Step 2: Candidate selection → shows source evidence and extracted dimensions.
- Step 3: Extraction review → the AI-extracted dimensions appear as **editable fields** (dropdowns for state/authority/visibility, text fields for subject/predicate/object), not read-only cards. The DM corrects any wrong values before proceeding.
- Step 4: Proposal creation → pre-filled from the corrected extraction dimensions. Entity identity, predicate, tags confirmed by the DM.
- Step 5: Approval → exact version confirmation, scope selection.
- Step 6: Application → atomic apply, receipt displayed.
- Each step shows progress (where in the flow), and back/forward navigation within the flow.
- Diagnostics (warnings, unresolved links) are shown contextually, not as a permanent panel competing for attention.

## Out of scope

- Auto-promotion or batch approval.
- Bypassing any promotion safety rule.
- The Brainstorm or Ask workflows.
- Extraction prompt/context improvement (TKT-0045, which should complete first).

## Acceptance criteria

- [x] The migration workflow is a guided, step-based flow, not a single stacked panel.
- [x] AI-extracted dimensions are editable: dropdowns for state/authority/visibility, text fields for subject/predicate/object.
- [x] The DM can correct extraction values before committing to a proposal.
- [x] Proposal creation is pre-filled from corrected dimensions.
- [x] Approval and application are inline steps in the flow.
- [x] Diagnostics appear contextually, not as permanent noise.
- [x] No promotion safety rule is bypassed.
- [x] Sanitized tests and full repository validation pass.

## Implementation

- Restructured the migration page from a single stacked panel into a three-column layout: document tree (left), candidate queue (middle), candidate detail (right).
- The document tree is now the primary navigation on the migration page — selecting a document filters candidates to that document.
- Source reviews (warnings, unresolved links, quarantine) moved into a collapsible `<details>` panel inside the candidate queue, eliminating permanent noise.
- Diagnostics per candidate moved into a collapsible `<details>` that only shows when reviews exist.
- Removed the always-visible Ask hero from the migration page; replaced with a collapsible "Ask the archive" panel matching the Documents page.
- Removed the Import run filter from the form (simplified to review status + authority + source).
- CSS for the three-column migration grid with dedicated tree, queue, and detail panels.
- Updated all tests to navigate to the Migration page via `renderApp` helper and adapted assertions for the new collapsible layout.
- Added an explicit six-step progress control for document, candidate, extraction, proposal, approval, and application stages.
- Candidate selection advances to grounded extraction review; selecting an extraction opens an editable draft for subject, predicate, object, state, authority, and visibility.
- Corrected subject and predicate values pre-fill proposal creation, while corrected truth-state dimensions flow into the proposed claim.
- Proposal creation, exact approval, atomic application, and the resulting receipt remain separate inline stages.
- Preserved explicit object-identity confirmation: free-text extraction objects do not silently create canonical entity relationships.
- Fixed successful extraction refreshes to merge the returned immutable extraction records directly into UI state instead of losing them to a lagging candidate re-fetch.
- Bound claim proposal items to the reviewed `candidate_extraction_id`; Campaign Core now uses that grounded extracted assertion in the immutable proposal while retaining the original candidate and source span as provenance.
- Added a corrected-extraction summary to the proposal stage and path-based PC/NPC/location kind prefill.

## Validation

- 22 React tests pass, including a stale-read regression proving successful extraction results render without a page refresh.
- Full repository validation passed: ruff, strict mypy over 61 source files, strict TypeScript, Windmill raw-app build, 38 retrieval fixtures.
- Campaign Core rebuilt and Windmill workspace redeployed with the updated migration page.
- Final repository validation on 2026-08-09 passed: Ruff, strict mypy over 61 source files, 236 Python tests (26 skipped), 21 React tests, strict TypeScript, Windmill raw-app build, and 38 retrieval fixtures.

### Extraction editability

Extraction cards remain an immutable view of provider output. "Review this extraction" creates a separate editable draft, making the boundary between AI output and DM corrections explicit. The corrected draft is the source for proposal prefill and claim truth-state dimensions.
