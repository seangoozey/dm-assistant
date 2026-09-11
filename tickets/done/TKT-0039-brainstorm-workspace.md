---
id: TKT-0039
title: Brainstorm workspace vertical slice
status: done
priority: P1
milestone: trustworthy-librarian
depends_on: [TKT-0038]
created: 2026-08-04
updated: 2026-08-30
---

# TKT-0039: Brainstorm Workspace Vertical Slice

## Outcome

The two-panel Brainstorm experience: capture every thought outside canon, refresh a side panel with grounded evidence and surfaced contradictions/consequences from canon, and end with a versioned promotion proposal across affected records.

## Context

Brainstorm is the flagship thinking workspace from the product vision. It builds on direct capture (TKT-0038), grounded retrieval (existing `/ask`), and the extraction pipeline (TKT-0035) for contradiction/consequence surfacing. All brainstorm content remains non-canon until exact versioned promotion.

Read `docs/product/vision.md`, `docs/architecture/workflows.md`, `docs/product/invariants.md`, and TKT-0038.

## Scope

- A `workflow_session` of kind `brainstorm` with parent/child session support for nested direct-lore operations.
- Capture-into-session binding so each submitted thought is preserved and linked to its brainstorm.
- An evidence side panel that runs grounded retrieval against existing canon after each submission, showing supporting facts, contradictions, and consequences.
- A React two-panel view: capture on the left, refreshed evidence on the right.
- Ending the brainstorm with a versioned promotion proposal using the existing candidate-proposal path.

## Out of scope

- Auto-promotion of any brainstorm thought.
- Audio Brainstorm (separate batch).
- The Lore Entry and Real Play experiences (TKT-0040 and a future ticket).

## Acceptance criteria

- [x] A brainstorm session captures and preserves every submitted thought as non-canon evidence.
- [x] The evidence side panel refreshes with grounded retrieval results after each submission.
- [x] Contradictions and grounded consequence checks surfaced by the continuity pipeline are visible in the side panel.
- [x] Ending the brainstorm produces a versioned promotion proposal through the existing path.
- [x] No brainstorm thought becomes canonical without explicit human approval.
- [x] Sanitized tests and full repository validation pass.

## Validation plan

- A synthetic brainstorm session capturing thoughts and verifying the side-panel retrieval.
- Confirm the closing proposal is versioned and scoped, not bulk-promoted.

## Implementation notes

- Consequence checks are deliberately derived from retrieved canonical context rather than invented connective lore. They identify records whose continuity should be reviewed if the thought is promoted.
- Strengthening brainstorm evidence into lore, preparation, or NPC intention is accepted only when the candidate belongs to the active Brainstorm workflow session. The resulting proposal remains pending until normal exact-version review, approval, and application.
- Validation: 311 Campaign Core tests passed with 35 environment skips; 65 React/Windmill tests passed; strict mypy, Ruff, TypeScript, raw-app build, retrieval corpus, and the deterministic repository validator passed. The isolated PostgreSQL migration/proposal suite passed 32 tests.
