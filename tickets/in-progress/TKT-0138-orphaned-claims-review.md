---
id: TKT-0138
title: Orphaned claims review — a standing queue to assign owners to subject-less claims
status: in-progress
priority: P1
milestone: trustworthy-librarian
depends_on: [TKT-0099]
created: 2026-09-21
updated: 2026-09-28
---

# TKT-0138: Orphaned claims review — a standing queue to assign owners to subject-less claims

## Context

Grouping Lore evidence by owning record (2026-09-21) exposed a population of claims with no `subject_entity_id` — they land in the "No owning record" group. Sean's read on the live data: **many belong somewhere obvious** (an entity that already exists), and **some don't** — history/lore claims that may legitimately have no owner, or belong to records that don't exist yet. Before the grouping, this residue was invisible; the identity review (TKT-0106) closed 91% claim coverage and this queue addresses the remainder. Per the standing productize rule, this is a permanent in-app review feature, not a one-time backfill.

## Scope when taken up

- **Core list endpoint**: subject-less claims (`subject_entity_id IS NULL`, non-superseded), each with assertion text, state, authority, sources, and **suggested owners** — deterministic suggestions from the existing co-mention / alias / word-index machinery (the link-audit and entity-lookup tooling), ranked; no suggestion is authoritative.
- **The bridge to Lore is the primary migration path** (user ruling 2026-09-21): the review is a list of orphaned claims that can be **checked and migrated into the Lore creation queue**. Checked claims become a seeded Lore queue item — the DM names the record they belong to (defaulting to the top suggested owner's name when one exists); the claims ride along as pre-loaded evidence in that item's working file, Consider-checked and ready to Link. Lore then handles both resolutions it already owns: create the new entity and take the claims under it, or match an existing entity via the link-target flow and Link to it. The orphans find their owner through the same reviewed door everything else uses.
- **Initial attribution write** — LANDED early (migrations 0067+0068, harness-tested): `move_claim_subject` accepts a NULL old owner with nullable `old_entity_id` receipts, and the re-attribution service/API handle the initial case. Receipted, reason required, provenance untouched; the claim's text/state/evidence never change, only ownership. Lore's Link path uses this for orphans the same way it uses re-attribution for owned claims.
- **Direct assign-to-record** stays available for the obvious cases (owner exists, no Lore ceremony needed): a suggested owner or searched record as the initial-attribution target.
- **"No owner needed" disposition**: some claims are ambient history/lore with no owning record. A receipted per-claim disposition (reason required, audited like candidate dispositions) that removes the claim from the review without inventing an entity — "missing source files never authorize automatic canonical deletion," and neither does a missing owner.
- **Tools-panel review queue** (link-audit pattern): rows show the claim (Truth State + authority chips, expandable text, source excerpt) with its suggested owners; actions = **Migrate checked to Lore queue** (primary) / **Assign to record** / **No owner needed** (reason required); re-runnable, so future unowned claims reappear — a standing review, not a batch.
- Per-item dispositions only: inspecting one claim never decides another; migration carries exactly the checked claims.
- Optional later (out of scope unless ruled in): the AI Promotion Assistant suggesting owners on this queue (TKT-0137 seam 4 — suggest subjects).

## Sean's priority ruling (2026-09-28) — this is the front

"Dealing with data that exists but is unassigned and thus mostly invisible is much more relevant than an Entity that has no non-Attribute Claims. Writing prose for Entities is a baseline purpose of this app and thus has no end." Consequences recorded: the orphan queue outranks Q1 zero-claim completion (which is baseline ongoing usage, not a finite campaign — TKT-0140 closed on this ruling); today NO surface lists the orphans (the only `subject_entity_id IS NULL` query in the codebase is an internal duplicate check; audit Q3 reports pending; Step 1's document-exclusive slice reaches only a few dozen of them). Live population: **186 non-superseded ownerless claims** (206 at discovery on 09-21; ~20 consumed via Step 1 Assign Ownership).

## Already landed since the ticket was written

- **The initial-attribution write path is DONE** (was an open scope item): migrations 0067+0068 extended `move_claim_subject` to a NULL old owner with nullable `old_entity_id` receipts; the re-attribution service and API handle it; harness-tested. The queue builds on a working write.
- **Step 1 Assign Ownership** (0140) consumed the document-exclusive slice and validated the UX (checked rows → one button → receipted attribution → re-audit).
- **The Lore working item persists evidence through refresh** (ADR-0019), so seeded orphans ride safely.

## Fold-in: the audit's Q5 flip

While touching the qualified audit for Q3, flip **Q5 (`q5_attributes_minted`) from pending to computed** — minting landed (TKT-0143, migrations 0069/0070, live 36 bindings across 19 profiles) but the audit still reports "pending claim-backed minting (TKT-0143)". Same file, same pattern: Q5 = every attribute-bearing profile's fields have a minted claim behind them (or the profile predates minting and carries the unanchored-but-dated backfill marker). Q3 flips to computed with this ticket's dispositions ("no owner needed" receipts + clean ownership); Q5 is a mechanical join against `attribute_claim_bindings`.

## Open at ticket time — the obvious-home path (user ruling 2026-09-21: defer)

The Lore bridge is right for orphans with NO obvious home. Orphans WITH an obvious home need their own solution — maybe still Lore (workspace built up to accommodate seeded resolution against existing records), maybe the Library's built-in entry editor (the page that already owns the record, per ADR-0016 every-page-editable). The tension: two editing homes (Lore workspace vs Library entry editors) and where an obvious-home attribution belongs. Decide when this ticket is worked; do not pre-commit.

## Out of scope

- Auto-assignment or bulk approval — every attribution is an explicit DM decision.
- Creating entities directly from this queue — creation goes through Lore (that is the bridge); the queue itself links and queues, it doesn't author.
- Changing claim text, state, or evidence — ownership only.

## Validation evidence

### REFRAMED 2026-09-28 (Sean's rulings with ADR-0020): FINITE CLEANUP, not a standing review

Three rulings: (1) backward compatibility with the original source is ABANDONED (ADR-0020) — the current database is the only working database; no future import produces failed-migration states, so this ticket cleans up a CLOSED population with an end, and no standing surface is warranted beyond the cleanup; (2) ongoing capture resolves ownership AT PROMOTION through the pipeline — that requirement moved to TKT-0148 (P1: the session/encounter reviewer is the gap; Lore/Brainstorm/Description already bind); (3) the PERMANENT guard is the audit's Q3 flipped to computed — any future ownerless claim is a regression signal there, not a queue entry. The panel becomes the cleanup tool, then a drill-down for Q3 failures. Slice 2 = the two cleanup actions (direct assign with the evidenced-on-their-page lead suggestion; migrate-checked-to-Lore) plus the receipted "no owner needed"; Q3 flips when the population reaches zero. ROUTING FINAL (ADR-0021 accepted, mechanism ruled 2026-09-28): encounters ARE Entities (kind `encounter`; authored-or-referenced criterion) — the 67 encounter-doc orphans resolve by MINTING the encounter entities from their documents (reviewed batch) then assigning, ONE action per encounter document. The 36 timeline.md orphans route to the TIMELINE — a unique event Entity that CAN own its own document's date records (TKT-0042's enrichment: reference-first — dates elsewhere become mentions for timeline viewing, ownership untouched; the timeline slice mints the entity and takes its document's records). The 49 session-note orphans are unfinished COMMITS (ADR-0021: sessions assign ownership at commit) — the assign action completes them. Remaining lore/cosmology/handout orphans → direct assign or Lore-bridge (event/reference entities mint on demand via the queue). TWO ACTIONS COVER EVERYTHING: assign to an existing entity, or Lore-create the missing one — no parallel ownership machinery. The Zander diagnosis that shaped this: the August import-review promotions carried `subject_entity_id: null` silently (218 of 461 claims) — promote-with-empty-subject was the orphan factory; 0148's guardrail ends it.

### Slice 2 delivered 2026-09-30 (deployed) — THE DRAIN ACTIONS

All three disposition paths from the 09-21 rulings, live on the orphan panel (0148's guardrail + disposition table landed the day before; this slice completes them for EXISTING claims):

- **Assign to record**: every suggestion chip is now a one-click action ("→ Raven King (co-mention)") — receipted initial attribution through the existing re-attribution write path (NULL-old-owner handled since 0067/0068); the row leaves the list on the re-gather. A panel-level search covers the checked rows for arbitrary records ("Assign checked to…", the Step-1 batch pattern).
- **"No owner needed"**: per-row, reason required — `POST /claims/{id}/owner-disposition` (DM-only) → migration **0074**'s `dispose_claim_owner` (the only canonical write path for disposing an existing claim; idempotent — a pre-existing disposition returns `already_disposed`; refuses owned or superseded claims). The orphan list excludes disposed claims (audit-side: these are resolved-by-receipt, not pending — Q3's computed flip must count dispositions as clean).
- **The Lore bridge**: check rows → "Migrate checked to Lore" → name the record (defaulted to the lead suggestion) → a Lore queue item is seeded with the claims as pre-loaded Considered evidence, ready to Link at creation or match. Seeded rows leave the session's list; they leave the DB's orphan set when Lore assigns.
- **Evidence**: React 87/87 (new end-to-end test: assign-by-suggestion with the receipted payload → row departs; no-owner reason gate + filing; Lore seeding asserts the queue item's consideredClaimIds); backend full suite green; deployed; 0074 in the ledger; endpoint + bundle verified live (no canonical writes performed — Sean drives the real drain).

**RULING IMPLEMENTED (same day, deployed)**: the orphan service resolves every claim's evidence document → its entity, DOCUMENT-FIRST (the inverted resolution: an entity's lore doc attaches even when a locations/ sheet outscores it as that entity's "best" page — `lore/goodmans-city.md` → Goodman's City alongside `locations/.../goodmans-city.md`; exact stem/name match first, then distinctive-token subset, longest name wins; a stem that IS another entity's name never borrows; session notes never match). The API rows carry `document_owner_id/name`; the panel renders a lead "(their page)" chip per backed row and a one-click batch **"Assign page-backed (N)"** — receipted per-claim attributions, "evidenced on their page (DM-confirmed batch)". LIVE at deploy: **6 of 181 backed** (Goodman's City 4 via the lore doc, Zander Thromius 2) — the thin edge today because the mass awaits its entities: the encounter slice mints encounter entities (67 attach), the Timeline entity takes timeline.md's 36 (the resolver attaches it automatically the moment the entity exists — exact stem match), and the remainder (sessions 49, cosmology 6, handouts 11, original-white-cloaks 4, hidden-truths 1) ride the suggestion/Lore-bridge/no-owner paths. Backend 5/5 orphan tests (added: the document-owner default + doc-first lore attachment); React 88/88 (added: the batch drain test — page-backed assigns in one click, the session claim stays for judgment).

**RULING (Sean, 2026-09-30): the default disposition is the entity the claim's evidence document is already attached to — "this includes encounters and lore."** Orphans evidenced on a record's document (npc/pc/location sheets, authored entity pages, lore docs attached via the matcher's lore-suffix rule) default to that record; encounter-doc claims default to the ENCOUNTER entity (the encounter slice mints them); timeline.md's claims default to the TIMELINE entity (0042). Session notes are excluded (ADR-0021 — sessions never own); their claims keep the suggestion/Lore/judgment paths. The drain becomes largely mechanical: page-backed claims assign in batch.

### Encounter slice delivered 2026-10-01 (deployed) — mint the table events, take their claims

Kind ruling first (Sean, 2026-10-01): **add `encounter` as its own kind** — distinct from the registry's unused `event` seed, which stays for lore events (the Timeline). Landed: domain enum + guidance, migration **0075** (kind_definitions + kind_versions rows — gotcha: exclusions/examples/counterexamples are ARRAY columns, plain strings malformed), UI kind list, glossary entry "Encounter (Entity)".

- **Backend**: the orphan result carries **encounter_groups** — the unbacked encounter-rooted orphans grouped by encounter (the directory for multi-doc dungeons, the file stem otherwise; one entity per encounter; names derived, editable later; session claims never group). `POST /campaign/encounter-entities` mints the entity through the identity queue's receipted idempotent create (kind `encounter`) and assigns the group's claims via receipted initial attribution in the same action — the paperwork-free shape.
- **UI**: an "Encounters (ADR-0021)" section on the orphan panel — each group with its claim/doc counts and a **"Mint & assign"** button.
- **LIVE**: 5 groups covering all **67 encounter orphans** — Ishirala 31 (5 docs), Fleurite Castle Dungeon 11, Return To The Monastery 10, The Descent 9, Exile Camp Meeting 6. No mints performed — Sean clicks.
- **Evidence**: backend 6/6 orphan tests (grouping: multi-doc directories, single-file stems, sessions excluded); taxonomy tests updated for the new kind; React 89/89 (the mint action's payload); full suites green; deployed; kind row + groups + bundle verified live.

### Collision fix (2026-10-01, deployed, from Sean's live mint run)

Sean minted four groups live (The Descent, Exile Camp Meeting, Fleurite Castle Dungeon, Return To The Monastery — 36 claims assigned, 181 → 145 orphans); **Ishirala errored**: "that name already resolves to an identity" — the derived group name collided with the existing entity **Ishi'ra'la** (the identity queue's name-resolution guard refused the create; nothing half-applied — claims untouched). Fix: encounter-group names are now **editable proposals** — an input per group (prefilled with the derived name), with server-side collision detection (apostrophe/case-insensitive, `name_available` on each group) surfacing the clash BEFORE the click ("that name already resolves to an identity — edit it before minting; the encounter is its own record, distinct from the entity it's named for"). The mint uses the edited value. Live after fix: 145 orphans; Ishirala (31 claims) flagged, awaiting the edited name + one click. React 90/90 (collision flag + edited-name payload), backend 7/7 (apostrophe-insensitive flag).

### ADR-0022 from the live run (2026-10-02, deployed)

Sean's report after minting **Ishirala Tower** (31 claims assigned — the encounter mass is DONE: all five groups minted, 67/67 claims home): "it didn't appear in the Library until a refresh." Ruled as **ADR-0022 (accepted): the Library reflects every change — no refresh required** — every canonical mutation refreshes the library index in the same interaction; new surfaces inherit it by default (standing-rule status like ADR-0019). Fix shipped with the ruling: the shared `refreshLibrary` callback threads through the Phase 2 page into both mutating panels — the orphan review's assign/batch/dispose/mint actions and Step 1's Assign Ownership all refresh on success (Lore creation and session commits already complied). React 90/90 (the mint test now asserts the library re-read). Name note: the entity is "Ishirala Tower" (directory-derived prefill, no apostrophes) — renamable on its profile if the real spelling is wanted.

### Library unification (2026-10-02, deployed, from Sean's live report)

"The Library has 2 Encounter blocks, which is wrong." Diagnosis: the entries tree rendered BOTH the entity-kind group (**"Encounter"**, singular — the five minted entities) AND the legacy source-backed document family (**"Encounters"**, plural — the nine documents); near-identical labels, split by representation. All 9 documents were already entity-covered (no minting needed — verified). Fixes:

- **One block**: encounter documents claimed by encounter entities no longer render the document family — `encounterDocumentClaimed` (group tokens ⊆ entity name tokens, apostrophe-insensitive: the Ishirala/ docs claim to "Ishirala Tower"); only unclaimed documents keep the family (0149 mints entities at authoring, closing that gap).
- **Entity pages render their documents**: `selectEntrySource` gained the encounter branch — an encounter entity's page is its group's first document by path (Ishirala Tower → ishirala-floor2.md; Return To The Monastery → its overview.md); previously two of the five entities rendered synthesized shells (stems like "overview"/"ishirala-perch" never matched their names). Authored entities/ pages still outrank via the exact flow.
- React 92/92 (matcher: group attachment + no cross-borrowing; tree: one entities block, family keeps only unminted docs).

### CLOSING BUILDS (2026-10-02, deployed) — the Ishi'ra'la split, the Timeline, and the audit flips

**The Ishi'ra'la split (Sean's ruling: "Ishi'ra'la was legitimately a group of encounters… 1 encounter per floor"):** the grouping rule changed from per-DIRECTORY to **per-DOCUMENT** — every encounter document is its own encounter (backend `_encounter_groups`: nested docs named from stem + parent context, digit-split — "Ishirala Floor 2"; the client matcher + tree claim test match per-document with the directory group as fallback for overview-style docs; digit tokens kept so Floor 2 ≠ Floor 3). **Data repair performed via the audited mint path**: five floor encounters minted (Perch 11, Floor 2: 5, Floor 3: 7, Floor 4: 5, Upper Floors: 3 — all 31 claims re-attributed by evidence document, no errors); **"Ishirala Tower" is now a claimless shell** — the first concrete use case for the deferred entity-retirement path (0139 deferred canonical deletion; it fails Q1 visibly until then; no rename API exists either).

**The Timeline slice (ADR-0021's timeline amendment):** the mint endpoint gained a `kind` parameter; **Timeline minted as kind `event`** with all **36** `timeline.md` orphans assigned (receipted initial attributions). The entity renders its document (exact stem match). 0042 keeps the dedicated ordered TEMPLATE build (reference viewing, BCE/CE).

**Q3/Q5 flipped to computed GLOBAL criteria** (the audit's pending pair is gone — `pending_criteria: []` forever): Q3 = live orphan count vs dispositions ("78 current claims without an owning record — the orphan review drains these"); Q5 = attribute-bearing profiles lacking any claim binding ("5 attribute-bearing profiles with no claim binding" — a NEW honest finding). Rendered on the panel under the count line.

**Live state after these builds: 131 entities, 81 qualified, 0 pending; 78 orphans remain** — the judgment tail (49 session claims + lore/handout residue) for Sean's clicks in the live queue. React 92/92; backend full suite green.

### The judgment tail worked (2026-10-02, Sean's five rulings + live drain)

Catalogue delivered 22 non-session orphans; Sean ruled item-by-item and worked most live while the build ran:

1. **Goodman's City ×4** → assigned to the location (page-backed; via API, receipts filed).
2. **Journals ×11** → **their NPC owners**: Vika Lana 4, Rhetus 3, Dariferra 2, **Mad 2 — Mad CREATED** (npc, identity-queue receipted create) per "Mads needs to be created." Sean worked these live in the queue.
3. **Cosmology ×6** → "needs a solution in general" — PROPOSED (awaiting go): the Timeline pattern — mint **Cosmology** as a worldbuilding Entity owning its document's records (the doc-first resolver attaches automatically), then re-attribute the assertions that truly serve existing records (Infinite Twilight, Far Realm Entity) at leisure — the same per-record judgment as the journals, with suggestions live.
4. **Campaign-bible note ×1** → assessed **NOT redundant** (no claim carries the chapter structure); migrated to the campaign_direction plan **"Campaign Bible — Three-Chapter Structure"** (create→approve→apply, receipted); the claim dispositioned with the migration reason.
5. **Zander's tattoo secret ×1** → migrated to the campaign_direction plan **"Zander's Tattoo — Hidden Truth (GM)"** (Zander named — campaign_direction correctly carries no in-world owner); the claim dispositioned, noting the other three secrets stay preserved on lore/hidden-truths.md for the **future GM-plans super document** Sean wants ("some time in the future to monitor these").

**State after: 55 orphans = 49 session claims (Sean's open surface question — deliberately set aside) + 6 cosmology (proposal pending). 83 of 133 qualified. Q3 live: "55 current claims without an owning record (2 dispositioned)."**

### The Mads correction + the identity rename capability (2026-10-02, deployed)

Sean's report: "Mads name is Mads, the Mad's Journal is a typo, it should be Mads' Journal." Investigation: Sean had already fixed the record's PROFILE live (canonical_name display copy, alias "Mads Mikkelson", minted race/sex/status — Mads is dead) but the entities-table name showed "Mad"; my earlier "Mad" creation was the mis-named one and my quick "Mads" creation duplicated the record. The rename gap (third occurrence: Ishirala Tower, then this) became a build:

- **Receipted identity name correction** (migration 0076 + `POST /identity/decisions/correct-name`): the migration-owned `correct_identity_canonical_name` function validates uniqueness (normalized), updates the entity, and files an identity_decisions receipt of kind `correct_name` (constraint extended). The OLD name deliberately does NOT become an alias — aliases are provenance-anchored (0052) and a corrected-away typo should not stay resolvable; the receipt's details preserve it.
- **The data repair**: the two journal claims consolidated onto the profiled record; my duplicate renamed to "Mads (retired duplicate)" (claimless shell); the profiled record renamed **Mad → Mads**. Both claim texts corrected via the receipted correction path ("Mad's journal records…" → "Mads' journal records…"). The journal DOCUMENT's frontmatter title keeps its typo verbatim — it is the immutable legacy source file (read-only collection); the canonical layers carry the truth.
- Evidence: backend suite green (the boundary test correctly forced the UPDATE into the migration function); deployed; both renames receipted live; Mads owns 5 claims (2 corrected journal + 3 minted attributes).

### COSMOLOGY RESOLVED + THE DRAIN'S FINAL NUMBERS (2026-10-02)

**Cosmology executed** (the Timeline pattern, per Sean's "continue"): minted as kind **worldbuilding** (the world's structure, not a historical occurrence — that distinction keeps `event` for the Timeline's history); all 6 claims assigned via receipted initial attributions with the doc-first resolver attaching `lore/cosmology.md` → Cosmology (exact stem match).

**THE DRAIN IS COMPLETE except sessions:**

| | |
|---|---|
| **Orphans remaining** | **49** — all session-note claims (Sean's open surface question) |
| **Dispositions filed** | 2 (campaign-bible plan migration + Zander GM plan migration) |
| **Qualified** | **84 of 135** (up from 71 at the campaign's start) |
| **Q3** | fail with the honest count: 49 without owners (the session surface question) |
| **Q5** | fail with 5 attribute-bearing profiles lacking bindings (new finding to chase) |

The campaign moved 132 orphaned claims to their owners (186 at discovery → 49 now, all sessions) and minted 12 entities (5 encounters + 5 floor encounters + Timeline + Cosmology) + 2 campaign_direction plans. The remaining 49 need the session-capture surface solution (0148 covers NEW captures; the backlog is the pre-0148 residue).

### THE SESSION BACKLOG SURFACE (2026-10-02, deployed) — 0138's final slice

Sean: "we need a backlog session promotion pipeline surface in migration." The 49 pre-0148 session orphans (captured before ownership-at-commit) now have a sequential review flow in the orphan panel:

- **"Review session backlog (N)"** button (decision-button prominence) opens the walk-through — one statement at a time, its source note path and Truth State/authority chips visible.
- **SubjectChoiceField** — the same component the session reviewer uses for new captures (0148's extraction pays off here): the lead suggestion PRESELECTED as a chip, other suggestions one click away, searchable via typeahead, or "No single record — ambient lore" (the receipted disposition).
- **Assign-and-continue**: one click files the receipted attribution and the re-gather brings the next statement. **Skip** advances without assigning. The backlog's position and count are visible ("statement N of M").
- The library refresh rides along (ADR-0022); the orphan list and audit update in the same interaction.
- React 94/94 (new test: opens the backlog, preselection confirmed, assign fires the receipted attribution, the next statement arrives after the re-gather).

### The Party quick-pick (2026-10-02, deployed)

Sean: "The primary owner of most of these is The Party, added as the faction Carpet Rollers, this needs to be an option that I don't have to search for." **SubjectChoiceField gained a `partyPick` prop** — a green "The Party · Carpet Rollers" chip rendered above the suggestion row, always visible when the party entity is resolvable (derived synchronously from the loaded orphan suggestions — Carpet Rollers appears on session claims), hidden when already selected. One click assigns to Carpet Rollers; no search, no scroll. Threading: the orphan panel computes it locally from its own loaded data (no dependency on the App's library load cycle — the async threading approach failed test timing; the synchronous from-suggestions derivation is both simpler and more reliable).

### Real-world date purge (2026-10-02, from Sean's live drain session)

Sean: "I missed the fact that I was marking a bunch of claims owned that have real world dates in them." The session-note claims carried their real-world capture dates into canonical text. **18 claims corrected** via the receipted correction path: `On YYYY-MM-DD, ` prefixes dropped; leading `M/D` session headers stripped; embedded `20XX` dates removed. **Campaign dates correctly survived** (`11/11/505`, `by 11/1/502` — years 502-505 are in-game, not real-world). The 2 skipped claims were campaign-date-only (correctly untouched). Zero real-world `On 20XX` prefixes remain in the canonical store. Reason on every receipt: "Real-world date purge (2026-10-02): session-note real-world dates are provenance, not campaign truth — stripped from the canonical assertion (TKT-0122 pattern)."

### THE DRAIN IS COMPLETE (2026-10-02, final)

**Zero orphans.** The last 3 session claims assigned to Carpet Rollers (Sean: "just manually do it" — the 3 that lacked the party chip because it derived from suggestions that didn't include Carpet Rollers; fixed to a mount-time lookup independent of suggestions). **186 → 0 across the entire campaign.** Q3's computed count now reads zero; the permanent guard holds.

**Remaining for the ticket**: the encounter slice (mint encounter entities from their documents — one action per encounter doc; default-from-page rule folded from 0148), the Timeline slice (0042's entity + template; the 36 timeline.md orphans), then Q3's flip to computed (counting dispositions as resolved).

### Side build delivered 2026-09-29 (deployed): the encounter creator + the un-consumed + menu (ADR-0021)

Sean's report ("before I forget"): "open sessions are consuming encounter creation. The + in the library should give access to the encounter creator, regardless of whether or not there's an open session." Investigation: there was NO encounter creator anywhere (encounters were imported documents only), and the + button was consumed — with a session live it opened table notes and the menu became unreachable.

- **The + menu is session-independent now**: it always opens; with a live session it leads with "Open session — table notes" (replacing Start), and every item stays reachable — Write session log, **New encounter**, Queue for Lore. Accessible name "New" (was "New session" — it is no longer session-shaped).
- **New encounter creator**: title + markdown body (## sections render as stages via the existing encounter page) → `POST /capture/encounters` (DM-only; `application/authored_encounters.py`) files an authored encounter document through the direct-input machinery with **zero statement extraction** — the 0148 guardrail philosophy: no claim enters canon ownerless by omission; encounter claims promote through reviewed surfaces and are owned by the encounter once ADR-0021's encounter-entity mechanism lands (0138's encounter slice). On save: the new document opens, sources refresh, receipt toast.
- Evidence: React 85/85 (new test: session live → menu still opens with all items → creator reachable → correct payload; 4 existing tests updated to the new button name); backend full suite green; deployed; route + DM-only guard + bundle verified live. No entity minting yet (kind `encounter` arrives with the encounter slice).

### Slice 1 delivered 2026-09-28 (deployed) — THE LIST EXISTS

Sean's ask: "create a phase 2 migration section for the orphaned claims so I can first see a list of them."

- **Core**: `application/orphaned_claims.py` + `adapters/postgres/orphaned_claims.py` + `GET /campaign/orphaned-claims` (DM-only, read-only). Each orphan carries assertion, state, authority, recorded day, capped evidence paths, and **deterministic suggested owners** (max 3): co-mention links (`claim_related_entities` — the importer's word-boundary linking + direct-capture mentions, 549 rows exist on orphans) outrank name-in-text matches (canonical names + `entity_aliases`, word-boundary, apostrophe-tolerant, longest-name-first). Suggestions are never authoritative; no AI in v1 (the 0137 seam-4 owner suggestions are a later wand-marked addition). Actionable-first sort (suggested rows on top, then text).
- **UI**: `OrphanedClaimsPanel` — the FIRST panel on the Phase 2 Migrations page (the ruled front): "List orphaned claims" button, count line ("N orphaned claims · M with a suggested owner"), rows in the evidence-item idiom (state/authority chips, orange suggestion chips with basis, assertion, source paths) inside a capped scroll container. No actions yet — slice 2 brings the Lore bridge / direct assign / no-owner-needed.
- **Live first run (2026-09-28)**: **182 orphans, 175 with a suggested owner** (324 co-mention + 119 name-in-text suggestions). First row: Zander's tattoo claim suggesting Zander Thromius/Vael'ka'noth/Inquisitors, all co-mentions. Population moved 186 → 182 during the day (Step 1 usage). Evidence: backend 4/4 (co-mention precedence + cap, word-boundary no-false-positives, apostrophe alias match, actionable-first sort); React 84/84 (new panel test: count line, suggestion chip, both rows); full suites green; deployed; bundle-verified.
