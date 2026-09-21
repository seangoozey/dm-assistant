---
id: TKT-0129
title: Template field enumerations and template editors — a home for controlled values
status: done
priority: P2
milestone: shared-campaign-knowledge
depends_on: [TKT-0121]
created: 2026-09-19
updated: 2026-09-19
---

# TKT-0129: Template field enumerations and template editors

## Context (Sean, 2026-09-19, reviewing entry pages)

"The parent location shouldn't be arbitrary text. Same with Status and Location Type. These template enumerations need a home with an editor. The templates themselves might need an editor."

Today `location_type`, `status`, and `parent_location` are free-text fields on entity profiles — arbitrary strings render on pages, nothing constrains vocabulary, and parent_location is text rather than a reference to an actual location entity.

## Scope

- **Controlled vocabularies for template enumerations**, stored in Campaign Core (receipted edits, like prompt overrides): the allowed values for location_type and status (per entity kind where kinds diverge). Profile editors offer the enumeration as a select with an "add value" affordance that files the receipt; free text is no longer the input path.
- **parent_location becomes a reference, not text**: the editor selects an existing location entity (search-driven, exact-name stored, resolved for the breadcrumb chain). Existing text values migrate by exact-name match, with a review queue for non-matching values rather than silent drops.
- **A template field editor** in Settings (or a Templates surface): manage enumeration values per field/kind — add, retire (retired values stop being offered but keep rendering), receipted history.
- **Template editor (exploration)**: Sean flagged that the templates themselves might need an editor. Scope as a design question first: what varies per kind (section order, field choice, hero fields) and whether editing is configuration (Core-stored template definitions) or code. Do not build a template editor before that design is agreed.

## Out of scope

- Changing what the templates render today (this ticket is about where the VALUES come from).

## Validation evidence

(to record when built)

## Classification analysis (2026-09-19, Sean's question)

"What classification can Roles, Status, Race, Sex and any other system enumerations fall under? or is Roles just too different from the others to justify grouping them?"

**Roles is too different — don't group it.** Roles are not a field on an entity: they are RELATIONS between entities (a named seat binding a member to a faction, with holders and ★ leadership). Role names are an open, per-faction vocabulary shaped by audited seating decisions — that machinery already exists (migrations 0055/0056) and belongs with membership, not with field enumerations.

The remaining fields split into two genuine groups:

1. **Intrinsic attributes** — Race, Sex, Location type: (near-)closed vocabularies describing what an entity IS. Editor = a simple receipted list per field; adding a value is rare and permanent-ish. These fit one shared "attribute vocabulary" home.
2. **States** — Status (active/disbanded/…) and Life status (already an enum): time-aware values that CHANGE, each change ideally carrying its since-date and, where possible, a decision receipt. Their editor is closer to the life-status pattern (value + since + anchor) than to a plain vocabulary list — the vocabulary is small and stable, but the assignment is an event.

Proposed shape for the editor home: one "Template vocabularies" surface managing group 1, with group 2 treated as state assignments (status gains the life-status treatment), and roles staying where they are.

## Validation evidence

Delivered 2026-09-19, deployed, live-verified.

- **Core** (migration 0063 + `template_vocabularies.py`): four vocabularies (location_type, status, race, sex) with seeded values and receipted add/retire (`vocabulary_receipts` audit table). Retired values stop being offered but keep rendering where already set. Roles are explicitly NOT a vocabulary (the classification ruling). `GET/POST /template-vocabularies/{vocabulary}` (DM-gated; 422 on unknown vocabulary/action).
- **Settings editor**: Settings → Template vocabularies — per-vocabulary chip panels (offered/retired counts, retire ×, add input with receipt). Roles stay with the roster, stated in the explainer.
- **Profile editors on vocabularies**: Location type / Status / Race / Sex are selects populated from the vocabularies (an out-of-vocabulary current value still shows, labeled); **parent_location is an entity reference** — a select over location entities (legacy unmatched values render with a "(no matching entry)" flag). Free text is no longer the input path.
- Validation: Core tests (seeds+overrides, receipted add/retire, roles rejected, API DM-only/round-trip) 5 local + docker 5/5 (migration 0063, durability); React 135/135 incl. the profile test now driving vocabulary selects and entity-reference parent selection. Live: location_type serves 17 values post-deploy.

### Post-delivery (2026-09-19): unretire affordance

Retired chips now carry a restore button (↩) — an "add" on an existing retired value flips it back to offered (Core already supported this via the receipted upsert). The toast distinguishes restore ("restored — offered again") from a genuine add.
