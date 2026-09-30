---
id: TKT-0099
title: Lore creation queue with evidence gathering and optional synopsis
status: in-progress
priority: P2
milestone: trustworthy-librarian
depends_on: []  # 0040 retired (superseded by ADR-0018); 0094 parked with the graph track — Lore shipped without either
created: 2026-09-09
updated: 2026-09-28
---

# TKT-0099: Lore creation queue with evidence gathering and optional synopsis

## Outcome

Capture missing campaign entries without interrupting writing. Later, load a queued item in Lore creation, gather relevant library evidence, and review a draft before creating or linking an entry. Deferred at the user's request; this ticket does not authorize implementation or canonical changes.

## Context

An unmatched mention such as Tsunadis can refer to a place already discussed in evidence but lacking its own Location entry. A missing identity is not missing knowledge, and typing a mention must not create canon automatically.

Coordinate with TKT-0040 (Lore creation), TKT-0093 (optional identity links), TKT-0094 (shared retrieval), and TKT-0095 (workflow integration). Reuse shared retrieval rather than building a separate scraper or graph.

## Scope

- Add **Queue for Lore** to the Library **+** menu, allowing a name and optional context to be saved without creating an entity.
- Provide a discoverable **Lore queue** entry point outside the + menu, with a compact pending count, and a queue picker on the Lore creation page. Prefer a Library navigation item or small queue button; settle its exact placement during UI work.
- Offer **Queue for Lore** for unmatched @mentions while retaining **Keep as text**. Preserve the current draft and caret; no forced navigation.
- Persist queued name, originating workspace/document reference, exact surrounding context, timestamps, and optional user notes. Repeated requests must not accidentally duplicate items. Suggest combining matching names, but do not merge ambiguous identities solely by spelling.
- Lifecycle: Queued, Drafting, Resolved; allow Dismiss. Retain context and resolution history. Resume drafts after refresh.
- Load a queued item into Lore creation with its context intact.
- Provide **Gather library evidence** using content search, aliases, and graph relationships. Return bounded, expandable source passages with citations. Keep plans, observed events, and unresolved conflicts distinguishable; graph associations are discovery aids, not proof.
- Allow selection of evidence and an optional, explicit **Draft synopsis** action. AI drafts only from selected evidence, cites its support, preserves uncertainty, and surfaces unanswered questions. Never turn plans into outcomes or assumptions into facts.
- Review/edit the proposed name, type, prose, and evidence before creating through Campaign Core. Alternatively resolve by linking to an existing entry. Mark resolved only after successful creation/linking; failures remain resumable.
- Offer explicit linking of pending mentions after resolution without rewriting original evidence or silently replacing prose.

## Out of scope

- Automatic canonical creation from mentions, queue actions, retrieval, or AI synopsis.
- Broad automatic entity extraction or mandatory subject-predicate-object enrichment.
- External web scraping; this gathers existing campaign-library evidence.
- Creating Tsunadis as part of ticket drafting.

## Acceptance criteria

- [ ] Library + can queue an item; the queue is also accessible without opening that menu.
- [ ] An unmatched mention can be queued without losing the active draft; keeping it as text remains possible.
- [ ] Queue items and drafts survive refresh, with origin/context retained and duplicate submissions handled safely.
- [ ] Lore creation can load, dismiss, resume, and resolve a queued item.
- [ ] Evidence gathering finds relevant passages even when no corresponding entity exists; passages are bounded and expandable.
- [ ] Synopsis generation is opt-in, editable, cited, and non-canonical. Unsupported details and contradictory evidence are not silently reconciled.
- [ ] Creating or linking requires an explicit action through existing Core boundaries; failure cannot falsely resolve the queue item.
- [ ] Suggested mention links require explicit acceptance and preserve original text/provenance.
- [ ] Tests cover lifecycle, duplicate requests, missing identities, conflicting evidence, provider failure, and successful resolution; UI is visually checked at normal and narrow widths.

## Validation plan

Use a sanitized Tsunadis-like example: several source passages mention a place and castle without a location identity. Verify that the workflow gathers those passages, asks about ambiguous identity rather than guessing, and creates nothing until reviewed. Include an existing-identity resolution and refresh/retry tests.

## Implementation sequence

1. Durable queue, Library entry points, and Lore-page loading.
2. Shared evidence gathering and explicit create/link resolution.
3. Optional cited AI synopsis, with visible progress, failure recovery, and existing model settings.

## Documentation

Document the distinction between queued names, non-canonical drafts, and resolved canonical entries, plus unmatched-mention behavior and evidence-selection rules.

## V1 delivered (2026-09-19, deployed) — the core Lore creation flow

- **Lore queue** (browser-local `localStorage`, `loreQueue.ts`): queue a name + optional context; idempotent per name (same-name re-queues append context, no duplicates); lifecycle queued → resolved / dismissed with history. Reset-for-test in App afterEach.
- **Lore page** (nav: Lore): Queue a name form → Pending list (Work this / Dismiss) → Creation workspace:
  - **Evidence gathering**: searches all source documents' claims for the queued name; matching claims are selectable checkboxes. Existing entity matches (via `searchEntities`) shown as link targets.
  - **AI synopsis**: "Draft synopsis" (wand-marked) queues a background prose-draft job from the selected evidence — lands in the Drafts tray.
  - **Creation**: write prose → "Create {name} as {kind}" → `createIdentityEntity` + `writeEntityDescription` through existing Core boundaries. Nothing becomes canon without the explicit button.
  - **Link resolution**: pick an existing entity → "Link to {name}" resolves the queue item without creating a duplicate.
- **Library + menu** gains "Queue for Lore" alongside the session options.
- Evidence gathering is currently document-by-document (the search path fetches each source to inspect claims — correct but potentially slow on large libraries; a Core-side search endpoint is a natural optimization when the volume justifies it).
- React 137/137 incl. the full queue → gather → create round trip with a Tsunadis-like name.

### Remaining for full 0099

- Unmatched @mention queueing in the session-note/brainstorm composers (Queue for Lore alongside Keep as text).
- Refresh persistence testing (the queue IS localStorage, but the creation workspace draft should survive refresh).
- Conflict surfacing inside creation review (was "the 0040 conflict path"; 0040 is retired — the concern now lands with TKT-0142's unified claim card).

### Post-V1 refinement (2026-09-19, Sean's real-use: Fleurite Treasury)

Sean hit the exact gap the ticket predicted: Lore's exact-name scan found nothing for "Fleurite Treasury," so he went to Ask to search "treasure" — but Ask's tray was too narrow to read evidence and there was no bridge back to Lore.

- **Lore gets its own relevance search**: a search box in the creation workspace that calls the retrieval endpoint (meaning-ranked, not exact-text). Results merge into the evidence checklist, auto-selected. Search "treasure" while creating "Fleurite Treasury" and the treasury-related passages appear. Enter key submits.
- **Ask tray widened** to 680px / 72vw — evidence cards with citations are readable (other tray panels keep their 430px width; only the ask tray is wider because its content is wider).
- React 137/137.

### Evidence workspace refinement (2026-09-19, Sean's workflow feedback)

- **Full-width page**: Lore uses the wide-page layout (same max-width as Migration/Tools).
- **Manual gather**: picking a queued item no longer auto-runs the exact-name scan — a "Gather by name" button triggers it. The search box and button sit in one aligned row.
- **Evidence items**: expandable (click to toggle clamped/full text), source citation below each.
- **Link Evidence + Consider checkboxes**: Link includes the claim as a referenced record (feeds the description filing + AI synopsis). Consider keeps the claim in a separate "Considered" section that survives searches. Checking Link auto-checks Consider; unchecking Consider does not uncheck Link.
- **Search semantics**: results arrive UNCHECKED; un-Considered prior results are cleared on each search (Considered items survive). The graph neighborhood is consulted for relational evidence tied to entities matching the query.
- React 137/137.

### Evidence persistence + search clearing (2026-09-19, Sean's feedback)

- **Linked/Considered survive refresh**: the lore queue stores each item's saved evidence workspace (claims, linked IDs, considered IDs) in localStorage. Picking a queued item restores its full evidence state — linked and considered items are exactly where you left them. Un-checked results are ephemeral (not saved).
- **Search clears un-Considered from the main list**: when a new search runs, only Considered (which includes all Linked) prior results survive — they stay in the Considered section; the main results list shows only the fresh, unchecked batch.
- React 137/137.

### Graph returns RECORDS, not relationship summaries (2026-09-19)

Sean: "The point is for the graph to retrieve Records that are related, not whatever that is." The graph's value in Lore creation is DISCOVERY — it identifies related entities whose CLAIMS are the evidence. The graph rows themselves (co-mention summaries, seat descriptions) are the PATH, not the payload.

Rewritten: after the retrieval search, the graph neighborhood identifies related entities (from both structural edges and co-mentions, entity names extracted from the row text). For each related entity (max 5), the library entry is fetched and its top 3 claims become evidence items, each labelled with the graph path ("via graph → Fleurite (location)"). No more "Frequently appears with" text as evidence — actual claims from actual related entities.

## Domain rulings from Lore creation use (2026-09-19 — Sean, pending design)

### The graph discovery path is noise
How an assertion was found (graph traversal, text search) is not relevant to the entity being created. The graph chip and "via graph →" notation should go from evidence items. The assertion is the thing being linked; the discovery path is ephemeral.

### The document/entity distinction is unclear
Sean: "I'm not particularly happy about the distinction between documents and entities. I'm not sure what purpose it serves other than being an artifact of migration." This is an open architectural concern — documents are evidence, entities are subjects, but the presentation conflates them.

### What IS clean: entities and their assertions
"The distinction between an entity and the claims it is built on does make sense. The assertions are about truth state management, they are underlying facts that entities can claim as being relevant to them."

### One owner per assertion
Each assertion has exactly one owning entity — the entity the assertion is directly about. When Lore creation assigns an assertion to a new entity, that's a re-attribution (ownership transfer), not a cross-reference.

### Consider vs Link — corrected semantics
- **Consider** (primary, first position): pulls the assertion into the drafting material. "I want this fact to inform my draft." Does NOT change ownership.
- **Link** (special, annotated as ownership action): declares that this entity is where this assertion belongs. This RE-ATTRIBUTES the assertion from its current owner to the new entity. Reserved for moving assertions, not just referencing them.
- Consider should be the primary/first checkbox; Link is the special, secondary action with clear annotation about what it does.

### What happens to the old owner
When an assertion is re-attributed to a new entity:
- The old owner loses the assertion (its subject changes)
- The old owner should be updated in some way — perhaps a reference/note that the assertion moved to the child entity
- This prevents silent information loss from the parent's perspective

### NO CHANGES YET — design first
These rulings need to be fleshed out into a concrete design (Core re-attribution operation, old-owner reference mechanism, UI annotation for Link) before implementation.

### Ruling refinements (2026-09-19, continued)

- **Graph tag in search results**: KEEP the dashed graph chip on evidence items in the Lore workspace (Sean wants to track the graph's usefulness). But when an assertion is LINKED (re-attributed to the new entity), the graph-discovery fact does NOT persist in the assertion's permanent record.
- **Dossier behavior on re-attribution** (Sean's vision): the old owner's Dossier keeps a tile titled "Treasure Room" (or the assertion's title) with a shortcut to the new entity (Fleurite Treasury) just below the title, plus its brief synopsis. The old owner doesn't lose the visual — it gains a pointer to where the assertion went.

## Assertion re-attribution delivered (2026-09-19, deployed) — Link = ownership

Implements Sean's ruling: Link is a declaration that this assertion belongs to the new entity.

- **Core** (migration 0064 + `claim_reattribution.py`): `POST /claims/{id}/reattribute` — changes the claim's `subject_entity_id` from old owner to new, records in `claim_reattributions` audit table (receipted, reason preserved). `GET /entities/{id}/moved-assertions` returns assertions that moved away with the new owner's name. Provenance is untouched (same source, same evidence, same text).
- **Lore creation**: after creating the entity + filing the description, each linked claim is re-attributed to the new entity. The toast reports how many moved. Non-UUID claims (graph items) are skipped.
- **Old owner's Dossier**: entity pages now show a "Moved to new entries" section with dashed tiles — each tile has the assertion's title, a brief synopsis, and a clickable "→ New Entity Name" shortcut. The old owner keeps its visual context while pointing to where the assertion went.
- **Consider first, Link second**: the evidence checkboxes are now ordered Consider (primary drafting tool) → Link (ownership action). Link carries a subtle "← moves to this entity" annotation so it's clearly not just a reference.
- Tests: Core 4 local + docker 5/5 (migration 0064, durable moves, moved-from listing, API DM-only); React 137/137.

### Margins + AI direction field (2026-09-19, deployed)

- **Margin fixes**: Draft synopsis row gets 14px above/below; step-actions (Back to Queue / Create) gets 18px top / 10px bottom; search row spacing tightened.
- **AI direction field**: a "AI direction (optional — shapes the draft's emphasis)" textarea between the search row and the evidence list. DM prose direction (e.g. "focus on the statue's significance and the secrecy around it") passes through `ProseDraftCommand.direction` → the prose harness includes it in the user prompt as "DM DIRECTION" between the SUBJECT and MATERIAL sections — shaping emphasis without loosening the evidence contract. Clears when switching queued items.
- Core: 8/8 prose tests pass (direction is optional; existing tests unaffected). React 137/137.

### Boundary compliance fix (2026-09-21, migration 0066)

- The re-attribution canonical write (UPDATE claims) ran inline in the postgres adapter, failing `test_boundaries::test_canonical_table_writes_exist_only_in_migrations`. Fixed: migration `0066_move_claim_subject_function.sql` owns `move_claim_subject(...)` (idempotent on the receipt, loud on a raced owner change, validates target existence and same-owner); the adapter now calls the function and surfaces P0001 as a readable error. Evidence: boundary test green; all 5 re-attribution tests pass in the docker harness (test-campaign-core-postgres.ps1).

### Evidence-context compliance fixes (2026-09-21, deployed)

Sean's rulings, all delivered:
- **Truth State on every listed claim** (both the gathered list and the Considered section): all Claims are canonically true, so listing one without its CTS state invites misreading a Considered reference as established fact. State chip now sits beside the authority chip.
- **Draft synopsis no longer requires a Link** — no Linked or Considered claims are required. With nothing checked, the queued name itself is the seed material ("{name} is a name queued for a new {kind} entry"), satisfying the prose harness's material minimum honestly.
- **Considered section order corrected** — Consider first, then Link, matching the gathered list (Consider is the primary drafting tool; Link is the ownership action).
- **Owner title + draft context** — every evidence item shows "About {owner}" when the owning record is known (retrieval evidence carries entity_id; graph evidence carries the entry name; gather-by-name items have no owner to show), and the prose draft material for Considered claims is prefixed `[about {owner}]` with the claim's state attached, so the model can never read a background reference as a fact of the entity being drafted.

Evidence: React 139/139 (new test covers state chip + owner title, zero-selection seed draft, Consider-before-Link order, and `[about owner]` material); deployed via test-stack.

### Workspace overhaul: Brainstorm-style layout + no-data-loss working file (2026-09-21, deployed)

- **Two-column workspace** modeled on the Brainstorm panel: main working file left (Entity Kind, existing matches, AI direction, Draft synopsis, Description, actions), evidence aside right (parchment panel, sticky header, search + Gather by name).
- **Results/Consider accordion with sticky bars**: one list open at a time; both bars always visible (sticky at 139px/180px below the panel header + search) so switching lists never requires scrolling. Live-verified via getComputedStyle.
- **Working file auto-save** (the workspace data-loss rule, recorded in ui-conventions #6): Entity Kind, AI Direction, and Description save with the evidence on every change and restore on re-entry — leaving the item, refreshing, or switching away and back loses nothing. React test covers the full round trip (direction + description + considered set).
- Evidence: React 139/139; deployed; live layout verification in-browser.

### REMAINING — backward ownership link (Sean's reminder, 2026-09-21)

Gather-by-name evidence shows no owner because document claims do not carry their subject entity back — "the claims don't own the entity and thus there's no backward record linking them together." The Source excerpt is the only hint. Fix = Core API: `getSourceDocument` canonical claims include subject_entity_id + canonical name; Lore evidence then titles every item (gather results included), and the AI draft material gains the same context it already has for retrieval/graph evidence. Sean asked to be reminded to deal with this — fold into the 0136 Lore slice or take standalone.

### Working item as an independent page (2026-09-21, deployed)

- "Work this" now opens the item as its own page: queue form/list stay behind a "← Back to Lore" control; the working page renders only the workspace (user ruling: independent page).
- The Evidence panel scrolls itself: the workspace matches viewport height (calc(100vh - 76px topbar - 40px chrome); live-verified 604px at 720px vh); BOTH columns scroll internally instead of the page.
- Results/Consider bars moved OUTSIDE the scroll area (flex-column panel: header + search + both bars fixed, one scroll container below) — with 95 live results the Consider bar stays reachable; verified both bars remain visible with the list scrolled deep. This replaced the earlier sticky-in-content approach, which pushed the Consider bar 15k px down on long result sets.
- React 139/139; deployed; live-verified (layout metrics + scroll behavior + bar switching).

### Backward ownership link + results grouped by entity (2026-09-21, deployed)

The backward-record gap is CLOSED for the document path:
- **Core**: `SourceDocumentClaim` (canonical + history) now carries `subject_entity_id` + `subject_entity_name` — both claim queries LEFT JOIN entities on `claims.subject_entity_id`. Evidence: `tests/test_source_document_owners_postgres.py` (owned claim returns the pair, owner-less claim returns nulls) green in the docker harness.
- **Lore gather-by-name** maps `subject_entity_name` into the evidence owner — name-scan results are titled and grouped like retrieval/graph evidence always were.
- **Results grouped by entity** (user ruling): the Results accordion groups claims under their owning record (mono heading + count, "Exile Camp · 8 claims"); owner-less claims fall into a trailing "No owning record" group; per-item owner chips in Results are replaced by the group heading (the Consider list keeps its per-item "About X" titles). Live-verified against the real campaign: a "Fleurite" search renders 30 owner groups.
- React 139/139 (grouping test added: two owners → two groups, Truth State chip still per-row).

### Gather preserves Considered; Consider grouped (2026-09-21, deployed)

- **Gather by name no longer dumps the Considered set**: it now merges exactly like search — Considered/Linked claims survive a re-gather, fresh name matches replace the unconsidered pool, deduped by underlying claim id (retrieval `record_id`s and `graph:`-prefixed ids collapse against document claim ids).
- **Consider is grouped by owning record** like Results (mono heading + count; owner-less → trailing "No owning record" group; per-item owner chips retired in favor of headings in both lists).
- React 139/139 with the gather-merge covered end-to-end (consider → re-gather → considered claim survives, gathered claim lands in Results under its owner).

### Evidence accordion: sliding branches (2026-09-21, deployed)

- The Results/Consider branches now form a true accordion (user spec): **one branch is always open — clicking the open bar leaves it open** (no collapse-to-none state).
- **Results open**: Consider's bar slides to the panel bottom and sticks; the Results list is the scroll area between the bars. **Consider open**: its bar slides to just under the Results bar; the Consider list scrolls to the panel bottom. The slide is a real flex-grow transition on the branch containers (fixed DOM order: Results bar → results scroll → Consider bar → consider scroll), so the Consider bar physically travels between its two parked positions.
- **Searching (or gathering) auto-opens Results** — the branch that receives new content becomes the visible one.
- Live-verified: Results-open parks Consider at 565px of the 602px panel with the 326px results scroll between; Consider-open slides its bar to 239px (just under Results at 202) with the Consider scroll filling below; aria-expanded tracks; round-trip back to Results restores. (Transition-freeze in the hidden automation tab required disabling the transition for end-state measurement — the animation itself is stylesheet-verified.)
- React 139/139 with accordion-semantics assertions (always-one-open, no-op reclick, search auto-open).

### Working page is exactly 100vh (2026-09-21, deployed)

- `.lore-working` now computes `height: calc(100vh - 76px)` (viewport minus topbar) as a grid with rows `auto minmax(0, 1fr)`: header row, then the workspace taking every remaining pixel. The workspace's own calc is gone — the grid row sizes it, so the header height can change without re-deriving offsets.
- Live-verified with a full evidence panel (95 search results): page `scrollHeight - clientHeight = 0` — the page never scrolls; only the workspace columns do. Mobile (≤900px) reverts to natural height.
