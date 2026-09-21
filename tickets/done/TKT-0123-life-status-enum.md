---
id: TKT-0123
title: Life status as an enumerated, audited entity dimension
status: done
priority: P1
milestone: shared-campaign-knowledge
depends_on: [TKT-0097]
created: 2026-09-15
updated: 2026-09-15
---

# TKT-0123: Life status as an enumerated, audited entity dimension

## Context (Sean, 2026-09-15)

"The dead member issue… if it cares about a status, shouldn't that status be an enumeration and not an arbitrary string?" The 0097 V1 death detector regexes prose — scaffolding. Life status is a dimension: `alive | dead | undead | resurrected | unknown`, character-scoped, with an effective date and a backing claim. Goodman ("resurrection as a golem") is `resurrected`, not `dead`; Martin is `dead` since 505-11-05. Structured status is the proper input for the conflict detectors (dead-member-on-roster, leadership held by the dead) and retires the regex.

## Design (agreed in conversation)

- **Field**: `life_status` on entity profiles (character kinds pc/npc), enum, plus `life_status_since` (CampaignDate) and `life_status_claim_id` (backing claim). Distinct from the profile's existing free-text `status` (organizational/location status — different dimension, untouched).
- **Audited path**: a status change is a receipted decision anchored to a claim (the observed death/resurrection). API: POST /entities/{id}/life-status (DM-gated, body: status, since date, claim id, idempotency key). Stored in the profiles table versioned rows; history in decision receipts (identity_decisions family or profile receipts — reuse what profiles already write).
- **Backfill = review, not bulk write**: queue proposing `dead` for entities with an observed, dated death claim; DM confirms each (productize rule). Expected volume small. Resurrected/undead proposed nowhere automatically — DM sets those manually with backing claims.
- **Detector switch-over (0097 increment)**: conflict queue gains "current membership/leadership seat whose member's life_status is dead (as of before the seat)" — mechanical, no prose matching. The regex death detector retires once backfill covers its cases.
- **Display**: hero field "Life status" (with date) on character entries via the entity template; the glossary gains the term.

## Scope

1. Migration 0060: profiles table columns (life_status, since y-m-d, claim ref) + CHECK enum.
2. Repo/service + API route (audited, idempotent).
3. Backfill queue endpoint (observed dated death claims → proposals) + review UI on the Tools conflict panel family.
4. Conflict detector: dead-member-on-roster + dead-leader-seat (reading the enum); retire regex death detector after backfill.
5. Hero display + glossary entry. Tests: docker (enum set/get, backfill proposal, detector fires on roster, regex path retired), React (status display, backfill confirm).

## Out of scope

- Enums for organizational/location status (separate ruling if wanted); AI-suggested statuses; non-character kinds.

## Delivery (2026-09-15, deployed — power disruption mid-build, resumed clean)

- **Model**: `life_status` (`alive | dead | undead | resurrected | unknown`), `life_status_since` (CampaignDate), `life_status_claim_id` on EntityProfile — the profile is stored as jsonb, so no migration was needed; versioned rows + receipts come free from the existing audited profile path. Distinct from free-text organizational `status`, per the design.
- **Backfill queue** (`GET /campaign/life-status/proposals`): observed, dated, name-adjacent death claims for entities without a life status — profiles seed on first confirm for entities never edited (Martin had no profile row; caught live and fixed). **Killer-vs-killed ambiguity caught live and fixed**: Gren's "Gren granted one pass and killed 200 soldiers" matched the loose 80-char adjacency — the pattern now requires the death word immediately after the name (linking verbs only), in BOTH the proposals query and the 0097 conflict queue. Live queue after fix: **exactly one proposal — Martin Faeroth, 505-11-05.** Zero noise.
- **Status writes** (`POST /campaign/life-status/{id}`): DM-gated, receipted against the backing claim, idempotent.
- **Dead-seat detector** (`GET /campaign/dead-seats`): current roster seats and leadership whose member's audited life_status is dead — mechanical, enum-driven, no prose matching. Empty until Sean confirms Martin (correct — his decision).
- **UI**: Life status panel atop Tools (proposal cards with the full backing claim, Mark dead action, Seats-held-by-the-dead listing); hero "Life status (since 505-11-05)" row on character entries; glossary term with the tooltip.
- Validation: docker `test_life_status_backfill_and_dead_seats` (proposal from observed claim → audited confirm writes enum+since+claim → dead seat surfaces → queue drains) — 8/8; local 462; React 112 (proposal confirm with correct coordinates, dead-seat rendering, hero field). Deployed; API-level live verification (browser session lost auth in the power cut — Sean's session unaffected). The domain query-time death hint keeps its entity-linked rule (records carry no names); the Postgres detectors are authoritative.

## Follow-up delivered same day (Sean's request): editor dropdown for continued backfill

The character profile editor (the NPC/PC template entry surface) gained a **Life status select** — Not set / Alive / Dead / Undead / Resurrected / Unknown — with a since-date field appearing when a status is chosen; saves ride the same audited profile write (version + receipt). This is the manual backfill path beyond the detector's death proposals: Goodman → resurrected with a date, undead NPCs, corrections. React test covers select → date → save carrying `life_status` and `life_status_since` through updateEntityProfile (113 passed). Deployed.

## Uniformity fix (2026-09-15, Sean: "why do only document-unbacked NPCs have it?")

The dropdown initially lived only in the entity profile editor — the editor path document-unbacked NPCs take. Sheet-backed NPCs/PCs edit through CharacterProfileEditor, which had no life status. Fixed across all three surfaces:
- **CharacterProfileEditor** (sheet-backed PCs/NPCs): Life status select + since-date with local draft state (date appears before any server call); commits through the audited setLifeStatus entity path, independent of the document-scoped PC profile save.
- **CharacterDocumentView hero**: Life status (since …) row for every character entry, fed from the entity profile — loadCanonicalEntry now fetches the entity profile alongside the sheet for document-backed characters.
- **Core**: claim_id optional on life-status writes (manual backfill from DM knowledge carries no anchor; detector confirmations stay anchored).
React 114 (sheet-backed Romulus flow: hero loads, editor opens, select+date → setLifeStatus). Live-verified on Romulus: character doc renders, Edit NPC page opens the editor, the six-option select present.

## Immortal added (2026-09-15, Sean: "several of the NPCs are straight up immortal")

`immortal` joined the enum (Core Literal, TS type, both editor selects, glossary). Semantics recorded in the glossary: immortal marks beings that cannot die — any death claim about them is a retcon question ("destroyed their form?"), never a status change. Detector behavior comes free from the existing guards: the proposal queue only surfaces entities with NO life status set, so an immortal marked once never receives death proposals afterward; dead-seat detection reads only `dead`. 114 React tests green; deployed; staged.
