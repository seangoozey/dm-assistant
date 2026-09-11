---
id: TKT-0040
title: Lore Entry with conflict-gated direct application
status: backlog
priority: P1
milestone: trustworthy-librarian
depends_on: [TKT-0038, TKT-0091, TKT-0094]
created: 2026-08-04
updated: 2026-08-05
---

# TKT-0040: Lore Entry with Conflict-Gated Direct Application

## Outcome

Captured and extracted assertions are applied deterministically when unambiguous and non-conflicting, with a receipt. The system stops on identity ambiguity, contradiction, or possible retcon for human review.

## Context

Lore Entry is the safe canonical write without a full proposal round-trip. It uses direct capture (TKT-0038), the assertion pipeline (TKT-0035), and the existing `apply_change_set` boundary, but adds an inline conflict/authority resolution service that decides auto-apply versus stop-for-review based on the truth-state-authority table.

Read `docs/product/truth-state-authority.md`, `docs/architecture/workflows.md`, `docs/architecture/campaign-core-schema.md`, and TKT-0038.

## Scope

- Use the shared knowledge service (TKT-0094) to locate affected and comparable records, with corrected evidence comparison policy (TKT-0091). Do not create a Lore-specific graph or infer safe automatic application from absence of retrieved conflicts. Coordinate the user-facing integration with TKT-0095.
- An application service that evaluates a candidate's claim dimensions against existing canon using the authority and conflict rules (truth-state-authority table).
- Auto-application with a receipt when the assertion is unambiguous, non-conflicting, and the authority rule permits direct application.
- Stop-for-review with a review item on identity ambiguity, contradiction, or possible retcon.
- A `/lore-entry` endpoint that captures text, extracts, evaluates, and applies-or-stops in one transaction-bound flow.

## Out of scope

- Auto-extraction itself (TKT-0035 provides the pipeline).
- The Brainstorm experience (TKT-0039).
- Real Play observation capture and retcon comparison (future ticket).
- Overriding an explicit conflict without a reviewed resolution.

## Acceptance criteria

- [ ] An unambiguous, non-conflicting assertion is applied canonically with a receipt through the existing change-set boundary.
- [ ] A conflicting assertion stops for review and creates a review item without partial mutation.
- [ ] A possible-retcon case stops for comparison review without canonical overwrite.
- [ ] Identity ambiguity prevents automatic application.
- [ ] No application bypasses the `apply_change_set` transaction or its receipt.
- [ ] Sanitized tests and full repository validation pass.

## Validation plan

- A sanitized non-conflicting lore entry proving automatic application and receipt.
- A sanitized conflicting entry proving stop-for-review with zero canonical mutation.
