---
id: TKT-0115
title: Brainstorm findability — prior thinking searchable under ADR-0017 vocabulary
status: done
priority: P2
milestone: shared-campaign-knowledge
depends_on: []
created: 2026-09-13
updated: 2026-09-19
---

# TKT-0115: Brainstorm findability — prior thinking searchable under ADR-0017 vocabulary

## Context (rewritten 2026-09-19 under ADR-0017)

The original framing ("brainstorm truth state — findable without granting canon") is resolved by ADR-0017's Truth State spectrum: Considered is the lowest rung, brainstorm thoughts are Sources, and promoted possibilities are Claims at the Considered state. "Non-canonical" no longer exists as a concept — everything has a Truth State.

**The remaining gap is findability of UN-promoted thinking.** After a brainstorm session closes, its thought text is reachable only through the Migration queue. A later brainstorm cannot ask "what did we already consider about the Long Night?" without manually scrolling through closed sessions.

## Design (ADR-0017-compliant)

- **"Possible" state displays as "Considered"** in the UI — matching ADR-0017's vocabulary. The DB value stays "possible" (no migration needed); this is a display rename.
- **Prior brainstorm search**: the Brainstorm page's search expands to include closed sessions' thought text. Results are labeled "Prior brainstorm thinking" and are Sources (not Claims) — findable as context, clearly not established truth.
- **Not in this ticket**: auto-extraction of Considered claims from thoughts (the existing promotion path handles that), graph participation for brainstorm Sources.

## Scope

1. **State display rename**: "Possible" → "Considered" across all state selectors, claim cards, and Brainstorm copy (the DB enum value "possible" stays).
2. **Prior brainstorm search**: the Brainstorm continuity panel's search includes closed sessions' thoughts alongside canonical Claims. Prior-session results appear in a clearly-labeled section with the session title, date, and thought text.
3. **Glossary alignment**: the existing Truth State entry already names Considered; the observed/prepared/intended/established entries update their short text to use "Considered" not "Possible" where referenced.

## Validation evidence

(to record when built)

## Validation evidence

Delivered 2026-09-19, deployed.

- **"Possible" → "Considered" display rename**: all 4 state-select dropdowns, both "Possibilities" section headings (now "Considered"), the brainstorm "Retain as possibility" option (now "Considered"), and the brainstorm empty-state copy. The DB enum value stays "possible" — no migration.
- **Prior brainstorm search**: when the continuity panel's search runs (3+ chars), it also searches closed brainstorm sessions' thought text (source documents under `gm/brainstorming/direct/`). Matching thoughts appear in a "Prior brainstorm thinking" collapsed section with the session title, the thought excerpt, and a "Source — brainstorm thought, not a Claim" citation. Capped at 5 results. Lazy — only fetches brainstorm documents when the search executes.
- React 137/137.

### CTS correction (2026-09-19, deployed)

Sean's clarification: Considered is IN ADDITION TO Possible, not a replacement. The CTS is six states. The earlier display rename that collapsed Possible into Considered was undone; both now appear as separate options in all state selects.

- **Six-state CTS** (recorded as ADR-0017 amendment): Considered ("worked through, found a route that precludes it" — parked, not rejected) → Possible ("available to happen, no known blockers") → Prepared ("DM material exists, not encountered") → Intended ("stated plan") → Established ("confirmed fact") → Observed ("witnessed at the table"). Any → Observed always possible; direct → Established avoided (that's Considered's purpose); Prepared is sticky (can't un-prepare even if the scenario dies).
- **DB migration 0065**: `claim_state` enum gains `considered` before `possible`.
- **Glossary**: Truth State entry updated to the full six-state definition with transition rules.
- **All four state selects** now offer Considered alongside Possible.
- React 137/137.
