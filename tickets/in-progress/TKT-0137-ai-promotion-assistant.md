---
id: TKT-0137
title: AI Promotion Assistant — wand-marked suggestions inside the Promotion Pipeline, tested on Lore first
status: in-progress
priority: P2
milestone: trustworthy-librarian
depends_on: [TKT-0136]
created: 2026-09-21
updated: 2026-09-27
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

### Lore-first build delivered 2026-09-27 (deployed; live-data runs await a fresh go per the live-pilot rule)

**Stage 1 + Stage 2 for Lore, per the ruled decisions (dedicated purpose, all-async, shared-space placement, restatement-first emphasis):**

- **Purpose + profile**: `promotion` purpose in Settings → AI models ("Promotion assistant") with a selectable `deepseek-chat` candidate profile (extraction-shaped task: precision over voice). NO default — activation is receipted, like prose. The prompt is editable with the receipted override pattern (TKT-0126) and a JSON-contract guard (malformed/partial output becomes a readable provider fault, never partial suggestions).
- **Backend** (`application/promotion_assistant.py`, `promotion/1`): `suggest(subject, kind, prose, material) → SuggestionSet` with the Osirus re-weighting — **restatement matching is the headline** (paraphrase judgment, meaning not word overlap, because the deterministic mirror misses exactly those). Positional references only (statement numbers, material numbers — a modest model cannot invent claim IDs); the harness validates every reference against the provided sets and retries once on contract failure. Secondary: 3–6 statement suggestions with suggested Truth State + basis, and the Link pre-sort. State/subject opinions on the DM's own rows stay out of v1 (the defaults carried all six live statements). Non-Lore surfaces refused — Lore proves the pattern first.
- **Endpoint** `POST /promotion/suggest` (DM-only, non-mutating; 409 with a Settings pointer when no promotion model is active; provider faults read, never 500). **Windmill job** `promotion_suggest` (the prose-draft pattern) + app backend binding — ALL AI calls async per ruling.
- **Lore UI — shared space, wand-marked, never auto-included**:
  - **Suggest** button (wand) beside Draft synopsis; runs on seed + current prose + Considered evidence. The queued job id and the landed set persist IN the working Lore item (loreQueue) — a refresh resumes polling, landed suggestions wait until reviewed (ADR-0019; they never expire into canon).
  - **Restatement suggestions co-display in the review rows** with the ruled agreement coloring, now named tokens (`--agreement-consensus` green / `--agreement-system` blue / `--agreement-ai` orange, documented in ui-conventions): system mirror + AI agree → GREEN consensus label; system-only reference → BLUE; AI-only (mirror missed the paraphrase) → ORANGE wand note quoting the material, with one-click "Mark as reference" (keeps AI origin: "AI-suggested, DM-confirmed") or "Keep as new claim". The DM's pick wins.
  - **Statement suggestions** arrive in a wand-marked block, excluded, with state chip + basis line and per-row provenance ("suggested by {model} · {version}"). Including = "Insert into description" (appends the sentence to the DM's prose, where promotion review derives it with a real span — the pipeline contract that claims trace to the filed document). Dismiss survives refresh too.
  - **Link pre-sort**: orange "Link — {reason}" chips on Consider rows for evidence the model judges to be ABOUT the new record; ranked, never pre-checked.
- **Stage 3 untouched**: no AI at or after the Approve promotion click.
- **Tests**: backend 11 new (positional-reference validation, retry-then-accept, state refusal, non-JSON refusal, Lore-only guard, DM-only + no-profile 409, purpose/profile shape with no default, prompt JSON guard); React 2 new (orange suggestion → mark-as-reference flow; green consensus coloring with no note when system+AI agree) + jobPlatform passthrough; full suites green (React 82/82, backend full run green). Deployed and verified live (route present, job script registered, bundle carries the suggestion UI).

**Open for Sean**: activate the promotion profile in Settings (AI models) and give a fresh go for a real-data lore run; the success bar is recall for consideration, not top-rank precision.

### Description dedup slice delivered 2026-09-27 (deployed) — the Osirus gap closes

Sean's ruling at the 0136 close review: put the dedup on 0137. The Description claim review (the surface where the paraphrase blindness was found) gained **"Check for duplicates"** — the same async suggestion job, now surface-aware:

- **Backend**: the command accepts explicit `statements` (the reviewed `::` rows as the DM edited them — judged verbatim, not re-split) and the `description` surface. The result now carries **`system_restatements`** — the DETERMINISTIC term-overlap mirror (`restates_claim`) computed server-side over the same rows, so the agreement coloring has a system value that never depends on the model. Non-UUID material keys (Lore graph wrappers) skip the mirror; Lore keeps its derive-time system value and is unchanged behaviorally.
- **Composer UI**: "Check for duplicates" (wand) sits above the Description claim review (gated on the entry having existing claims — nothing to dedup against otherwise). Notes co-display in the rows per the placement ruling: **green** "Restatement — system + AI agree" quoting the claim; **blue** "System mirror: restates an existing claim" when only the deterministic side catches it; **orange** "AI suggests this restates an existing claim" (with model provenance) when only the AI catches the paraphrase; and when both flag the same row against DIFFERENT claims, the blue system flag stays and the AI's differing match renders beneath it. One-click **"Exclude row"** — nothing is ever excluded automatically (the mirror marks; the DM decides). Dismissing the AI call ("Keep as new claim") keeps the system's blue flag. Editing a row's wording re-keys the match naturally.
- **Persistence**: the suggestion set, queued job id, and dismissals ride the composer's ADR-0019 working file (`dm-assistant.descriptionWork.{id}`) — a refresh restores prose, rows, and the duplicate check together.
- **Evidence**: backend 13/13 (new: description surface + explicit rows + mirror correctness incl. non-UUID skip and zero-overlap; refusal text updated); React 83/83 (new: the full composer path — derive :: rows, run the check, consensus green, DM excludes the row); full suites green; deployed and bundle-verified. The commit-time duplicate check itself is unchanged — the AI/mirror notes are the review-time mitigation.
