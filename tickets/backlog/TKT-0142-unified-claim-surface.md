---
id: TKT-0142
title: Unified claim surface — one claim card component behind every claim operation
status: backlog
priority: P2
milestone: trustworthy-librarian
depends_on: []  # TKT-0136 closed 2026-09-27 — satisfied
created: 2026-09-21
updated: 2026-09-28
---

# TKT-0142: Unified claim surface — one claim card component behind every claim operation

## Context

Sean's assessment (2026-09-21): "Can all Claim surfaces be unified? This app is a russian doll." It is — because every claim surface is the same transaction re-implemented per layer: a claim (text + subject + truth dimensions + provenance) undergoing an operation (create, promote, supersede, replace, re-attribute, attribute-assign, presumed-retcon) with a review affordance. Built without a shared abstraction, the layers each grew their own editor: the Migration claim form, the session reviewer, extraction review, claim correction/replacement editors, the conflict queue's supersede, brainstorm promotion drafts, the Promotion Review row. The vocabulary (ADR-0017) and the pipeline (ADR-0018) established the domain answer; this ticket is the UI consummation.

## Scope when taken up

- **The claim card component**: composable slots — assertion edit, dimensions (Truth State/authority; defaults inherited per surface), provenance cite (immutable), consequence line (the operation), reason area (supersession/retcon/disposition), and the AI agreement coloring (green = agree, blue = system, orange = AI — the 0137 ruling, live in two surfaces since 2026-09-27, a FIRST-CLASS slot not an optional one). TWO row implementations currently do overlapping claim-review work — the Promotion Review row (seed) and the Description `::` claim review (0146's regroup rows) — both converge onto the card.
- **Unify the card, not the pages**: each surface keeps its idiom (ADR-0015 flow-surface ruling); Brainstorm stays Brainstorm-shaped, Migration stays a queue — the claim card inside them is shared.
- **Convergence plan, phased at natural touchpoints** (no big-bang rewrite; revised 2026-09-28):
  1. Promotion Review row extracts into the shared component (seed).
  2. Description `::` claim review rows converge (regroup ops become card slot compositions).
  3. ClaimReplacementEditor converges (correction/supersession/split flows).
  4. Session review's statement reviewer adopts the card — this IS TKT-0145, which also retires the phase-1 flag and archives the wizard (subsuming the old "Migration steps 3–6 collapse" phase).
  5. The orphan-review queue's rows (TKT-0138, built ahead of the card with simple display rows so the ruled front is not delayed) absorb into the card.
  6. Surfaces born after the card — presumed retcon (TKT-0141), attribute assignment, AI suggestion surfaces — are BORN on the card.
- **Slot composition over flags**: the card serves many masters via composable slots, not a configuration boolean per surface — the failure mode of shared components is config swamps, and the design guard is explicit.
- One component test suite inherits across surfaces as each converges.

## Out of scope

- Forcing surface pages into one layout (idioms stand).
- Backend unification (ADR-0018's facade already owns the transaction side).

## Validation evidence

(to record when built)
