---
id: TKT-0138
title: Orphaned claims review — a standing queue to assign owners to subject-less claims
status: backlog
priority: P2
milestone: trustworthy-librarian
depends_on: [TKT-0099]
created: 2026-09-21
updated: 2026-09-21
---

# TKT-0138: Orphaned claims review — a standing queue to assign owners to subject-less claims

## Context

Grouping Lore evidence by owning record (2026-09-21) exposed a population of claims with no `subject_entity_id` — they land in the "No owning record" group. Sean's read on the live data: **many belong somewhere obvious** (an entity that already exists), and **some don't** — history/lore claims that may legitimately have no owner, or belong to records that don't exist yet. Before the grouping, this residue was invisible; the identity review (TKT-0106) closed 91% claim coverage and this queue addresses the remainder. Per the standing productize rule, this is a permanent in-app review feature, not a one-time backfill.

## Scope when taken up

- **Core list endpoint**: subject-less claims (`subject_entity_id IS NULL`, non-superseded), each with assertion text, state, authority, sources, and **suggested owners** — deterministic suggestions from the existing co-mention / alias / word-index machinery (the link-audit and entity-lookup tooling), ranked; no suggestion is authoritative.
- **The bridge to Lore is the primary migration path** (user ruling 2026-09-21): the review is a list of orphaned claims that can be **checked and migrated into the Lore creation queue**. Checked claims become a seeded Lore queue item — the DM names the record they belong to (defaulting to the top suggested owner's name when one exists); the claims ride along as pre-loaded evidence in that item's working file, Consider-checked and ready to Link. Lore then handles both resolutions it already owns: create the new entity and take the claims under it, or match an existing entity via the link-target flow and Link to it. The orphans find their owner through the same reviewed door everything else uses.
- **Initial attribution write**: extend re-attribution to claims with no owner. Today `reattribute` conflates a NULL subject with "claim does not exist," and `move_claim_subject` compares `subject_entity_id = p_old_entity_id` (NULL never matches). Add the initial-attribution case (old owner NULL) through the same migration-owned function — receipted, reason required, provenance untouched; the claim's text/state/evidence never change, only ownership. Lore's Link path uses this for orphans the same way it uses re-attribution for owned claims.
- **Direct assign-to-record** stays available for the obvious cases (owner exists, no Lore ceremony needed): a suggested owner or searched record as the initial-attribution target.
- **"No owner needed" disposition**: some claims are ambient history/lore with no owning record. A receipted per-claim disposition (reason required, audited like candidate dispositions) that removes the claim from the review without inventing an entity — "missing source files never authorize automatic canonical deletion," and neither does a missing owner.
- **Tools-panel review queue** (link-audit pattern): rows show the claim (Truth State + authority chips, expandable text, source excerpt) with its suggested owners; actions = **Migrate checked to Lore queue** (primary) / **Assign to record** / **No owner needed** (reason required); re-runnable, so future unowned claims reappear — a standing review, not a batch.
- Per-item dispositions only: inspecting one claim never decides another; migration carries exactly the checked claims.
- Optional later (out of scope unless ruled in): the AI Promotion Assistant suggesting owners on this queue (TKT-0137 seam 4 — suggest subjects).

## Open at ticket time — the obvious-home path (user ruling 2026-09-21: defer)

The Lore bridge is right for orphans with NO obvious home. Orphans WITH an obvious home need their own solution — maybe still Lore (workspace built up to accommodate seeded resolution against existing records), maybe the Library's built-in entry editor (the page that already owns the record, per ADR-0016 every-page-editable). The tension: two editing homes (Lore workspace vs Library entry editors) and where an obvious-home attribution belongs. Decide when this ticket is worked; do not pre-commit.

## Out of scope

- Auto-assignment or bulk approval — every attribution is an explicit DM decision.
- Creating entities directly from this queue — creation goes through Lore (that is the bridge); the queue itself links and queues, it doesn't author.
- Changing claim text, state, or evidence — ownership only.

## Validation evidence

(to record when built)
