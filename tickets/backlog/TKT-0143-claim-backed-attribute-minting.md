---
id: TKT-0143
title: Claim-backed attribute minting — the dropdown mints dated claims behind the fast path
status: backlog
priority: P2
milestone: trustworthy-librarian
depends_on: [TKT-0141]
created: 2026-09-21
updated: 2026-09-21
---

# TKT-0143: Claim-backed attribute minting — the dropdown mints dated claims behind the fast path

## Context

Ruled during the Qualified Entity work (2026-09-21): **attributes are claim-backed and part of the CTS.** Every attribute value becomes the projection of a dated backing claim; the profile editor stays a one-click fast path that MINTS the claim behind the dropdown (the life_status pattern generalized — proven in production with the death detector). This is the mechanism TKT-0139's Q5 audits and TKT-0137's attribute promotion waits on. Own ticket per Sean's ruling ("its own ticket is fine").

## Scope when taken up

- **Mint on write**: every profile-editor attribute change mints a claim — subject = the entity, the structured assignment as its content, Truth State Established by default, dated (recorded_at = the change), provenance-free-but-marked (unanchored DM knowledge). Receipted like all profile writes.
- **Anchoring, optional and attachable later**: an attribute claim may anchor to an evidence span (existing claim evidence machinery); unanchored-but-dated qualifies per the standard — anchoring is the nudge (surfaced as an advisory count), never the gate.
- **Supersession through the presumed-retcon rule** (TKT-0141): changing a value supersedes the prior backing claim — with no conflicting observed claims it auto-accepts as presumed retcon with an editable reason (the Romulus case: High Elf 9/21 → Orc 10/23, transformation ≠ retcon, prior period queryable).
- **The field becomes a projection**: reads resolve the current value from the winning backing claim (with a projection/cache so page renders don't pay a supersession query per field).
- **Migration**: existing populated attributes backfill as unanchored-but-dated claims (the 0123 killer-vs-killed playbook — mark, nudge later; never block).
- **API/UI shape**: the editor UX is unchanged (one click); a Records-view affordance shows the backing claim (date, anchor, supersession history) per attribute.

## Out of scope

- AI attribute suggestions (TKT-0137 rides on this, separately).
- The Qualified audit itself (TKT-0139's endpoint reports Q5 pending until this lands).
- Auto-anchoring or auto-refining reasons — the DM anchors and refines.

## Validation evidence

(to record when built)

### DELIVERED 2026-09-24 — minting + presumed retcon + backfill live

- **Migration 0069**: `apply_attribute_claim(entity, field, value, key)` — the migration-owned mint: creates the dated claim (subject=entity, predicate=field, assertion "{field}: {value}", Established/explicit_lore, confidence 1.0, dm_only, unanchored), supersedes the prior binding's claim through the **presumed-retcon rule** (auto-accept with reason "presumed retcon" when no observed claim on the record names the field; an opposing observed claim BLOCKS with a readable error — observed authority stands), updates the binding, all idempotent per key (`attribute_claim_bindings` + `attribute_claim_receipts`). The `::`-era boundary rule holds — no canonical write outside a migration-owned function.
- **Migration 0070 (backfill)**: every populated attribute across 19 profiles became unanchored-but-dated claims — 36 bindings minted live on first deploy. The Romulus case now exists: his race claim is dated and his next change will supersede with a presumed-retcon receipt.
- **Adapter**: the profile editor's update path mints on change — each of the six minted fields (status, location_type, race, sex, parent_location, base_location) whose value changed calls the function with key `{save-key}:mint:{field}`; unchanged fields mint nothing; aliases/summary/life_status keep their dedicated machinery.
- **Live effect on the campaign (the Q5 flip)**: the audit moved **53 → 63 of 120 qualified** (57 unqualified) — ten zero-claim entities now own their attribute claims via the backfill alone, no other change. Q5's "pending minting" report can now flip to computed on the next audit update.
- **Evidence**: new `tests/test_attribute_claims_postgres.py` 2/2 in the harness (mint → change → presumed retcon with supersession reason asserted → idempotent replay; observed opposition blocks); promotion harness still 8/8; unit suite 514 passed; deployed live.

Remaining (follow-ups): flip the Qualified audit's Q5 from pending to computed against bindings; the Records-view per-attribute affordance (date, anchor, history); anchor attachment lane; presumed-retcon reason editing surface (TKT-0141's UI half).
