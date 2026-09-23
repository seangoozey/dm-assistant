---
id: TKT-0142
title: Unified claim surface — one claim card component behind every claim operation
status: backlog
priority: P2
milestone: trustworthy-librarian
depends_on: [TKT-0136]
created: 2026-09-21
updated: 2026-09-21
---

# TKT-0142: Unified claim surface — one claim card component behind every claim operation

## Context

Sean's assessment (2026-09-21): "Can all Claim surfaces be unified? This app is a russian doll." It is — because every claim surface is the same transaction re-implemented per layer: a claim (text + subject + truth dimensions + provenance) undergoing an operation (create, promote, supersede, replace, re-attribute, attribute-assign, presumed-retcon) with a review affordance. Built without a shared abstraction, the layers each grew their own editor: the Migration claim form, the session reviewer, extraction review, claim correction/replacement editors, the conflict queue's supersede, brainstorm promotion drafts, the Promotion Review row. The vocabulary (ADR-0017) and the pipeline (ADR-0018) established the domain answer; this ticket is the UI consummation.

## Scope when taken up

- **The claim card component**: composable slots — assertion edit, dimensions (Truth State/authority; defaults inherited per surface), provenance cite (immutable), consequence line (the operation), reason area (supersession/retcon/disposition), and the AI agreement coloring (green = agree, blue = system, orange = AI — the 0137 ruling) as an optional slot. Reuses the Promotion Review row as the seed implementation.
- **Unify the card, not the pages**: each surface keeps its idiom (ADR-0015 flow-surface ruling); Brainstorm stays Brainstorm-shaped, Migration stays a queue — the claim card inside them is shared.
- **Convergence plan, phased at natural touchpoints** (no big-bang rewrite):
  1. Promotion Review row extracts into the shared component (seed).
  2. ClaimReplacementEditor converges (correction/supersession/split flows).
  3. Migration steps 3–6 collapse onto the card (the 0131 plan).
  4. Session review's statement reviewer adopts the card.
  5. New surfaces — presumed retcon (TKT-0141), attribute assignment (0139/0137), AI suggestions — are BORN on the card.
- **Slot composition over flags**: the card serves many masters via composable slots, not a configuration boolean per surface — the failure mode of shared components is config swamps, and the design guard is explicit.
- One component test suite inherits across surfaces as each converges.

## Out of scope

- Forcing surface pages into one layout (idioms stand).
- Backend unification (ADR-0018's facade already owns the transaction side).

## Validation evidence

(to record when built)
