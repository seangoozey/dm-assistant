---
id: TKT-0029
title: Establish minimal entity types, intent ownership, and optional tags
status: ready
priority: P1
milestone: trustworthy-librarian
depends_on: [TKT-0024, TKT-0027]
created: 2026-08-02
updated: 2026-08-02
---

# TKT-0029: Establish Minimal Entity Types, Intent Ownership, and Optional Tags

## Outcome

Replace unrestricted, overlapping entity classification with a deliberately small enforced type vocabulary; distinguish player, GM, and in-world intent without predicting player behavior; and provide an optional in-app tag expansion control for useful secondary descriptors.

## Context

The current database accepts arbitrary text in `entities.entity_type`, while the provisional domain model mixes broad types, narrow roles, artifacts, and concepts. That forces the DM to guess among overlapping labels and permits inconsistent classification over time.

The first live canonical entity is a location. Review of subsequent planning material also exposed a separate modeling need:

- `player_intent` records what a player currently wants to pursue, without promising a future PC action;
- `gm_intent` records a DM-only direction used to guide campaign development;
- an NPC or faction intention remains an in-world intention whose outcome is not established merely because it is planned.

Secondary descriptors should not multiply primary types. For example, a deity that acts as a character should remain discoverable in an ordinary character/NPC lookup while an optional `deity` tag enables narrower retrieval.

The legacy use of “Cosmology” was broader than metaphysical concepts: it served as the low-friction worldbuilding bucket for historical events, cosmological events, mythical events, and related setting lore. The replacement must preserve that convenience without pretending all such subjects are cosmological concepts.

Read `docs/product/invariants.md`, `docs/product/truth-state-authority.md`, `docs/architecture/domain-model.md`, `docs/architecture/campaign-core-schema.md`, `docs/architecture/workflows.md`, TKT-0022, TKT-0023, TKT-0024, and TKT-0027. Because this changes a durable domain decision, read `docs/decisions/README.md` and add an ADR.

## Design constraints

- Optimize for the fewest primary types that cover demonstrated campaign needs without overlap.
- Prefer broad, mutually exclusive types. The initial set should start from `character`, `location`, `group`, `object`, and `worldbuilding`; adding another type requires a concrete live use case that cannot fit one of these without ambiguity.
- `worldbuilding` is the deliberate home for stable setting subjects that are not characters, locations, groups, or objects, including historical events, mythical events, cosmological events, eras, legends, and abstract setting concepts. It preserves the low-friction role formerly served by “Cosmology.”
- `worldbuilding` is not an unrestricted `other` bucket: operational records, sources, sessions, encounters, proposals, and campaign-development notes keep their own record kinds.
- Do not provide `other`, arbitrary free-text types, or silent fallback classification. Material that does not fit remains unclassified evidence until the vocabulary is deliberately amended.
- Sessions, encounters, source documents, proposals, and planning notes remain their own record kinds unless a demonstrated identity requirement justifies treating one as an entity.
- Tags are optional, non-exclusive retrieval and presentation facets—not substitutes for primary type or truth state. Do not require tags that add no useful distinction.
- Tags may overlap when the overlap is meaningful. A character can carry `deity`; character control/role must still allow ordinary PC or NPC lookup without requiring the user to duplicate type decisions.
- Worldbuilding tags such as `historical`, `mythical`, or `cosmological` are optional and should exist only when they materially improve filtering. A user must be able to save a worldbuilding subject without choosing one.
- Tag names are normalized and unique case-insensitively. Renames and aliases preserve stable tag identity and existing entity links.
- Intent ownership is explicit and non-overlapping: `player_intent`, `gm_intent`, and in-world entity intent. Do not introduce separate `player_declared_intent`; the declaration and its provenance are evidence for `player_intent`.
- `player_intent` is evidence of the player's current plan or interest, not a guarantee that the PC will act.
- `gm_intent` is DM-only campaign-development guidance. It describes desired pressures, opportunities, themes, or directions and cannot establish a PC's future action.
- In-world NPC or faction intent remains true only as an intention and never establishes its intended outcome.

## Scope

- Audit demonstrated live and fixture classification needs and record why each retained primary type is necessary.
- Add an ADR defining the minimal type vocabulary, the amendment rule, intent ownership, and the boundary between types, roles, tags, claims, and other record kinds.
- Expand the domain model, schema documentation, truth-state guidance, workflows, and UI documentation with concise decision rules and representative examples.
- Replace unrestricted entity-type input with a Campaign Core-enforced vocabulary and a safe migration for existing entities and immutable proposal history.
- Model character role/control so PC and NPC lookup is deterministic and a character tagged `deity` remains included in the appropriate ordinary lookup.
- Preserve legacy Cosmology material through a documented mapping to `worldbuilding`, retaining original source classification and provenance rather than rewriting source files.
- Add normalized, stable entity tags and auditable tag assignment/removal through exact versioned proposals and canonical change sets.
- Add explicit intent ownership/purpose at the appropriate typed claim or planning boundary without weakening existing state, authority, visibility, time, or PC-agency rules.
- Update proposal comparison and approval so type, character role, intent ownership, and tag changes are completely visible before approval.
- Add a compact app control that keeps tags out of the way by default and expands on demand. The expanded control must autocomplete existing tags, allow an explicit new-tag action, prevent case-only duplicates, and permit removal before proposal submission.
- Make type, character role, intent ownership, and tags available to grounded retrieval filters without treating a tag as canonical evidence for unrelated claims.
- Add sanitized backend, migration, retrieval, and React tests for the full vertical slice.

## Out of scope

- Automatically tagging every imported source or candidate.
- Creating an exhaustive ontology or hierarchy of tag categories.
- Inferring player intent from predicted behavior, PC prose, or GM plans.
- Treating `gm_intent` as authority to control a PC.
- Reclassifying source-document types as entity types.
- Promoting additional live candidates merely to exercise the new model.
- Redesigning campaign calendars or date storage. Dates are structured temporal data rather than tags; TKT-0030 owns the audit-time/campaign-time separation and legacy negative-year normalization.

## Acceptance criteria

- [ ] An ADR defines a small mutually exclusive primary type vocabulary, with no `other` or arbitrary free-text escape hatch and an explicit process for adding a demonstrated new type.
- [ ] Documentation clearly distinguishes entity type, character role/control, optional tags, claim state, authority, visibility, and intent ownership using concrete examples.
- [ ] Documentation explains that legacy “Cosmology” was a worldbuilding collection spanning historical, mythical, cosmological, and abstract lore—not a narrow concept type.
- [ ] Campaign Core rejects unsupported primary types at proposal validation and canonical application boundaries.
- [ ] Existing canonical entities and immutable receipts remain valid through a documented, tested migration and rollback path.
- [ ] `player_intent`, `gm_intent`, and in-world entity intent have deterministic state/authority/visibility mappings and cannot establish future PC behavior or intended outcomes.
- [ ] Ordinary PC/NPC or character lookup includes correctly controlled characters regardless of secondary tags; a `deity` tag narrows results without excluding the entity from ordinary lookup.
- [ ] Historical, mythical, and cosmological events can all be represented as `worldbuilding` without requiring a subtype or tag, while optional tags can narrow retrieval.
- [ ] Tags have stable identity, normalized case-insensitive uniqueness, aliases/renames where needed, and auditable assignment/removal through exact approved change sets.
- [ ] The app presents a short primary-type choice with plain-language guidance and no overlapping options.
- [ ] Tags remain collapsed or unobtrusive by default; an explicit expansion action supports autocomplete, explicit creation, duplicate prevention, and removal.
- [ ] Proposal comparison shows the complete before/after type, role, intent, and tag state before approval.
- [ ] Grounded retrieval can filter by the new dimensions without promoting tags or planning records into unrelated canonical facts.
- [ ] Sanitized tests cover ambiguity rejection, every retained primary type, legacy Cosmology migration, historical/mythical/cosmological worldbuilding, deity-as-character retrieval, player-versus-GM intent, PC-agency safeguards, tag normalization, tag expansion UI, exact approval scope, migration, and rollback.
- [ ] Relevant repository validation and isolated PostgreSQL integration tests pass, with validation evidence recorded before the ticket moves to done.

## Validation plan

- Enumerate every proposed primary type against sanitized examples and at least one audited live structural case; remove any type whose cases can be represented unambiguously by another retained type plus an optional tag or role.
- Exercise migration against a disposable restore of the current campaign database before applying it to development data.
- Verify the existing location entity, claim, receipt, and source provenance survive unchanged.
- Verify representative legacy Cosmology structures map to `worldbuilding` without requiring arbitrary subtyping or losing their original paths and provenance.
- Verify unsupported types and case-only duplicate tags fail atomically without receipts or partial mutations.
- Verify `player_intent` and `gm_intent` never set `predicts_subject_action` for a PC and never become observed outcomes without separate real-play evidence.
- Verify default app use requires no tag choice and that expanding the tag control does not approve or mutate anything until an exact proposal is approved and applied.

## Follow-up work

- Do not silently expand this ticket into automated tagging or AI-assisted classification. Create separate tickets after the minimal human-controlled model is proven.
- TKT-0030 follows with calendar-neutral campaign chronology after this ticket settles entity and intent boundaries.
