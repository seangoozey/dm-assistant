---
id: TKT-0140
title: Migrate the whole library to Qualified Entities — everything reaches the bar through the Promotion Pipeline
status: backlog
priority: P2
milestone: trustworthy-librarian
depends_on: [TKT-0136, TKT-0139]
created: 2026-09-21
updated: 2026-09-21
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
