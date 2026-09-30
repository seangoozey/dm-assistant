---
id: TKT-0140
title: Migrate the whole library to Qualified Entities — everything reaches the bar through the Promotion Pipeline
status: done
priority: P2
milestone: trustworthy-librarian
depends_on: [TKT-0136, TKT-0139]
created: 2026-09-21
updated: 2026-09-28
---

# TKT-0140: Migrate the whole library to Qualified Entities — everything reaches the bar through the Promotion Pipeline

## Context

Sean's ruling (2026-09-21): migrate **everything in the library to a Qualified Entity**, including summaries. **Blocked by stable promotion** — the Promotion Pipeline (TKT-0136) must be complete across its surfaces and proven in real use before this runs, because the pipeline is the migration's engine. **Blocked by the standard** (TKT-0139) — the migration audits against the Qualified Entity definition. Per the standing productize rule, this lands as a standing in-app review (an "unqualified entities" queue in the Tools panel), never a one-time manual backfill.

## Scope when taken up

- **Core audit endpoint**: compute the Qualified Entity checklist per entity (TKT-0139's machine-checkable bar) and return the unqualified set with per-entity reasons — the queue's data source, re-runnable so newly-degraded entities reappear.
- **Summaries migrate via the Promotion Pipeline**: profile `summary` content becomes a Description through the pipeline, not a copy — the prose derives candidates, statements face the mandatory include-or-exclude review (ADR-0018 pt 8), and the description files with provenance. Live today: 1 substantive summary of 19 profiles; the field is then retired (editor + synthesized-page injection removed, per the ADR-0015/0017 violation assessment of 2026-09-21).
- **Route every unqualified entity through its lane**: zero-claims entities via their actual material sources — unpromoted documents/candidates through promotion review (Lore/entry revision), and, where an orphaned claim's obvious home IS this entity, assigning it via the TKT-0138 review (that assignment can be the entity's first claim — the one intersection between the orphan queue and this campaign, per Sean's 2026-09-21 correction: orphaned claims are a claim-side population, not a lane of this campaign); vocabulary failures via the chip editor; wrong-kind records via the profile editors.
- NOTE (Sean, 2026-09-21): this campaign is about Entity-shaped Documents forced into compliance — entity-side gaps. TKT-0138 (claims with no owning entity) is its own standing claim-side review, valuable independently, feeding Q3 when it lands; it is NOT folded into this campaign.
- **The queue drives to zero and stays there**: entity-level rows with reasons and shortcuts into the right lane; progress visible (like the identity review's 281-decisions run); completion recorded with evidence.
- Non-entity record classes (plans, encounters, sessions) follow the TKT-0139 scope ruling — presumed excluded unless a parallel standard is ruled in.

## Out of scope

- Auto-qualification: every fix is an explicit DM action in its reviewed lane; the audit only finds and routes.
- New qualification criteria beyond TKT-0139's definition.

## Validation evidence

(to record when built)

### Slice 1 delivered 2026-09-21 — the campaign surface: Phase 2 Migrations page

- **The Migration nav slot is now the Phase 2 Migrations page** (Sean's ruling: reuse the Migration page; shelve phase 1): header framing the completion campaign, the **Qualified Entities panel** (audit re-runnable on open; count line; unqualified rows GROUPED by failing criterion; routing: Q1 → "Open entry — promote its material", Q4 → "Fix kind", **Q6 → one-click "Re-activate '{value}'"** filing the vocabulary restore receipt in place — Core criterion results now carry structured vocabulary/value for this), and the **Unpromoted material panel relocated from Tools** — one migration-completion home.
- **Phase 1 shelved behind Settings** ("Phase-1 Migration wizard" flag, default OFF): the six-step wizard, import queue, and extraction machinery stay reachable for the session-note review and legacy proposal review until session review is re-homed (both flows navigate to migration-legacy explicitly; noted as queued follow-up).
- Live structured Q6 findings: Catlantis/Fleurite (location_type), Andice Thromius/Bruteus Ponteius/Martin Faeroth/Nero (race) — each one click from resolution.
- React 141/141 (nav-slot swap, flag-gated wizard tests, panel scoping); Core audit unchanged (53/120 live).

Remaining: slice 2 (summary retirement through the pipeline); the drive to zero; then standing re-check holds it.

### Slice 2 delivered 2026-09-22 — summary retired (migration already done by Sean)

- **The one live summary was already migrated — by Sean himself**, live-testing the pipeline: `entities/osirus.md` and `entities/nero.md` both filed through promotion review on the morning of 09-22. Osirus promoted its genuinely-new statement (1 current claim — the pipeline's first real user-run promotion); Nero filed with all statements excluded (the deliberate reviewed-zero outcome) and honestly remains the empty shell the audits flag for revision.
- **The field is retired**: the profile editor's Summary textarea is gone, and synthesized stand-ins no longer inject it (the model keeps reading old data, writes simply stop offering it). Q8's presentation discipline is now structural — nothing can re-create the canon-side prose blob.
- React 141/141; deployed.

**Campaign state**: 53/120 qualified, 67 unqualified (65 Q1 + 6 Q6 — the six one-click vocabulary restorations are on the Phase 2 page). Standing unpromoted: 1 shell (Nero), 5 pending captures, 1 unpromoted brainstorm. The drive continues in use.

### Audit cohesion fix (2026-09-22, deployed, live-verified)

Sean's WIP test (the open Wrath of Romulus brainstorm) exposed a double-count: the unpromoted audit listed the session SIX times — five per-thought document rows (thought docs carry pending candidates, hitting pending_captures) plus the session row. Fixed: brainstorm thought documents are excluded from pending_captures and fold into their session's single unpromoted_thoughts finding. Harness 7/7 (new test: five-thought WIP → exactly one finding, count 5). Live: Wrath of Romulus = 1 finding; pending_captures now 0 (Sean reviewed the five session-note captures himself during the morning's pipeline testing). The Library's 5× GM-planning listing of the same thought docs is TKT-0144's scope, not the audit's.

### The Q1 lane becomes actionable — gather + move home (2026-09-22, deployed)

Sean's live feedback: the audit showed all unqualified entities with **no way to do anything about it** — "Open entry" landed on a bare zero-claims page (the only path was writing prose from scratch; the material was unreachable). Fixed with the **Q1 gather lane**: each Q1 row gains "Gather claims about this record" — an entry-scoped material scan (claims mentioning the name across source documents, using the backward-ownership labels), each result showing its owner with a **"Move here"** action (receipted re-attribution, provenance untouched, old owner keeps a moved-reference tile); ownerless results flag as needing the orphan review (TKT-0138). "Done — re-run audit" refreshes the standing. The dead-end "promote its material" label became "write its description" (the authored-prose path, which is the OTHER lane).

**Population discovery from the live data**: the library endpoint counts mentions, so only Nero is truly claimless — the other 64 Q1 entities are **mention-rich, subject-poor** (material exists, owned by others) and **206 orphaned claims** sit in the database. The gather lane is precisely the machine for the first; 0138's initial attribution for the second.

React 142/142 (new test: audit renders rows + gather lists owned/orphaned claims with owner labels + Move here re-attributes + moved claims leave the list).

### Step 1 delivered 2026-09-22 — Assign Ownership over document-exclusive claims

Sean's ruling: take all unqualified entries, gather the claims that appear ONLY on the Document representing them, list with checked boxes and an Assign Ownership button that assigns those claims to the entity those documents represent. Delivered:
- **Core**: `GET /campaign/unqualified-exclusive-claims` — per unqualified entity (Q1 failures), the page matcher's essential rules server-side (authored entities/{slug} page wins; exact stem; distinctive-token subset, never another entity's exact name) resolve its representing document; claims evidenced ONLY on that document (dual-evidenced excluded), non-superseded, with owner labels.
- **Initial attribution** (migration 0067 + 0068): `move_claim_subject` accepts a NULL old owner (matching subjectless claims); `ReattributionReceipt.old_entity_id` nullable — the migration's provenance-first orphans can now be assigned for the first time, receipted, provenance untouched. The re-attribution service distinguishes missing claims (error) from orphaned ones (initial attribution).
- **UI**: the Phase 2 page's Qualified panel gains the **Step 1 — Assign Ownership** section: "Gather document claims" loads the endpoint; per-record groups (name, count, document path) list their exclusive claims with checked boxes (all checked by default, owner labels distinguishing "no owner — initial attribution" from "currently owned by X"); per-record **"Assign Ownership (N)"** re-attributes the checked claims, toasts the result, re-gathers, and re-runs the audit.
- **Evidence**: harness 8/8 (new end-to-end test: doc match + exclusivity [dual-evidenced claim excluded] + initial attribution landing in the DB); React 143/143 (gather renders groups, uncheck excludes from the assignment, Assign Ownership re-attributes exactly the checked claim, toast).
- **Live first run**: 4 records / 24 exclusive claims — **Raven King: lore/the-raven-king.md, 6 claims, all unowned** (the whole history we walked through, ready for one button).

### Mention display + the blank-draft fix (2026-09-24, deployed)

Two rulings from Sean's Far Realm Entity review:

- **Mention-anchored clamps + owner titles**: claims owned by another record now render on a Document with an "owned by {owner}" title, and long claims clamp around the FIRST SENTENCE CONTAINING THE MENTION with leading/trailing ellipses covering omitted sentences (the relevance is visible at a glance instead of buried — the statue claim showed its first sentence, which never mentioned the Far Realm Entity). ClaimAssertion gained `contextName`; threaded through the character and structured claim lists. The backward-ownership link extended to the library entries endpoint (claims + history now carry subject_entity_id/name — live-verified: the statue claim reads owner "Fleurite Treasury").
- **Blank description drafts diagnosed and fixed**: the prose jobs SUCCEED server-side (latest Far Realm Entity draft: 3,563 chars, 781 tokens, 8 citations) — the drafts were never injected. Root cause: two of the three DescriptionComposer call sites (the character-view branch and the unpaged-NPC branch) never passed `initialText`/`initialSelected` — "Return to draft" opened a blank composer for NPCs. Both now seed the composer exactly like the structured branch (initialText, initialSelected, documentId for revisions).
- React 144/144 (new mention-clamp test asserting the owner title, the anchored sentence with ellipses, and the full text behind the expander); harness 8/8; deployed.

### Data fix (2026-09-24): attribute vocabulary poll + normalization (migration 0072)

Sean's ruling after the PC updates tripped Q6: poll all attribute values — auto-migrate obvious vocabulary equivalents, report the rest. Findings: the vocabularies were nearly empty of the campaign's real values (race knew half-orc/tabaxi/god only; sex was EMPTY; status knew only 'retired'), while profiles carried Capitalized import-era casing ('Human', 'Half-Orc', 'Continent', 'Male', 'Active', 'Dead', 'Disbanded'). Migration 0072:
- **Created 12 vocabulary values** (receipted, lowercase per existing style): race += dwarf, human, gnome, half-elf, high elf; sex += male, female, unspecified; status += active, dead, disbanded; location_type += region. Every value found in the poll now has a home — nothing unmatched remains to report.
- **Normalized 28 profile attribute values** to canonical casing (case-insensitive match against active vocabulary).
- **Normalized 13 automation-minted attribute claims** ("race: Human" → "race: human"); provenance/evidence untouched (casing fix of automation output, not content).
- **Live effect: Q6 failures 6 → 0; the audit jumped 63 → 71 of 120 qualified** (the six Q6 records plus chains where the profile normalization completed Q1 via minted bindings). Ladir and the PCs clear.

### Correction: the Q6 failures were an audit bug, not missing vocabularies (2026-09-24)

Sean's catch: the Settings page showed the full seeded vocabularies all along. Root cause: the vocabulary system is TWO layers — a code-seeded baseline (`VOCABULARIES` in template_vocabularies.py: 17 location types, 6 statuses, 10 races, 3 sexes) merged with DB-stored overrides (Settings adds/retires like the retired dragonborn) — but **the Qualified audit's Q6 queried only the bare `template_vocabularies` table**, blind to the seed. 'dwarf'/'active' failed Q6 because the audit couldn't see the seed that offered them; migration 0072's value creation was therefore redundant (harmless — the merge dedupes — but unnecessary).
Fixed: the audit's `active_vocabulary_values` now applies the same merge as `TemplateVocabularyService.values()` — (seed ∪ stored) − stored-retired — so Q6 judges against exactly what Settings and the dropdowns offer. 0072's normalization statements (28 profile casings + 13 claims) remain valid work. Ledger repaired by dropping the 0072 row (statements are idempotent; Core re-applied from its image copy — harness 8/8 green first). Live: 71/120, Q6 = 0.

### Bastok repaired (2026-09-24): 0072's profile rewrite had flattened JSON types

Sean's report: Bastok's editor failed to save ("profile version changed") and the profile GET 500'd. Root cause: 0072's original statement 2 rebuilt profile_json through `jsonb_each_text`, which flattens every value to text — **28 profiles lost their JSON types** (aliases arrays became the string `'["x"]'`, life_status_since objects became text), breaking EntityProfile validation and the editor's load/save cycle. Fixed:
- **2a repair**: string-typed aliases/life_status_since converted back to real JSON (28 aliases rows + 1 object row); live count of corrupted rows = 0.
- **2b rewrite**: normalization now uses `jsonb_set` on ONLY the four vocabulary string keys — never rebuilds the object, so types survive by construction.
- Harness 8/8; deployed; ledger repaired by drop-and-reapply (statements fully idempotent). Live: Bastok profile GET clean (version 1, status active, aliases []); audit holds 71/120, Q6 = 0.

### Q1 gather lane removed; Open Entry auto-opens the composer (2026-09-27, deployed)

Sean's ruling after live use: the Migration page's **"Gather Claims about this Record" button appears to do nothing** (a whole-document scan by name match — slow, and its results duplicated what the step-1 exclusive-claims section already offers) and is "kind of useless anyway". The Q1 lane is now:

- **Removed outright** — the gather handler, the moved-home handler, the drawer, the button, the `GatheredClaim` type, and the dead `.qualified-gather` CSS. Q1 rows keep exactly one affordance: **"Open entry — write its description"**.
- **Open Entry now lands the writer open**: navigation through the guard loads the entry, then (mirroring the tested Write-Description path) seeds nothing (a Q1 record has no sheet Background to prefill) and opens the DescriptionComposer — `loadCanonicalEntry` now returns the loaded entry so the post-load callback can act on it. Arrival = ready for prose, no second click.
- React 80/80 (new test: a Migration Q1 finding's page opens the Description composer directly; assert the gather button is gone); tsc clean; deployed and bundle-verified in the Windmill DB (gather strings and CSS absent from the served bundle).

## Closed 2026-09-28 — Sean's ruling: the finite campaign is delivered; Q1 completion is baseline

Delivered: the Phase 2 Migrations page (Qualified Entities panel with re-runnable audit, Q6 one-click restores, Step 1 Assign Ownership over document-exclusive claims with initial attribution), summary retirement, the 0072 vocabulary data fix + audit seed-merge fix, the Bastok corruption repair, and the Q1 gather-lane removal with composer auto-open. Campaign state at close: **71 of 120 qualified; Q6 = 0; 0 corrupted profiles.**

Sean's closing ruling (2026-09-28): "Writing prose for Entities is a baseline purpose of this app and thus has no end." The remaining 49 unqualified records are all Q1 (zero claims of any kind) — finishing them is ongoing app usage (descriptions, Step 1, promotion review), not a campaign deliverable. The standing enforcement stays: the audit holds the bar — an entity whose claims drop to zero reappears as Q1-failed, and nothing new can be created empty (mandatory review + minting). The ORPHANED-CLAIMS side of incomplete migration (186 ownerless claims, invisible today) is the relevant gap and continues as TKT-0138 (ready, P1). Q5's audit flip rides with 0138.