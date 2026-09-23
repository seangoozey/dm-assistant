---
id: TKT-0137
title: AI Promotion Assistant — wand-marked suggestions inside the Promotion Pipeline, tested on Lore first
status: backlog
priority: P2
milestone: trustworthy-librarian
depends_on: [TKT-0136]
created: 2026-09-21
updated: 2026-09-21
---

# TKT-0137: AI Promotion Assistant — wand-marked suggestions inside the Promotion Pipeline, tested on Lore first

## Context

Sean's ruling (2026-09-21): the Promotion Pipeline should accept AI support, targeted at **Lore first for testing**. ADR-0018 point 7 fixes the four AI seams (draft the proposal, gather evidence, suggest candidates, suggest subjects) and the hard rule — AI never auto-includes, never gates, never executes the commit. Point 8 (mandatory statement review) makes the DM's per-statement include-or-exclude decision the compliance mechanism; the assistant reduces typing and surfaces candidates worth considering, and never touches that decision. This ticket is the design proposal for review before implementation.

## What the assistant does

**Stage 1 — Proposal (Lore surface):**
- **Link/Consider pre-sort**: for each piece of gathered evidence, a wand-marked suggestion whether it should Link (re-attribute into the new entry — "this claim is really ABOUT the Treasury, not the Exiles") or stay Consider (context only). Ranked, not pre-checked — Sean checks Link himself.
- **Statement suggestions**: from the seed name + gathered evidence, propose 3–6 statements the new lore entry might assert, each with a suggested Truth State and a one-line basis referencing the evidence key it came from.

**Stage 2 — Candidates (review list):**
- AI-suggested rows arrive **excluded, wand-marked, with provenance** ("suggested by {model}, {version}") — never auto-included (ADR-0018). Include, edit, or reject inline; edited suggestions keep their origin for audit (AI-suggested, DM-edited).
- A suggested-state chip appears where the model disagrees with the surface default, with its one-line why.
- AI **tension notes** (e.g. "this may clash with the vault claim") render as suggestions, visually distinct from the deterministic conflict flag — per the consequence≠conflict ruling, the flag keeps its narrow meaning and an unflagged statement is never guaranteed clean.

**Stage 3 — Commit: untouched.** No AI involvement at or after the Approve promotion click.

## Mechanics

- New per-purpose model profile: purpose **`promotion`** in Settings → AI models, with receipted activation and an editable, version-stamped prompt (prompt_configuration pattern; JSON-contract guard like extraction — malformed or partial output becomes a readable provider fault, never partial suggestions).
- Backend: `application/promotion_assistant.py` — `suggest(surface, seed, gathered_evidence) → SuggestionSet` (statements + states + link/consider calls + bases). Runs only on an explicit **Suggest** click, through the budget gateway.
- Delivery: async Windmill job (prose-drafting pattern) landing in the working Lore item, which already persists through refresh — suggestions wait in the review list until reviewed, never expire into canon.
- Audit: every suggestion outcome (included / edited / rejected) is derivable from receipts + origins; success bar is **recall for consideration** (did it surface what Sean wanted to consider?), not top-rank precision.

## Why Lore first

It is the next 0136 adoption slice anyway (bound-created owner + re-attribution), the queue is low-stakes, the working item survives refresh, and it exercises both suggestion kinds (new statements + moves-from). Real-data runs on live lore items need a fresh go per the live-pilot rule.

## Open decisions — ruled 2026-09-21

1. **Purpose slot**: dedicated `promotion` purpose — RULED dedicated by Sean.
2. **Async vs sync**: RULED by Sean — ALL AI calls async ("they take 30 seconds"); no synchronous AI anywhere.
3. **Suggestion placement — Sean's vision (2026-09-21, pending his own Description pass)**: SHARED SPACE — no separate section. The promotion card's pickers (Truth State, entity/subject where the surface has them) are dropdown/combo-edit controls, and the AI suggestion co-displays in the same control with agreement coloring:
   - **AI and system agree** → one value, listed GREEN.
   - **They disagree** → the SYSTEM's value listed BLUE, the AI's listed ORANGE, side by side in the same control; the DM's pick wins (one click adopts either).
   The user never hunts to a different section for the AI's opinion — it lives in the row. Color semantics: green = consensus, blue = deterministic/system, orange = AI suggestion; these become named semantic tokens in ui-conventions when built (never bare colors). Sean will check the Description review list and update this with refinements.

## Attribute promotion — blocked on a mechanism (Sean, 2026-09-21)

AI can be tasked with suggesting ATTRIBUTE assignments during promotion assistance (attribute-shaped statements → structured fields: race, location_type, parent_location, status…), with the green/blue/orange agreement treatment on the value. **Blocked: there is no Attribution-as-a-Claim mechanism** — attributes are written directly to the profile with receipts but no claim, evidence span, Truth State, or supersession, so promoted attributes would be canon-without-provenance (the Summary-field violation at scale). Prerequisite: generalize the life_status claim-anchor pattern to all attributes (recommended v1) or rule full claims-derived profiles in TKT-0139. Terminology: needs a name distinct from re-attribution (ownership moves) — suggested "claim-backed attribute assignment."

## Evidence from live use (Osirus description review, 2026-09-21)

Sean reviewed the live Promotion Review on Osirus's description (6 prose statements vs 3 gathered claims, mostly paraphrases) and ruled: **the designed v1 suggestions would not have been useful there.** The DM's actual toil was recognizing which statements already exist — not wording (the DM wrote it) and not Truth States (the default carried all six). Two consequences:

- **Restatement matching is the killer feature, not state/subject suggestions.** The deterministic mirror detector is term-overlap based and missed every paraphrase ("Osirus is the god that created Myrin" vs the Dusk-of-Creation claim shares too few terms); the commit-time duplicate check shares the blindness. v1 suggestion emphasis re-weights to: **AI restatement suggestions** — "model suggests: statement N restates gathered claim #M" as a wand-marked suggestion the DM confirms (green when system mirror and AI agree; blue/orange when they disagree, per the placement ruling). State/subject suggestions demote to secondary.
- **Slice-1 gap logged (0136)**: deterministic paraphrase blindness means near-duplicate claims can be approved today. Known limitation; the AI suggestion above is the mitigation path, plus any tightening of the deterministic gate that survives honest scoping.

## Out of scope

- Auto-include, auto-commit, gating (permanently, per ADR-0018).
- AI conflict detection replacing or feeding the deterministic flag.
- Brainstorm/Description surfaces (after Lore proves the pattern).

## Validation evidence

(to record when built)
