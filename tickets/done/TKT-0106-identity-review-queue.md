---
id: TKT-0106
title: Identity review queue — continuous detection, presentation, and reviewed resolution of identity gaps
status: done
priority: P0
milestone: shared-campaign-knowledge
depends_on: [TKT-0093]
created: 2026-09-11
updated: 2026-09-13
---

# TKT-0106: Identity review queue — continuous detection, presentation, and reviewed resolution of identity gaps

## Problem

The measured live-slice trial (TKT-0103, 2026-09-11) showed canonical identity coverage is the retrieval bottleneck: only 46/170 extracted relationship edges anchor to canonical identities (53 entities, zero aliases). The Inquisition — the organization at the center of the campaign's organizational chain — is not a canonical entity; Grand Inquisitor is an unregistered role; `castle fleurite` is ambiguous between the `Fleurite` and `Fleurite Castle` tokens. Manual backfill does not scale: new lore, NPCs, and canon arrive continuously, so identity coverage must be a standing in-app capability, not a one-time fix.

## Design

The queue follows the established review idiom (import candidates, source reviews, failed plans): derived signals surface review items ranked by evidence; the DM decides; decisions become canonical only through exact, versioned proposals, approval, and receipts. Detection and ranking are programmatic; decisions stay human.

### Detection (three derived sources, one queue)

1. **Name mining over current claims** — deterministic, no LLM: recurring proper-noun phrases across claim text matching no canonical entity or alias, with counts and exact evidence spans. Fed by promotion/outbox events so new canon enters the queue automatically.
2. **Retrieval demand** — the unresolved-endpoint audit productized: endpoints the graph projection or relationship extraction cannot resolve (or resolves ambiguously) are logged with evidence and query context. This measures what retrieval actually reaches for, not just what text contains.
3. **Ambiguity hits** — mentions matching two or more candidate identities become alias/merge review items (extends TKT-0093 prose linking).

### Presentation (DM-only review surface)

Queue sorted by measured retrieval impact (unresolved edges suppressed, queries affected), each item showing surface form(s), frequency, claims and exact spans, candidate existing entities for aliasing, and the decision set:

- **Create entity** (with kind),
- **Add as alias** of an chosen existing entity,
- **Mark as role/title** — stays a property on edges/claims, not a node (decision stored as precedent for similar future gaps),
- **Dismiss** (retained in audit history; resurfaces if demand grows).

### Resolution (existing machinery)

All decisions flow through exact, versioned entity-metadata proposals → approval → atomic application → receipts. Alias additions improve resolution at query/projection time immediately — no re-extraction or index rebuild.

## Phase 1 implementation (2026-09-11)

Built end-to-end, working tree only (not deployed):

- **Detector + read-model in Core** (`application/identity_gaps.py`, `adapters/postgres/identity_gaps.py`): deterministic phrase mining over current claims — connector chains kept whole ("Court of the Stars"), group-boundary suffix surfaces so embedded mentions ("Members of the Silver Cloaks") aggregate with sentence-initial ones, sentence-start noise suppressed by lowercase-frequency, edge-connector stripping. Ranked by claim frequency; retrieval-demand ranking arrives with Phase 2's projection wiring. Surfaces resolving via canonical names/aliases or carrying dismiss/mark-role decisions never appear. 6 unit tests.
- **Four audited decisions** through `POST /identity/decisions/*` (DM-only, idempotency keys, receipts in new `identity_decisions` table, migration 0043): **create entity** (kind chosen at review; entity creation stays behind the database's canonical-write boundary via migration-owned `apply_identity_queue_create_entity`, mirroring `apply_campaign_change_set` — the architecture-boundary test enforced this and now passes); **add alias** (evidence-sourced: the alias row carries the source revision of a current claim containing the surface; refuses names owned by another identity — "merge requires explicit review"); **mark as role**; **dismiss**. Decisions are immediate DM commands with receipts, matching the approved profile-sync precedent; the multi-item proposal workflow remains for bulk work.
- **API**: `GET /identity/gaps` + four decision routes; Windmill review backend routes and both CampaignClient implementations added.
- **UI**: Identity Review panel on the Tools page — top 20 unresolved surfaces with claim counts, evidence excerpts, suggested alias targets (one-click with explicit receipt), kind selector + Create entity, Mark as role, Dismiss; queue refreshes after every decision. 1 React test (load → create faction → receipt → queue empties).
- Verification: local 452 passed/45 skipped; docker integration 22 passed across identity/alias/metadata/imports suites; React 74 passed, `tsc` clean. Known scope notes: ranking is frequency-only until Phase 2; the queue shows top-N by frequency (retrieval demand will re-rank); surface variant merging (possessives, leading-article duplicates across surfaces) is still on the detector-improvements list.

### Live-queue feedback round (2026-09-11, after Sean's first in-app pass)

Sean used the deployed queue (created Myrin through it). Reported issues and their dispositions:

- **Own page / presentation** — deferred to the back burner by Sean's request; also noted there: the Library presents source-backed documents (e.g. `lore/infinite-twilight.md`) alongside entity entries without distinguishing them, which made "Infinite Twilight" look already-canonical. The queue is correct — a document and 15 claims exist, but no entity identity.
- **Possessive surfaces ("Romulus's", "Ishi'go'dan's")** (FIXED): `normalize_surface` strips trailing `'s`/`'s`, so possessives of known identities resolve; unowned ones (e.g. "Ruh's") remain real gaps. Unit-tested.
- **"Alive Location" cross-line joins** (FIXED): phrases no longer cross line breaks — status blocks ("Status: Alive\nLocation: …") are field lists, not names; status values (alive/deceased/missing/…) are suppressed outright. Unit-tested; live queue no longer shows the entry.
- **"King Peter le Fleur" should be Peter le Fleur + alias** (FIXED): `strip_title_prefix` suggests a canonical name without person-title prefixes (King/Queen/Lord/Captain/Grand/High/…); the create button shows "Create as Peter le Fleur" and automatically keeps the full surface as an alias. Unit- and integration-tested.
- **Kind defaulted to faction even for obvious NPC names** (FIXED): `suggest_kind` proposes a kind deterministically — alias-target affinity first (all candidate entities agreeing), then tail-word vocabularies (faction/location/worldbuilding). The selector defaults to the suggestion and stays editable; title-prefixed person surfaces without other signals still default to faction rather than guessing npc. Unit- and integration-tested; live queue now suggests Jace→npc, Zander→pc, Infinite Twilight→worldbuilding, White Cloaks→faction, Chamber of Echoes→location.
- Known remaining noise (ticket improvement list, not fixed this round): first-name fragments of existing entities ("Jace", "Sorin", "Zander") should surface as alias candidates via first-token matching; plural role forms ("Inquisitors"); "Golden Dawn" inherited kind=location from its building entity via affinity — acceptable as a suggestion. Ruh is an undefined NPC, not a nickname of Ruhrogue (Sean, 2026-09-11) — the gap is legitimate; create as npc.

### Created identities arrive connected (2026-09-11)

Sean confirmed the queue's purview covers migration-era identity gaps (Infinite Twilight) and reported that Myrin only appeared in the Library after a manual refresh. Fix (migration 0046): queue-created identities and queue-added aliases now also record `derived_mention` associations for every current claim containing the surface or alias (constraint widened from 'mentioned'-only), so a created entity lands in the Library already connected to its claims — the receipt reports "N claims linked". The React app refreshes library entries after every identity decision (no manual reload) and shows the link count in the receipt message. Tests: two new integration cases (create links claims incl. cross-entity claims; alias links its claims) — 17/17 in docker; React 74 passed, `tsc` clean. Derived links are distinguishable from reviewed 'mentioned' links so a bad match can be suppressed without touching its source (TKT-0093 semantics).

Verification this round: 13 miner unit tests, 10 queue integration tests (docker), 5 alias-sync integration tests, local 459 passed/51 skipped, React 74 passed with `tsc` clean, and a read-only live-database queue run confirming the reported entries cleared.

### Undo as an audited decision (2026-09-11)

Sean asked how to undo an alias decision (receipt 0e8bd9ef: "Golden Dawn" → Church of the Golden Dawn, 29 claims linked); none existed. Migration 0047 adds the 'revert' decision kind: a revert references the receipt it reverses, both stay in audit history, and v1 reverts add_alias decisions by removing the alias row and **reconciling** the entity's derived links against its remaining names — links still justified by the canonical name or a surviving alias are kept (derived links are a projection of current claims × current names, so undo recomputes rather than blind-deletes). Double reverts and unknown receipts are refused; entity-creation reverts remain open design (entity retirement should follow the reviewed supersession pattern). UI: the queue panel keeps the session's recent decisions with Undo buttons. Sean's revert ran through the audited path: receipt b7b85f76, aliases_removed=1, links_removed=24, 5 links kept (still justified by the church's canonical name). Tests: 2 new integration cases (reconcile semantics + idempotent replay + refusal paths) — 14/14 in docker; local 459 passed; React 74 passed, `tsc` clean; deployed.

### Monastery/Fleurite display bug and linking hygiene (2026-09-12)

Sean reported the Monastery of Arkin entry showing Fleurite's document text after aliasing "Monastery" (receipt 3f131532, 23 claims linked). Root cause chain, verified from the audit trail: the alias linked Fleurite's own containment claim ("Fleurite contains ... Monastery ..."), legitimately pulling `fleurite.md` into the entity's source set — and the Library picked the entry's representative document as the alphabetically first `locations/` path, which `fleurite.md` now preceded `monastery.md` on. Two fixes: (1) representative-document selection now scores sources by entity-name token affinity with kind-root preference (both the entry view and the NPC dossier drawer; exported `selectEntrySource`, React-tested); (2) derived-link matching is now whole-word and case-aware (migration 0048 + adapter + reconcile): a capitalized surface ("Monastery") links only proper-noun usage, so lowercase generic prose no longer associates claims; lowercase aliases stay case-insensitive, and evidence lookups remain case-insensitive. The Monastery alias itself is domain-correct (the containment list's Monastery is Arkin's) and was NOT reverted; the Fleurite link is legitimate. Sean retains the audited revert path if he ever wants it. Deployed after clearing a stale Docker Desktop port proxy (the deploy's health wait 404'd while the server was actually up; `docker restart` of the windmill server restored the proxy, and the re-run completed the workspace sync). Verification: 15 identity-queue integration tests, 30 across the broader docker sweep, local 459 passed, React 75 passed, `tsc` clean.

### Possessive titles and the misspelling decision (2026-09-12)

Sean reported remaining possessives ("Castle Fleurite's", "Inquisitors'", "Inquisition's", "Kira Lana's") and the Corefera/Coreferra misspelling case. Fixes: (1) display titles now strip possessives with original casing kept — the key already aggregated "Inquisition's" into "inquisition", but the title kept the apostrophe; plural-possessive trailing apostrophes ("Inquisitors'") now strip in both key and display. Live queue verified: no apostrophes remain in any surface title. (2) New audited decision **mark_misspelling** (migration 0049): a misspelling resolves entity lookups and links its claims through an entity_aliases row with `alias_kind='misspelling'`, but the Library separates it from real aliases (summary now carries both arrays; the dossier shows "Recorded misspellings:" — never "Also known as"). This follows the domain model's own alias definition, which includes misspelled names, while keeping the correction auditable, reversible (revert guard extended to misspelling decisions), and semantically distinct from naming. UI: each alias-target search result has "Misspelling" alongside "Alias". Tests: miner possessive unit tests (14 total), misspelling integration case (lookup resolves, claims link, library separates, revert works — 21 total in docker), React misspelling flow (77 passed, `tsc` clean). Deployed; live queue verified.

### Unrelated-document borrowing (Ruh/Goodman, 2026-09-12)

Sean created Ruh via the queue; the Library showed Goodman's profile and document under Ruh with Ruh's claims. Root cause: Ruh (a queue-created identity with no file of his own) reaches claims through documents about other subjects — Ruh's death is recorded in npcs/Goodman.md — and the representative-source picker tied all nocs/ sources at zero name-affinity, falling back alphabetically to Goodman.md, whose NPC profile then loaded as Ruh's "information." Fix: a document may represent an entity only when its filename shares a name token with the entity (affinity > 0); identities without a matching document show their claims over the clean synthesized entry instead of borrowing someone else's file and profile. Applies to both the Library entry view and the dossier drawer. React-tested (78 passed); deployed. This generalizes the earlier Monastery/Fleurite fix, which scored affinity but still allowed zero-affinity root matches to win.

### Kind-appropriate synthesized entries (2026-09-12)

Sean created Far Realm (location) via the queue after Ruh (npc); Ruh rendered a valid character page but Far Realm did not render as a location. Cause: file-less identities fall back to a synthesized document, which carried only minimal frontmatter — enough for the pc/npc character view but not for the generic entry view real location files feed (kind frontmatter, a section structure, the canonical heading). Fix: `synthesizedEntryDocument` builds a kind-appropriate scaffold — location → "Established Facts", faction → "Operations", worldbuilding → `type: lore` + "Lore", pc/npc → "Current Status", plus item/event/rules_element headings and frontmatter aliases — so every queue-created identity gets a proper entry page with its claims. React-tested (79 passed, `tsc` clean); deployed. Follow-up fix the same day: the no-aliases stub variant glued the closing fence to the type value (`type: location---`), so frontmatter never parsed and alias-less identities like Far Realm rendered as bare "source" entries; the fence now stands alone in both variants, with a regression test asserting parseable frontmatter.

### Editable identity profiles (2026-09-12)

Sean: synthesized locations lacked location type/status/parent location, were not editable, and queue-created NPCs (Ruh) shared the problem — the character editor is document-bound and file-less identities have no document. Built the entity profile layer (migration 0050): versioned, receipted profile overlays keyed to the entity (`entity_profiles` + revisions + receipts), mirroring the PC-profile pattern; DM-only; stale-version refusal; idempotent replay; alias edits sync the managed 'profile' namespace with the same never-steal semantics (aliases require evidence provenance — an identity with no linked claims has none yet, so such aliases are skipped and reported). Canon status is deliberately absent from synthesized entries: real location pages carry it from imported source frontmatter, while a queue-created identity is canon by its decision receipt. UI: synthesized entries render profile fields into the entry (empty fields hidden in view mode, per Sean) and every file-less entry has "Edit identity" — locations get location type/status/parent location, characters race/sex/status/player, all kinds name/aliases/summary. Verification: 3 entity-profile integration cases in docker (location save/version/alias-sync incl. stale refusal; removal + conflict skips; idempotent replay — 19 total with identity queue), local 460 passed, React 80 passed with a full location-edit flow test, `tsc` clean. Deployed.

### Standardized edit affordance + style conventions (2026-09-12)

Sean: Romulus's edit button (compact RecordIcon in the standard `entry-page-actions` header slot) is the pattern synthesized identities should use — not the invented text-button bar. Fixed: StructuredEntryView gained the standard optional header edit action; synthesized character entries pass `onEdit` into CharacterDocumentView's existing slot; the invented `.identity-entry-actions` bar and its CSS were removed. File-backed characters keep document-profile editing; file-less identities open the entity profile editor from the same standard button. Sean also asked whether a style document is needed — agreed: a design-language reference (tokens, page widths, header/section/kicker idioms, button classes, icon-action slots) is now on the ticket's follow-up list so future pages check existing patterns first. React 80 passed, `tsc` clean, deployed.

### UI conventions reference (2026-09-12)

Written `docs/architecture/ui-conventions.md` (tokens, type stack, page widths, header rhythm, button vocabulary incl. the entry-page-actions icon slot, panel idioms, entry anatomy, form rules) and a live **Conventions** page in the app (nav after Tools) rendering every component with its CSS class named inline — swatches, each button class, card/queue/notice/empty examples, a miniature entry page, and the form grid — so styling can be fixed by name. Linked from the docs index; React-tested (81 passed); deployed.

### Button interaction audit (2026-09-12, from Sean's review)

Sean: no button may move or resize on hover/click; Identity's Create/Alias buttons were unstyled; the Full-entries toggle and Refresh had low-contrast hovers; Refresh also moved. Root causes found in CSS: two `transform: translateY(-1px)` hover rules (primary buttons + claim-editor actions) and a hover rule that filled the outline `.secondary-button` with dark `#68412d` while leaving its `#754831` text — dark-on-dark. Fixes: all hover movement removed (now rule #2 in ui-conventions.md); outline-button hover fills accent with white text; the toolbar toggle hover fills accent; new `.decision-button` (solid accent, slightly smaller than form primaries) + `.decision-button.outline` (fills on hover) applied to Create entity and Alias → actions; Conventions page documents both and states the no-movement rule. React 81 passed, `tsc` clean, deployed.

### Honorific surfaces and doomed creates (2026-09-12)

Sean asked about "Lily Valamacke · 7 claims · Alias → lily valamacke": the claims consistently say "Lady Lily Valamacke" (honorific), so the surface is legitimately unresolved — but three presentation flaws made it baffling: the compact row silently displayed the title-stripped suggestion instead of the raw surface; alias candidates rendered in lowercase (drawn from the lowercased known-name set); and Create-as-suggested would be refused ("that name already resolves") with no warning. Fixes: alias candidates now carry display-case canonical names from the entities table; the compact row and card title show the raw surface ("Lady Lily Valamacke") with the title-stripped suggestion labeled beside it; Create disables with an explanatory tooltip when the chosen canonical name already resolves to an existing identity, pointing at the alias action. For this case the correct decision is Alias → Lily Valamacke, linking the seven claims. 16 identity-queue integration tests in docker, React 81, `tsc` clean, deployed.

### Manual alias declarations (2026-09-13, from Sean's Golden Dawn create)

Sean's "Create with 1 alias" (canonical Golden Dawn, manual alias "Era of the Golden Dawn") silently failed: Core refused because the manual alias appears in zero claims — the per-alias evidence rule, correct for suggested aliases (they are mined FROM claims), wrongly applied to owner-typed names. Migration 0051 splits the paths: `manual_aliases` are declarations — no per-alias claim evidence required, provenance sourced from the created surface's own claim evidence, recorded as `alias_kind='manual_declaration'`, still refused when the name belongs to another identity; suggested `alias_surfaces` keep the evidence requirement. Claims link on manual aliases too (word-boundary, case-aware). The client sends manual aliases as a separate field, and decision failures now render as red `.notice.error` alerts (previously a silent flash — the refused decision left the queue unchanged and the plain status message was easy to miss). Verified: new integration case (manual alias accepted without evidence; name-theft still refused; details audited) — 25 identity/profile tests in docker; local 460; React 81 with the create call asserting the split; deployed.

### Self-resolving surfaces and declaration undo (2026-09-13)

Sean asked what happens when a manual alias declared during creation is itself an unresolved surface in the queue. Verified live: the alias is accepted (declarations need no per-alias evidence), the claims link case-aware, and the twin surface silently disappears from the queue on refresh because it now resolves — correct behavior, since resolution is the queue's exit condition. As a live demonstration the Inquisitors faction was created with "Inquisition" declared as a manual alias (34 claims linked; receipt recorded; this was the action Sean had described intending). The trace exposed one real gap: a mistaken manual declaration had no undo — create-entity revert is deliberately withheld, and the profile editor only managed its own namespace. Fixed: the entity profile editor now also manages `manual_declaration` rows (owner-named aliases, whichever namespace they landed in) — removal there deletes exactly those rows; evidence-based `queue_decision` aliases keep their own lifecycle (queue revert) and are never duplicated or removed by profile saves. 21 identity/profile integration tests in docker, local 460, deployed.

### Canonical-name expansion (Penelope Clinkhammer, 2026-09-13)

Sean's create failed with "manual alias 'Penelope' has no provenance: no current claim mentions 'Penelope Clinkhammer'" — his claims only ever say "Penelope" while he supplied the full name as canonical with the attested short form as manual alias. The provenance rule anchored manual aliases to the created *surface's* claim evidence; wrong anchor when the canonical name is expanded beyond what sources attest. Migration 0052: manual-alias provenance anchors to the alias's own claim evidence first, the surface as fallback, preferring claims that literally contain the alias; the refusal (now naming both spellings) remains only when nothing at all mentions either form. Claim linking already matched the manual alias, so such identities link their claims via the attested name. Integration case added (expanded canonical + attested alias: creates, links 2/2 claims, manual_declaration kind) — 22 identity tests in docker, local 460, deployed. The red-alert error surfacing from the previous fix worked exactly as intended in the field.



## Completion (2026-09-13): the full live review is done

Sean completed the entire identity review through the app. Final measured state:

- **281 audited decisions**: 65 create_entity, 34 add_alias, 171 dismiss, 7 mark_role, 3 mark_misspelling, 1 revert — every one receipted.
- **118 identities** (from 53 at the queue's start): 45 npc, 44 location, 16 faction, 7 worldbuilding, 5 pc, 1 item.
- **67 aliases** across three audited kinds (50 queue_decision, 14 manual_declaration, 3 misspelling) plus profile-synced rows.
- **819 derived claim links**; 407 of 448 current claims (91%) now touch at least one identity, 305 via evidence association — up from near-zero explicit association coverage when the queue shipped.
- **Queue: 0 remaining candidates.**

Every acceptance criterion is met, including the final one (Phase-1 validation against the live campaign, reviewed by Sean) — the review itself was the validation. Follow-on work is recorded separately: TKT-0107 (in-app graph view, deferred by request), pilot-bundle regeneration (refreshes Brainstorm graph traces), and re-running the TKT-0103/0104 retrieval evaluation now that identity coverage — the measured bottleneck — is closed.

### Pre-re-index repairs (2026-09-13, deployed)

Sean flagged three issues before any paid re-index. All resolved:

1. **Wrong faction kinds** (the queue's faction default): the entity profile editor now has a **Kind (audited)** selector — propose → approve → apply through the existing entity-metadata proposal path (full audited chain, receipts; the UI's first correction attempt surfaced that approval alone doesn't mutate — the apply step is now included). Three live corrections applied through the audited path: Eustice → npc, Michael Stromgard → npc, Ley Lines → worldbuilding. Judgment calls remaining for Sean: Circle of Dreams, Fleurite Exiles, Goodman City Exiles, Oracles (arguably factions or groups — left as-is).
2. **Faction template**: entity profiles gained `base_location` (faction HQ, shown in the hero), and Library summaries for factions now derive a **Members** list — pc/npc entities sharing claims with the faction (co-membership from evidence association, not aliases). Synthesized faction entries render Operations + Members sections.
3. **Court of the Stars document bug**: root cause was the word "the" passing the name-token filter in `selectEntrySource` — "Court of **the** Stars" matched ANY document with "the" in its stem (the-raven-king.md). Connector words are now excluded from name tokens; Court of the Stars gets its synthesized entry (its sources are all zero-affinity and correctly not borrowed). React-tested; the earlier Ruh/Goodman test still passes.

Verification: 27 identity/profile/metadata integration tests in docker (incl. new faction base_location + members derivation case), 460 local, 82 React, `tsc` clean; deployed; live kinds confirmed (Eustice npc, Ley Lines worldbuilding, Michael Stromgard npc).

### Faction membership as a first-class audited record (2026-09-13, deployed)

Sean validated the derived Members list ("kind of right" — 22 entries incl. non-members like Romulus, Malygos, Raven King) and ruled: Faction Members are a key graph relationship; auto-association is useful but MANUAL MANAGEMENT IS A BASE REQUIREMENT. Built (migration 0054): `membership_records` (faction, member, optional role title, optional evidence claim, superseded-removal with in-place audit; current-row unique per partial index) behind `apply_membership_decision` — add/remove are audited `membership` decisions in identity_decisions with receipts; add refuses duplicates, remove refuses when no current record, faction target enforced. Library faction members now prefer the explicit roster; the derived co-mention list appears ONLY while the roster has never had a record (deliberate: once the DM curates, retrieval noise never re-enters the roster). UI: faction entity-profile editor gains a Members (audited roster) block — search to add, Remove per member (name resolved through entity lookup since summaries carry names). Carpet Rollers seeded with the real party roster (11 members: Ruhrogue, Coreferra, Zander Thromius, Dariferra, Lucindus Arellius, Martin Faeroth, Kira Lana, Ladir, Merghana, Rhetus, Penelope Clinkhammer) through the audited path. Auto-association suggestions (surfacing likely members in Identity Review) is future work. 28 identity docker tests + 460 local + 82 React; deployed.

Follow-up fixes (2026-09-13, deployed same day): (1) member add/remove did not refresh the roster on screen — the handlers now reload the library entry after the audited decision, and the editor stays open through roster changes (only Save profile and Kind correction close it); (2) the Save identity profile button used default styling — now the standard `.decision-button` commit style per `docs/architecture/ui-conventions.md`. Regression test `refreshes the faction roster in place after removing a member` (asserts remove → entry reload → roster shrinks → editor stays open); React 83 passed, `tsc` clean. Verified live in the deployed app (Carpet Rollers editor: roster block renders, Save button computed style matches the #82533a decision-button token).

## Phasing status

1. **Phase 1 (DONE, above)**: deterministic detector + queue read-model + all four decisions, audited.
2. **Phase 2 (DONE 2026-09-11, working tree)**: retrieval-demand ranking. Migration 0044 adds a derived `identity_demand_log`; the `/entities` lookup route records a best-effort demand hit whenever a DM lookup returns zero matches (names that resolve are never demand; telemetry failures can never break the read path). The queue now ranks demand-first — a surface with measured lookup misses outranks a more frequent surface nobody reaches for — with frequency as the secondary key. The queue is computed live per request, so promotions re-detect on the next load with no event wiring needed; the heavier outbox-driven projection refresh belongs to TKT-0092's track. Gap cards show "N lookup misses" when nonzero. Tests: two new integration cases (demand ranking with a resolving-name no-op; HTTP-level miss recording) — 6/6 in docker; local 452 passed/47 skipped; React 74 passed, `tsc` clean.
3. **Phase 3 (DONE 2026-09-11, working tree)**: ambiguity/merge items and role precedent. Migration 0045 adds `apply_identity_queue_create_identity` — one audited, atomic decision that creates an identity AND merges related surfaces as its aliases (entity, change set with exact coordinates, evidence-sourced `identity_queue` aliases, decision receipt, or nothing on any rule failure: an alias owned by another identity or lacking current claim evidence aborts the whole decision). The queue presents `related_surfaces` per gap — variant detection relates subset/overlap surfaces and surfaces sharing a distinctive word, while generic organizational nouns ("Silver Cloaks" vs "White Cloaks") do not relate; sharing a proper head noun ("Church of Malygos" / "Cult of Malygos") relates them *without merging* — the Cult-vs-Church correction is encoded as the presenting rule. Related surfaces arrive checkbox-selected (merge is the common case; deselecting is the explicit refusal), and the create button becomes "Create with N aliases". Role precedent: surfaces the DM marks as roles contribute their final content word; later gaps ending in one of those words carry a non-blocking "ends like a role you have marked" hint. Tests: 2 unit (grouping, precedent), 3 integration (merge-create audited incl. details, rejected-alias atomicity, role hint) — 9/9 in docker; local 454/50 skipped; React 74 passed, `tsc` clean.

## Included repairs (user-reported, verified 2026-09-11)

- **Alias input rejected spaces** (FIXED): the shared PC/NPC profile editor trimmed every keystroke, so a trailing space was deleted before the next keystroke landed — "The Grand Inquisitor" was literally untypable. Fixed in `App.tsx`: the in-progress segment keeps its trailing space mid-word, earlier segments are trimmed, blur normalizes, and save trims/filters. New React test `accepts aliases with spaces while typing and trims them at save`; 73/73 pass with `tsc --noEmit` clean.
- **Profile aliases never reach `entity_aliases`** (IMPLEMENTED 2026-09-11): profile saves now sync the focal entity's aliases inside the same transaction. The focal entity is resolved through claim evidence (exactly one entity whose claims are evidenced by the document; multiple candidates narrow by exact case-insensitive name match; persistent ambiguity skips the sync — measured live coverage: every npc/pc document resolves to exactly one entity; only 3/53 entities carry the older change-set document link, so that path was unusable). The profile editor manages its own `profile` namespace: new aliases insert (`alias_kind='profile_edit'`, the pinned source revision), aliases removed from the profile delete only that namespace's rows, and aliases whose normalized form belongs to another identity are skipped, never stolen. Every mutation is recorded in the receipt (`alias_sync` jsonb, migration 0042) and replayed idempotently; the save message in the React app reports applied/removed/skipped aliases. Verification: 5 new integration tests (`test_pc_profile_alias_sync_postgres.py`: apply+lookup, idempotent replay, managed-namespace removal, conflict skip, no-focal-entity skip) plus entity-metadata/imports/change-set suites — 24 passed in docker; remaining integration suites 20 passed; local 446 passed/41 skipped; React 73 passed with `tsc` clean.
- **Stale integration counts repaired** (found during verification): `test_imports_postgres.py` expected the pre-wiki-link-fixture set (17 documents/18 candidates) while the committed fixture set scans 20/20 (cross-references + shared-vault pair, 2026-08-04); counts updated to match the committed fixtures.
- **View-mode shows no empty alias row** (OPEN, cosmetic): aliases render nothing until editing begins; add an explicit empty state.

## Verified findings and directions (2026-09-11, read-only DB checks)

- **Infinite Twilight exists as canon content but not as an identity**: 15 current claims reference it (lore-sourced, as Sean noted), while the entity registry has zero matching entities. This is precisely the queue's content-versus-identity distinction — the detector flagged an identity gap, not missing lore.
- **Myrin confirmed as a migration miss** (Sean: "the root of all locations"): 28 claims mention it, no identity. First queue-validated create candidate (worldbuilding/location kind decision at review time).
- **The `faction` kind exists in the controlled vocabulary but zero entities use it**: the registry's 53 entities are typed location x31, npc x18, pc x4. The Library already groups entries dynamically by kind, so a Factions branch materializes automatically once organizations carry `kind=faction`.

### Kind rulings from Sean (2026-09-11 — first queue precedents)

- **Correctly typed locations, no change**: Church of the Golden Dawn, Heart of Unity, and The Estate are buildings in Unity. Grey House was literally a family house — "not an organization in any way"; the organization that inhabited it was **the Rebellion**, a missing faction identity (detector: 3 claims, demand 1). Monastery of Arkin (sanctuary building) stands as location.
- **Two distinct Malygos-worship organizations, not one** (Sean, correcting an over-consolidation): the **Cult of Malygos = the Stars = the Court of the Stars** are one identity; the **Church of Malygos = Priests of Malygos** are a second, separate identity. Sean accepts merging a church with its priests as not worth distinguishing, but the Cult and the Church are different organizations. Queue lesson recorded: never cluster surfaces by shared deity or head noun — "all Malygos worship is one org" was a real-world heuristic bleeding in, and exactly the kind of merge that must remain a human ruling. Canonical names chosen at review.
- **"Watch" is generic, not one faction**: most cities have a watch. Standalone "Watch" candidates are excluded as common-noun organization patterns; they resurface only when qualified by context (e.g., a specific city's watch).
- **Fleurite Castle**: possibly faction-worthy as the seat of power in the city — Sean's call at review time; location is defensible.
- **Missing faction identities identified so far**: the Cult of Malygos/Stars/Court of the Stars, the Church of Malygos/Priests of Malygos, the Inquisition, the White Cloaks, the Rebellion; candidate list adds Council of Unity (7 claims) and Assassins Guild (3 claims).
- Detector fixes after Sean's review (2026-09-11): connector chains now supported ("Court **of the** Stars" was being fragmented into bare "Court"/"Stars"); words frequent in lowercase are suppressed as sentence-start noise ("This"/"On"/"In" class); candidates 1,472 → 1,284. Remaining known limitations recorded for the in-app queue: merge surface variants (leading articles, possessives, trailing sentence continuation), synonym clustering as review suggestions (never auto-merge), first-name fragments as alias candidates ("Jace"/"Zander"/"Sorin" → existing entities), and no console truncation — pagination in-app (the offline script's top-25 print was display-only; the full ranked list is the artifact).

## Acceptance

- [ ] Detector runs on demand and after promotions (outbox-driven), deterministic, no provider calls in Phase 1.
- [ ] Queue ranks by measured retrieval demand; each item shows evidence spans and candidate resolutions.
- [ ] All four decisions flow through versioned proposals with receipts; no auto-created entities or aliases.
- [ ] Alias additions improve lookup/mention/resolution immediately without re-extraction.
- [ ] Profile-alias → `entity_aliases` disconnect resolved per the design decision, with tests.
- [ ] Phase-1 validation run against the live campaign recorded (candidate list with counts and demand), reviewed by Sean.

## Validation

Phase-1 offline proof: `deploy/evaluation/identity_gap_candidates.py` mines current canonical claims read-only and ranks gaps, cross-referenced with the 124 unresolved endpoints from the live-slice audit. No canonical writes; candidates are derived review items, never auto-promoted.

## Constraints

Derived detection never auto-creates or merges identities. Similar names never merge without explicit review. Dismissed items remain queryable in audit history. The queue is DM-only. Role-vs-entity precedent decisions are recorded, not just applied.
