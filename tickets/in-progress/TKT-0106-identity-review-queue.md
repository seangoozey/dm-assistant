---
id: TKT-0106
title: Identity review queue — continuous detection, presentation, and reviewed resolution of identity gaps
status: in-progress
priority: P0
milestone: shared-campaign-knowledge
depends_on: [TKT-0093]
created: 2026-09-11
updated: 2026-09-11
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
