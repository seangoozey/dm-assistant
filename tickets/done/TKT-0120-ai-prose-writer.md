---
id: TKT-0120
title: Reusable AI prose writer — gather, draft from selected material, cite support
status: done
priority: P2
milestone: shared-campaign-knowledge
depends_on: [TKT-0111, TKT-0099]
created: 2026-09-15
updated: 2026-09-16

---

# TKT-0120: Reusable AI prose writer — gather, draft from selected material, cite support

## Context (Sean, 2026-09-15)

"Many forward looking surfaces will want this" — descriptions (TKT-0111), lore creation (TKT-0099), session debriefs, handoffs. The writer is a shared surface, not a feature of any one page: built once, consumed everywhere, like the toast bus.

## Scope when taken up

- **The contract** (inherits TKT-0099's drafting rules verbatim): drafts are produced ONLY from the gathered/selected material passed in; each passage carries its citation back to what supported it; uncertainty is preserved in the prose; plans are never written as outcomes. Explicit opt-in per draft — never automatic.
- **A shared UI component**: a composer panel any surface embeds — shows the gathered material (claims, evidence excerpts, aliases, roles), lets the DM select/deselect what the draft may draw from, a Draft action, an editable result with per-passage support shown, and a save path defined by the host surface (descriptions file entity documents; lore creation files through its queue).
- **Provider path through Campaign Core**: credentials never in the browser; a dedicated writer profile beside extraction in the existing AI configuration; budget-gated and usage-reported like every provider call; Core stamps drafts as machine-drafted so downstream surfaces can label provenance honestly.
- **Consumers register, not reimplement**: 0111's description composer and 0099's synopsis are the first two hosts.

## Out of scope

- Auto-drafting on open; the Draft button is always a deliberate act.
- Any surface-specific prose conventions — hosts own their framing, the writer owns gather/draft/cite.

## Gather design: two layers (agreed 2026-09-16)

- **Base layer, always on**: Core-served relations — members, roles/seats, related co-mentions — receipt-backed, no graph dependency.
- **Expansion layer, opt-in**: graph neighborhood traversal (1–2 hops over audited member_of/leader_of edges, ranked co-mentions) as a discovery aid. Two standing watch-outs (Sean affirmed): (1) graph rows are cited to the canonical records behind the edge, never to graph edges (the graph is derived/rebuildable); (2) brainstorm's recall profile and the writer's precision profile must be separate, explicitly named configurations — recall must never leak into drafting.

## Prose model chosen (2026-09-16)

Sean's first pick: `deepseek-v4-flash` (openrouter `deepseek/deepseek-v4-flash-0731`) — cheap, fast, non-reasoning flash tier, registered as a `candidate` profile under the prose purpose (TKT-0124's Settings slot). Activation is Sean's click in Settings. The writer's Draft action will consume `active_profile("prose")`; suitability upgrades from `candidate` only after real drafting use.

## Fleurite drafting trial (2026-09-16 — graph expansion verdict: worth it)

A/B trial with drafter subagents on identical instructions/rules, only the input varying: **A** = Fleurite's 17 linked claims; **B** = same claims + graph relations from the live-pilot-v5 bundle (audited seats, ranked co-mentions, Exiles/Castle clusters). Artifacts: `.local/fleurite-trial/` (materials, both drafts).

- **Groundedness**: both routes zero inventions; both correctly quarantined the four `prepared`/dm_plan claims as prep-not-history. The 0099 rules held without graph info.
- **Graph's unique contribution in B**: (1) genuinely new grounded facts absent from the linked claims — Jace Valamacke leads the Fleurite Exiles (with Lily a member) reached the draft, correctly cited to graph; (2) salience/organization — B surfaced the Assassins Guild's taught betrayal account (claim 20506bef) as a live continuity conflict against the record (claim f5aec94c) and ruled "preserve as indoctrination-versus-record rather than harmonized" — the retcon-comparison instinct — while A, holding the same claims, flattened it away; (3) explicit corroboration ("the graph's audited edges are consistent with this picture") properly subordinated to claims.
- **Failure mode observed**: one malformed citation in B (nonexistent claim ID `4712e08c` for `4712d8d6`) — citation integrity must be validated against the gather set before a draft can be filed; a bad reference breaks the stale-flag chain.
- **Caveats**: both drafts ran on the same model family (subagents), so this isolates the input delta, not model quality — with a genuinely cheaper model the gap is expected to widen (structure substitutes for reasoning). n=1 (one entity, one run).

## V1 delivered (2026-09-16, deployed, live-verified) — the writer's Core contract + first host

- **Core** (`application/prose_drafting.py`): `prose/1` system prompt carrying the 0099 rules verbatim (draft only from provided material; cite every assertion; never narrate intended/prepared/possible as accomplished; preserve uncertainty; prose only, paragraph limit). Citations are **positional** (`[3]` = material item 3) so a modest model cannot fabricate claim IDs — the Fleurite trial's failure mode is unreachable by construction. `ProseHarness` validates every marker against the material set (retry once with the rejection reason; refuse on persistent violation — no partial output), requires at least one valid citation, and JSON-parses the response. `POST /prose/draft` (DM-gated, non-mutating — a draft is a machine-drafted suggestion the DM disposes of through the normal authoring path; no campaign records change). Builds per request from the ACTIVE prose profile (409 with a Settings hint when none is active; 503 when no provider key).
- **First host — the description composer (0111)**: "Draft from selected" (opt-in button in the gathered-claims panel; shows "activate a prose model in Settings" when none is active). Material = the selected claims with truth states; the returned prose lands clean of positional markers (references are the claim selection), the selection mirrors the draft's citations, and the result is labeled machine-drafted with model + token counts — honest provenance per the Core-side stamping requirement.
- **Live verification (2026-09-16/17)**: Sean activated `deepseek-v4-flash` in Settings (receipt filed); a live one-item material call produced a correctly-cited draft that refused to invent beyond its material — the contract holding under real use.
- Validation: Core 7/7 prose tests (citation validation, retry semantics, refusal, DM-only, Settings-gap error) + local suite 454/70; React 125/125 incl. the draft flow (material shape asserted, markers stripped, machine-drafted labeling).

## Remaining (next slices)

- **Two-layer gather**: Core-served relations (members/roles/related as selectable material rows — the always-on base layer) and the opt-in graph expansion layer (audited member_of/leader_of neighborhood, ranked co-mentions; relations as `kind: "relation"` material, cited to the records behind the edges).
- Other hosts: 0099's synopsis; session debriefs later.
- Suitability review: `deepseek-v4-flash` upgrades from `candidate` after real drafting use.

## V1.1 (2026-09-17) — discoverability fix after Sean's "no apparent interface" report

The Draft action had shipped inside the gathered-claims details panel — collapsed and invisible for zero-claim entries. Fixed: the action row (Draft from selected + model/token note, or the activate-in-Settings hint) now sits directly under the description textarea, above the claims panel; the composer explainer names the Draft option explicitly for both fresh writes and revisions. Deployed as app version 222 (verified in the windmill app_version table).

## V1.2 (2026-09-17) — two live defects from Sean's first real Draft click

1. **Worker TypeError (`selected.path` undefined)**: the review backend bridge (`backend/review_campaign.ts`) had no `draft_prose` case — `route()` fell through to `undefined` and the worker crashed. Added the route (`POST prose/draft`, DM-gated) + backend unit test asserting method/path/role. Deployed as app version 223 (verified in windmill storage).
2. **Error toasted but absent from the Log**: the bus itself was correct (unit-proven: toast + log + Log page all record the failure), but the session log was in-memory only — any reload erased it, breaking the Settings promise "every outcome is still recorded in the Log regardless." The log now persists to `localStorage` (`dm-assistant.sessionLog`, same 200-entry cap), hydrates on load, survives reloads; resetForTest clears storage too. Log page copy updated.

## V2 delivered (2026-09-17, deployed, live-verified) — two-layer gather + the description ruling

- **Sean's editorial ruling (prompt prose/2)**: descriptions are NOT summarization — liberties may be taken to flesh out the entity's character, relevance is editorial (e.g., person-level testimonies don't belong in a region description), the DM has final say. The prompt now separates factual substance (must trace to material, cited) from connective/characterizing prose (the model's), and instructs leaving out material that doesn't serve the description.
- **Base gather layer (always on)**: the composer's new Gathered relations panel builds from the entry's own canonical data — role seats (★ leadership), membership records, derived co-mentions — each row labeled with its backing.
- **Expansion gather layer (opt-in)**: "Include graph neighborhood" loads `GET /entities/{id}/graph-neighborhood` (DM-gated, dev-gated like the pilot; `EntityGraphNeighborhoodService` reads the v5 bundle): audited member_of/leader_of seats first — including a faction seed reading its own roster, plus one hop out through the entity's factions — then ranked co-mention partners, capped at 24 rows, every row carrying its backing ("audited membership record" / "receipted roster decision" / "derived co-mention association"). Bridge route + client method shipped with the backend from day one (V1.2's lesson).
- Material keys normalized (`claim:*` / `relation:*`); the draft's citation sync mirrors both layers into their selections.
- Validation: Core — neighborhood unit tests (location = co-mentions only, member sees sibling seats, faction reads its roster, unknown entity, disk-backed service) + full local suite 474; React 128/128 incl. two-layer gather → draft material shape (claims + both relation layers) and citation-mirroring. Live: Fleurite serves 24 ranked rows; Fleurite Exiles serve their audited roster (Jace's leadership seat with role title) then co-mentions.

## Remaining

- 0099 host (lore synopsis); suitability review of deepseek-v4-flash after real drafting use; Sean's Fleurite re-draft with relations selected = the live Route B acceptance.

## V2.1 (2026-09-17) — Sean's interface refinements on the gather surfaces

- **Relations panel on every page**: previously rendered only when the entry had base relations (roles/members/related), which made "Include graph neighborhood" appear and vanish with no discernible pattern. The Gathered relations panel now always renders; entries with no canonical relations show the empty note and the graph expansion remains reachable.
- **Checkbox, not a button**: "Include graph neighborhood" is a checkbox inside the relations panel. Unchecked = grey panel (`#efede6`, graph rows dimmed and inert); checked = definitive outline (`1.5px solid #82533a`, `#fffefa`) and the neighborhood loads pre-selected. Unchecking after load greys the rows and excludes them from draft material without discarding selections.
- **Consistent composer rhythm**: `.description-composer .character-content` is now a uniform 14px-gap grid with child margins neutralized — no more ad-hoc vertical spacing between the textarea, draft row, panels, and actions.
- **AI-action wand**: every button that triggers a model call leads with the wand icon — Draft from selected, Extract/Re-extract this candidate, Extract all/Extract pending candidates, Retry failed extraction. Documented as the glossary entry "AI action (✨ wand)" (Help), a live Conventions row, and the wand rule in docs/architecture/ui-conventions.md.
- Validation: React 128/128 (toggle interaction, panel states, wand assertion); deployed as app version 225 and verified in the windmill app store.

## V2.2 (2026-09-17) — prose/3 + timing; then CLOSED per Sean's close-and-split ruling

- **prose/3** (Sean's Route B test findings): the prose must never use system meta-language ("records", "material", "the archive", "the library" — write about the world, not the tool), and descriptions must match what the subject IS (a place is characterized by look/people/power/shaping events, not the biographies of everyone who passed through; testimony only where it reveals the place).
- **Timing logged**: draft duration measured (performance.now), shown in the composer message ("machine-drafted, model, 12.4s · N tokens"), the support note, and the success/error toasts — the bus logs both to the persisted Log.

## Closing (2026-09-17)

Baseline complete and accepted by Sean ("the baseline of the ticket is close if not complete"): shared writer contract (prose/1→3), positional-citation validation with no partial output, DM-gated non-mutating endpoint, per-purpose model profiles with the flash model live, two-layer gather (Core relations + graph neighborhood), wand-marked AI actions, editorial-ruling prompt (description-not-summarization). Sean's real-use findings that belong to the follow-ups: prompt authoring (editable/configurable prompts, quality iteration — his Fleurite Route B draft still over-included testimony and meta-language before prose/3) → **TKT-0126**; blocking generation (single windmill worker queues page loads behind draft jobs; composer-held awaits lose drafts on navigation) → **TKT-0127**.
