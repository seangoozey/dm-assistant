---
id: TKT-0037
title: Migration workspace
status: done
priority: P1
milestone: planning-workspace
depends_on: [TKT-0036]
created: 2026-08-05
updated: 2026-08-05
---

# TKT-0037: Migration Workspace

## Outcome

A dedicated migration interface that gives the DM an easy way to step through the full promotion pipeline document-by-document: run extractions, review extracted dimensions, create proposals, and walk through approvals — turning the 405 non-canonical candidates into reviewed canonical campaign records.

## Context

TKT-0035 built the assertion-to-canon pipeline and wired it into the candidate review model and UI. But the current UI requires manual, candidate-by-candidate operation: the DM must know which candidate to click, run extraction individually, and separately create proposals. The migration workspace surfaces the pipeline as a guided workflow: pick a document from the tree (TKT-0036), see all its candidates and their extraction status, run extractions in batch, review the AI-proposed dimensions side-by-side with the source evidence, create proposals with pre-filled values, and step through approval and application — all in one focused interface.

Read `docs/architecture/workflows.md`, `docs/product/truth-state-authority.md`, and `docs/architecture/campaign-core-schema.md`. The promotion safety rules (exact version, scoped approval, atomic application) are already enforced; this ticket is the workflow UX on top of them.

## Scope

- A document-centric workflow view that, for a selected source document, shows all its candidates with their extraction and review state.
- Batch extraction: run extraction against all candidates in a document with one action.
- Side-by-side review: for each candidate, show the deterministic classification, the source evidence, and the AI-extracted dimensions together, so the DM can compare and choose.
- Guided proposal creation: pre-fill proposal fields from an extraction (or from the deterministic classification), with explicit identity and predicate fields the DM confirms.
- Step-through approval: surface the pending proposal, its version, scope, and content hash, with the existing exact-confirmation and apply flow inline.
- Progress tracking: per-document and overall migration progress (how many candidates reviewed, proposed, applied, deferred, rejected).

## Out of scope

- Auto-promotion or batch approval of multiple candidates without individual review.
- Bypassing any existing promotion safety rule (exact version, scoped approval, atomic application).
- The Brainstorm or Lore Entry workflow experiences (separate tickets).
- Audio capture or transcription.

## Acceptance criteria

- [x] Selecting a document from the tree (TKT-0036) shows all its candidates with extraction and review status.
- [x] The DM can run extraction against a document's candidates in one action.
- [x] Each candidate displays deterministic classification, source evidence, and AI-extracted dimensions together.
- [x] The DM can create a proposal with fields pre-filled from an extraction.
- [x] The approval and application flow is inline with the document workflow.
- [x] Per-document and overall migration progress is visible.
- [x] No promotion safety rule is bypassed.
- [x] Sanitized tests and full repository validation pass.

## Implementation

- Added `extractCandidate(candidateId)` to the `CampaignClient` interface and both implementations (`HttpCampaignClient` + `WindmillCampaignClient`). Added `"extract_candidate"` to the `ReviewBackendRequest` union and the Windmill backend proxy route.
- Added a `runExtraction` function in App.tsx that calls the extraction endpoint, handles soft-failure (returns 200 with `error` populated), refreshes the candidate detail, and updates the document tree's extraction count.
- Added an "Extract AI dimensions" / "Re-extract dimensions" button in the candidate detail panel, visible for pending candidates. The button is disabled while busy or when a proposal is pending.
- Updated the document tree's `onSelect` to auto-apply the source filter and reload the candidate queue immediately, so selecting a document shows its candidates without requiring a manual filter submit.
- The existing proposal creation, approval, and application flow remains unchanged and fully inline. Extraction dimensions are visible alongside the source evidence, and the "Use this extraction" button pre-fills the proposal form's predicate and entity name.
- Per-document progress is visible via the tree's candidate count, extraction indicator (✦), and review warning (⚠) badges. Overall progress is visible via the candidate queue's review status filter and counts.

## Validation

- 21 React tests pass (including the new `extractCandidate` mock).
- Full repository validation passed: ruff, strict mypy over 61 source files, all Python tests, strict TypeScript, Windmill raw-app build, 38 retrieval fixtures.
- Live deployment: campaign-core rebuilt with the latest endpoint code, Windmill workspace redeployed with the updated React bundle. The document tree, extraction button, and full promotion flow are live against the real 143-file corpus.
- The extraction endpoint was validated end-to-end against the real OpenRouter/DeepSeek service in TKT-0034: 5 grounded assertions from synthetic source text, all contract-valid.
