---
id: TKT-0147
title: Phase 2 Stage 3 — Document/Entity alignment: sheets demote to evidence, identity lives on the record
status: done
priority: P2
milestone: trustworthy-librarian
depends_on: [TKT-0140, TKT-0143]
created: 2026-09-24
updated: 2026-09-28
---

# TKT-0147: Phase 2 Stage 3 — Document/Entity alignment

## Context

Sean's ruling (2026-09-24): **character sheets are a consequence of incomplete migration.** Imported `npcs/*.md` / `pcs/*.md` sheets currently act as three things at once — evidence (an imported Source), the entry's rendered page (the page matcher prefers sheet roots), and the identity's data store (race/sex/status parsed into a per-document PCProfile). The live symptom: Roccid's editor has no attribute dropdowns and no claim minting, because sheet-backed characters render and edit through the sheet path while the vocabulary selects and TKT-0143 minting live on the entity path. Two editors, two save paths, one of them outside canon machinery — a russian doll ADR-0015 was supposed to prevent.

Stage 3 of the Phase 2 Migration (TKT-0140's campaign): **align all Documents and Entities** — finish ADR-0015's separation. Identity data lives on the Entity (Attributes, now claim-backed). Rendering comes from the Entity's template and its authored Description. Imported documents — sheets included — are evidence, nothing more.

Live scope: 18 npc sheets + 4 pc sheets (22 sheet documents); 5 PCs + 48 NPCs in the library.

## The fix, in slices

### Slice 1 — Sheet identity migrates onto the record (anchored)
- Parse each sheet's identity fields (race, sex, status, player, aliases) and mint them as **anchored attribute claims**: subject = the entity, predicate = the field, evidence = the span in the sheet ("Race: Half-Elf" in `npcs/Roccid.md`). This is the 0143 mint with the anchor the backfill lacked — sheets give us spans, so Stage 3's claims are born anchored, not nudged.
- Sheet "Background / History" prose does NOT migrate — it is evidence for a future Description (descriptions are advisory polish, never required; the DM writes one when wanted).
- PCProfile stops being the identity source; the per-document profile store becomes read-only legacy.

### Slice 2 — The page matcher stops borrowing sheets (and everything imported)
- The `npcs/` / `pcs/` preferred roots retire from page matching; broader: **only authored `entities/` Descriptions render as an entry's page** — imported documents never do.
- Character-kind entries render the **character template from the Entity** (Attributes + claims + Dossier + authored description), the same templated presentation every other kind already uses; the entityTemplate's character exclusion lifts.
- Sheets appear where every Source appears: the Records evidence list with provenance.

### Slice 3 — One editor, one save path
- `CharacterProfileEditor` retires; all kinds edit through `EntityProfileEditor` (the vocabulary dropdowns, the minting, the life-status field — which already lives there).
- With a single save path, every attribute change on every character mints — Roccid's dropdowns arrive by convergence, not by duplication.

### Slice 4 — The audit catches up
- Qualified audit Q5 flips from "pending minting" to **computed** against attribute_claim_bindings (Stage 1's anchored claims + the backfill make the population real).
- Link audit's "wrong-page borrow" finding class empties by construction — nothing borrows anymore; the matcher rule retires with the class.

## Consequences (named before building)

- Every character page changes appearance (sheet layout → character template). The sheet's exact visual layout is lost as the default page — retrievable via the Records evidence view of the sheet document.
- The 22 sheet documents become read-only evidence; nothing about their text changes (source safety).
- Race/sex/status values that exist ONLY in sheet text (never in entity attributes) surface onto the record for the first time — some will be duplicates of existing claims (reconciliation may follow), some net-new canon.
- Undo story: every step is receipted (claims, bindings, matcher is code not data); the render change is a deploy, reversible.

## Out of scope

- Sheet-prose → description auto-drafting (the DM writes descriptions when wanted; the sheet stays reachable as evidence).
- Non-sheet imported page borrowing beyond matcher retirement (locations/lore docs are already evidence-only in practice; the matcher change covers them).
- Reconciliation of value conflicts between sheet-parsed fields and existing claims — surfaced, not auto-resolved.

## Validation evidence

(to record when built)

### DELIVERED 2026-09-24 — unified rendering, one editor, anchored sheet identity, background promotion

Sean's expanded rulings (2026-09-24): **all Documents render the same** (no backing-based splits); Nero shows his attributes; Roccid uses the same editor; sheet Backgrounds promote to descriptions via candidate promotion then stay editable; in a Seeded environment all Entities are treated the same by Kind. Delivered:
- **Character render branch REMOVED** — the characterDocument ternary is gone; every non-session, non-encounter document and every entity renders through StructuredEntryView. Sheets render like all evidence documents.
- **The unified template serves characters**: entityTemplate's pc/npc exclusion lifted; the hero field list gains Race/Sex/Player from the profile; life_status and aliases as before. Nero (unpaged npc) now shows attributes on his page.
- **Page matcher narrowed**: pc/npc preferred roots removed — sheets are never page candidates (locations transitional). Entity pages render the template from Attributes + claims; sheets appear as Sources evidence.
- **One editor**: CharacterProfileEditor's render path is unreachable (branch removed); Edit everywhere opens the entity profile editor with the vocabulary dropdowns and 0143 minting. Roccid edits with the same dropdowns as everyone.
- **Background promotion** (TKT-0146 flow): Write description on a character with a sheet source prefills the composer with the sheet's Background/History section — the :: candidate review then promotes it into an authored Description that is fully editable thereafter.
- **Migration 0071**: sheet identity fields minted as ANCHORED attribute claims (evidence spans into the sheet text — born anchored, unlike 0070's nudged backfill). Live: 12 anchored bindings (Roccid: status); 48 bindings total.
- **Records hood claims gained the mention context** (owner titles + mention-anchored clamps render under Records too, not only in the character Known-facts list — which itself retired with the branch).
- Tests: the five sheet/PC-editor tests replaced with unified equivalents (entity editor dropdowns for PCs, alias trimming through the one save path); Romulus/NPC-document tests rewritten to evidence-document expectations. 11 files / 79 tests green (the retired surfaces removed their tests); harness 8/8; deployed.

## Closed 2026-09-28

Delivered 2026-09-24: all Documents render the same (character branch removed); entityTemplate serves every Kind (Race/Sex/Player in the hero); the page matcher drops pc/npc roots (sheets are Sources evidence, never pages); one editor by Kind with dropdowns + minting; sheet Backgrounds prefill the composer for :: promotion; migration 0071 anchors sheet identity claims (12 anchored/48). Sheets remain visible as a migration consequence only through their evidence — the alignment is done.