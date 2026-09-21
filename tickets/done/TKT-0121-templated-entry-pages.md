---
id: TKT-0121
title: Templated entry pages — derived presentation over canon, claims under the hood
status: done
priority: P1
milestone: shared-campaign-knowledge
depends_on: [TKT-0111]
created: 2026-09-15
updated: 2026-09-18
---

# TKT-0121: Templated entry pages — derived presentation over canon, claims under the hood

## Context (Sean, 2026-09-15)

"I want neat well formatted blocks of data on the Library pages, not a list of arbitrarily ordered facts. Templates should manage the look of the page. The claims and known facts and sources and other structural data should be under the hood... maybe it's right that the formatted elements aren't canonical and they are all derived from canon data." Background and Dossier are the aesthetic proof: authored/structured blocks that belong on a page. Claim cards are the counterexample — underscoring data presented as an arbitrarily ordered list.

## The architecture (three layers, agreed)

1. **Canon, under the hood**: claims, truth states, authorities, provenance, sources, supersessions. Never the default surface.
2. **Authored documents**: DM-typed prose as evidence-class canon input (descriptions per TKT-0111's corrected ruling; session notes; brainstorm thoughts). The only place display and canon meet — written because they read well, filed because the DM wrote them.
3. **Templated presentation, fully derived**: per-kind templates assemble pages from structured canon (status, location, roles, aliases as formatted blocks) and authored prose (Background, Description, Operations as reading blocks). Derived display cannot contradict canon; look-and-feel becomes a pure presentation question.

## The system-wide under-the-hood pattern (named here, applies everywhere)

Per ADR-0015 and the UI conventions: ONE affordance, everywhere — the Records control. Standard icon in the standard `entry-page-actions` slot, label "Records", opening the audit view (claims with states/authorities, provenance passages, supersession history, sources). 0121 implements it for entry pages; any future surface (Brainstorm evidence, Log, graph view) exposes the same control the same way. The glossary's "Records (under the hood)" entry teaches it in DM language.

## Scope

- **Per-kind templates** as the page managers: PC/NPC (Background, Status, Dossier), Faction (Description, Operations, Members, Roles), Location (Description, hierarchy), Worldbuilding (Description/Lore), Item/Event. Blocks render structured canon formatted; prose blocks render authored documents.
- **Claims under the hood**: the canonical claim sections become a per-entry records view — one deliberate click (audit/provenance drill-down: claims, supersession history, sources). Not buried: it is the verify surface for 0097 repair and retcon checks. Search/retrieval unchanged (claims-based, invisible).
- **Description block consumption**: authored description documents (TKT-0111) render as the template's prose block; the "no page" flag becomes "no authored page."
- **Known-facts curation**: structured facts surface as fields/rows in blocks, not assertion cards; prose-like established claims can flow into reading blocks via the template's selection rules (deterministic, labeled).

## Acceptance

- Library entry pages for every kind render as templated blocks; no raw claim card list on any default page.
- The records drill-down is reachable in one click from every entry and shows the full audit view (claims, states, authorities, provenance, history).
- Templates are data-driven and per-kind; adding a block is a template change, never a canon change.
- React tests cover each kind's template and the drill-down reachability.

## Out of scope

- Drag-and-drop block arrangement or per-entity custom layouts (templates are per-kind, system-owned).
- Changes to claim/canon machinery — this ticket moves display only.

## Layer 1 delivered (2026-09-15, deployed) — claims under the hood

Every entry view (structured + character) now renders claim sections, provenance, and sources inside the collapsed Records hood — the consistent ADR-0015 affordance; no claim card list in any default page body. Remaining for full 0121: per-kind template refinement beyond the current hero/sections rendering (structured field blocks per kind), Records hood on remaining surfaces (session notes, encounters), and the "no authored page" flag rename when 0111's stale-flag work lands.

## Refinement delivered (2026-09-16, deployed)

- **Records hood everywhere**: session notes and encounters now carry the same collapsed Records affordance as structured and character views — no claim card list renders in any default page body across the whole app.
- **Structured faction roster block**: faction pages render Members from roster DATA in the template (name + role chip, ★ leadership, legend line) rather than markdown bullets from the synthesized doc — so authored description documents keep the structured roster automatically. Derived co-mentions render as an "Appears with" block with the honest not-a-roster note. synthesizedEntryDocument no longer generates Members/Appears-with markdown.
- React 119 (structured-roster test: names, role chip, ★, legend, hood present). Live-verified on the Inquisitors: "Members · Eustice Inquisitor · Romulus Grand Inquisitor ★ · ★ unique leadership seat".
- Remaining minor: per-kind hero field refinements beyond current (location hierarchy display etc.), flag rename when 0111 stale-flag lands.

## Remaining scope (2026-09-18 — this ticket is the dedicated template/dossier styles home; TKT-0128 stays floating-trays only)

1. **Known-facts curation into template blocks** — the ticket's core undelivered scope: structured established claims surface as curated fields/rows inside per-kind blocks (not assertion paragraphs), with deterministic template selection rules and the "derived" label; the Records hood remains the full audit view.
2. **Per-kind dossier styling pass** — Background/Dossier are the aesthetic proof; bring every kind's template to that standard (block spacing, field rows, reading blocks). Includes location hero refinements (hierarchy display, e.g. clickable parent navigation).
3. **"No authored page" flag rename** — the unpaged flag's tooltip/copy reframed per ADR-0015 (an entry can be paged by imported evidence yet have no authored page; 0111's stale/banner language applies).

Delivered alongside (recorded in TKT-0111, no longer this ticket's work): authored description prose rendering as the entry's page; authored pages winning the page match over same-name imports.

## Design rulings (Sean, 2026-09-19 — refining the dossier look)

1. **Known facts = Dossier cards, DM-curated**: established claims render as cards styled like the NPC dossier. Each claim row in the Records hood carries a **Promote to Dossier** icon (top right); each Dossier card on the page carries a **Demote from Dossier** icon (top right). Promotion is a per-claim DM decision — persisted and receipted in Core (audited, like every other standing decision), never a template heuristic.
2. **Composition order: structure first** — dossier feel, matching how NPC pages read today (hero → structured blocks → prose → Records hood).
3. **Location hierarchy = breadcrumb trail** under the name (Illisan › Fleurite, clickable upward); the contains-list stays a body block.
4. **Cards everywhere** — every block a bordered card with a mono kicker title, the identity-page look.

## Dossier curation delivered (2026-09-19, deployed, live-verified) — ruling 1 + 3

- **Core**: receipted dossier decisions (migration 0062; `DossierService` + `PostgresDossierRepository`) — promote/demote per claim, latest decision wins, entity-scoped; `GET /entities/{id}/dossier`, `POST .../dossier/{claim}/promote|demote` (DM-gated). The entry's dossier = promoted claims ∩ current claims (superseded claims drop out until a successor is promoted).
- **UI**: Dossier cards on structured entry pages — promoted claims render as NPC-dossier-styled cards (kicker "Dossier", grid, demote icon top-right, state + "promoted by DM decision" note). Every claim row in the Records hood carries a **Promote to Dossier** icon (new RecordIcon kind "dossier"); promoted rows show an "On page" tag instead. Promote/demote toasts; decisions receipted in Core.
- **Location breadcrumb** (ruling 3): `Illisan › Fleurite` trail under the hero name when a parent location is known — parent clickable via exact-name entry navigation (guard-wrapped).
- Validation: Core dossier tests (latest-wins, entity scoping, API DM-only round-trip) + docker 3/3 (migration 0062, durability); React 132/132 incl. promote → card → On page tag → demote round trip and the breadcrumb. Live: dossier endpoint serves Fleurite post-deploy.

### Remaining (this ticket)

- Ruling 2 (structure-first composition) + ruling 4 (cards everywhere): convert remaining entry-page sections to the card language and confirm order across kinds — styling pass continues.
- Promote icons in the character-sheet Records hoods (PC/NPC pages use CharacterDocumentView's hood; wired for structured kinds today).
- "No authored page" flag rename (tooltip copy).

### Formatting follow-up (2026-09-19, per Sean)

Dossier facts now match the NPC dossier's exact section formatting (hairline `#e3ddd2` separation, .88rem `#574b40` heading, .84rem fact lines — not boxed cards), and the description/background prose renders ABOVE the Dossier (hero → prose → Dossier → sections → roster → Records). Demote icon stays top-right per fact.

### Formatting parity, verified (2026-09-19)

First matching attempt was edge-flush inside the page (no block padding) and forced a 600 heading weight — the visible mismatch Sean reported. Fixed: the Dossier block now carries the page's block rhythm (20px/32px padding, block hairline) with facts separated by the NPC dossier's exact `#e3ddd2` hairline, and the heading mirrors `.npc-dossier-body h3` verbatim (default weight, .88rem, #574b40). Added `dossierFormatting.test.tsx`: jsdom applies the REAL index.css to both surfaces and asserts computed font-size/weight/line-height/color and hairline width/color equality — the parity is test-enforced, not eyeballed.

### Cards like the NPC dossier (2026-09-19, final form)

"Closer, but still not cards like npc" — the NPC dossier's cards are its identity cells (`.npc-dossier-identity div`): bordered, tinted, boxed dt/dd units. Dossier facts now render as exactly those cells — an auto-fill grid of `.dossier-card`s (border #dfd7ca, radius 4px, #faf7f0 tint, .65rem uppercase label + .78rem value), each labeled with its truth state, demote icon top-right. The parity test now asserts card chrome (border-color/radius/background/padding) and label typography against `.npc-dossier-identity` cells under the real stylesheet.

### Dossier cards = the established character-dossier style (2026-09-19, final)

"Look at Aris Placidia" — the established style is the NPC page's Character dossier block: `.character-content.character-dossier`, a two-column grid of padded serif cards (16px padding, #ded8ca border, #fbfaf5 fill, Libre Caslon h3 + entry-text body). The entry Dossier now REREUSES those classes verbatim (h2 "Dossier", grid of fact cards, h3 = truth state, EntryText body, demote icon absolute top-right); the only additive CSS is the icon's positioning. Custom dossier CSS deleted. Parity test asserts card chrome + heading typography against the Aris-style block under the real stylesheet.

### Sheet-hood parity + flag rename (2026-09-19, "continue")

- **Character pages get the full Dossier**: PC/NPC Records hoods carry the same Promote icons / On-page tags, and promoted facts render as the established character-dossier cards directly after Background (both sheet-backed and profile-backed characters). The Dossier is now a cross-kind surface: structured entries and characters curate identically, receipts in Core.
- **Flag rename**: the tree flag tooltip now reads "No authored page yet — this entry is displayed from its records. Write a description to give it an authored page." (ADR-0015 language).
- **Vocabulary**: glossary gains "Dossier" (Records and truth) — DM-curated fact cards, promote/demote, editorial never automatic.
- React 134/134 (character-page promote → established-style card). Remaining on this ticket: the broad cards-everywhere/structure-first sweep across remaining sections — best done with Sean's eyes on real pages.

### Sean's consistency pass (2026-09-19, deployed)

- **Records visibility settings** (Settings → Records visibility): "Show sources & provenance" and "Show earlier versions", both OFF by default — provenance drawers/details, per-claim provenance, source drawers, and Earlier-versions history render only when enabled (the referenced files aren't accessible in-app; the audit view is still one toggle away).
- **Bottom-strip provenance**: provenance details and "Read full canonical assertion" are now no-margin strips that expand the bottom edge of their parent card (edge-to-edge, hairline + tint, rounded to the card).
- **Established card fixes**: the unexplained 7rem right padding is gone (icons get a tight 2.9rem zone — no more text/icon intersection).
- **Records hood summary** now aligns with the page gutter (28px).
- **Dossier cards**: the per-card "Established" state title removed — cards are the facts.
- **Authored-page status bar removed**: the neutral "Authored page · N referenced records" bar is gone; revision moved into the header action slot (edit icon, "Revise description for X"). The STALE ALERT (superseded references) still renders with its Revise action.
- **Header gap** between the type label and its meta span; **hero type-kicker removed** (the bold header already says the type an inch above); **breadcrumb** left-aligned with tight top margin.
- **Breadcrumb = the full ancestor chain** (Myrin › Illisan › Fleurite › Fleurite Castle): parent locations walk upward through entity profiles (memoized per entry, 6-hop cap, cycle-safe), every ancestor clickable, current entry last.
- **"Operations"** on faction pages renamed to "Purpose".
- Template enumerations (status/location_type values, parent-as-reference, template editor) ticketed as **TKT-0129** rather than built here.
- React 134/134 (provenance-asserting tests now enable visibility in-test; authored-page test asserts the header Revise action).

### Follow-up fixes (2026-09-19, Sean's second pass)

- **Revise icon**: solid page (new RecordIcon kind "page") — dashed page stays exclusive to "no authored page".
- **Faction phantom section REMOVED**: not renamed — the synthesized faction document emits no section heading at all (nothing can populate it; hero + roster + Dossier + Records are the faction page).
- **Established cards, overlap actually fixed**: the root cause was the action ROW (3–4 icons ≈ 7rem wide) overflowing any reserved padding. Actions now sit in flow, top-right on their own line (flex column card) — text can never intersect regardless of icon count; provenance/read-full strips stretch the card's full width below.
- **Dossier fact cards** reserve the single-icon column (2.4rem) so text never underlaps.

### Third pass (2026-09-19, "get rid of the ON PAGE text, then continue")

- Promoted indicator in Records hoods is icon-only (the dossier mark; tooltip carries the meaning).
- **Cards everywhere, continued**: the doc `##` sections on structured entries now render as character-dossier cards (the approved style) in the established two-column grid; level-2 sections span full width. Authored prose stays the open reading band above them — completing rulings 2+4 for structured entries.

## Closing (2026-09-19, Sean: "if nothing else needs to be done with 121 i think we can close it")

Accepted against the four criteria:

1. **Templated blocks, no raw claim list** — every kind renders structured cards (character-dossier style for sections and Dossier facts; hero with breadcrumb, aliases, life status, roles; faction roster from data; authored prose as the reading band). No claim card list renders on any default page body.
2. **Records in one click** — the Records hood is on every surface (structured, character, session, encounter), carrying claims with states/authorities, provenance (settings-gated), supersession history (settings-gated), and sources (settings-gated).
3. **Data-driven, per-kind** — templates render from entity profiles, roster data, vocabulary selects, and authored documents; adding a block is a presentation change (0129's vocabularies carry the values). Never a canon change.
4. **React coverage** — 135/135 across structured templates, character dossiers, faction rosters, the Dossier promote/demote round trip on both structured and character pages, breadcrumb rendering, formatting parity (test-enforced against the real stylesheet), and the Records-hood affordances.

Delivered across the ticket's life: layer 1 (claims under the hood everywhere), the Dossier (DM-curated, receipted, the Aris Placidia card style), full-ancestor breadcrumbs, records-visibility settings, provenance bottom strips, card action-row overlap fixes, the authored-page display rules, vocabulary-driven template fields (0129), and the encounter/session pages keeping their own established idioms (stage flow, session note view) — reviewed with Sean's eyes in use; they are correct as-is.

### Post-close ruling (Sean, 2026-09-19)

"Both Brainstorm and Encounter are in pretty good shape, reworking their style would be wrong, they have a flow purpose and they look right for that" — the encounter stage flow and the brainstorm workspace keep their own idioms permanently; the cards-everywhere language applies to reference/entry pages, not to flow surfaces. No follow-up styling work is intended for either.
