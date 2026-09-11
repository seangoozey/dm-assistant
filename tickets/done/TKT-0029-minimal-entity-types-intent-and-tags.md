---
id: TKT-0029
title: Establish the referenceable-record foundation, minimal entity kinds, and optional tags
status: done
priority: P1
milestone: trustworthy-librarian
depends_on: [TKT-0024, TKT-0027]
created: 2026-08-02
updated: 2026-08-02
---

# TKT-0029: Establish the Referenceable-Record Foundation, Minimal Entity Kinds, and Optional Tags

## Outcome

Introduce a stable identity and reference model shared by referenceable records; replace unrestricted entity classification with a deliberately small, enforced kind vocabulary; preserve the PC/NPC agency boundary; and provide an optional in-app tag expansion control for secondary descriptors.

## Context

The current database accepts arbitrary text in `entities.entity_type`, while the provisional domain model mixes broad types, narrow roles, artifacts, and concepts. That forces the DM to guess among overlapping labels and permits inconsistent classification over time.

The first live canonical entity is a location. Review of subsequent planning material also exposed a separate plan model, now bounded as TKT-0031: `campaign_direction` for DM development guidance, `in_world_plan` owned by an NPC or faction, and `player_plan` for attributed nonbinding player communication. Plans cannot establish their intended outcomes or predict PC behavior.

Secondary descriptors should not multiply primary types. For example, a deity controlled by the DM remains an NPC and must be discoverable in an ordinary NPC lookup, while an optional `deity` tag enables narrower retrieval.

The legacy use of “Cosmology” was broader than metaphysical concepts: it served as the low-friction worldbuilding bucket for historical events, cosmological events, mythical events, and related setting lore. The replacement must preserve that convenience without pretending all such subjects are cosmological concepts.

Named in-world plans such as a villain's long-running scheme also need stable identity, provenance, relationships, lifecycle, and cross-document references. They are first-class `plan` records, not entity types and not `campaign_direction`. TKT-0029 supplies the shared identity and kind foundation; TKT-0031 implements the plan family.

Read `docs/product/invariants.md`, `docs/product/truth-state-authority.md`, `docs/architecture/domain-model.md`, `docs/architecture/campaign-core-schema.md`, `docs/architecture/workflows.md`, TKT-0022, TKT-0023, TKT-0024, and TKT-0027. Because this changes a durable domain decision, read `docs/decisions/README.md` and add an ADR.

## Design constraints

- Add a thin common `records` identity table. Every referenceable record has one stable UUID and controlled `record_type`; each family table, such as `entities`, uses that UUID as its primary and foreign key. Claims, relationships, evidence links, and cross-record references use real foreign keys to `records.id`.
- Do not use unchecked `record_type` plus arbitrary UUID polymorphism, and do not flatten family data into a generic JSON table.
- Separate the stable record family from its namespaced family-specific kind: `record_type`, `entity_kind`, `plan_kind`, `artifact_kind`, and `rules_kind` have distinct vocabularies.
- Registry data owns stable kind identity, versioned keys, labels, documentation, aliases, lifecycle status, and replacement metadata. Versioned application code and migrations own required fields, validation, storage behavior, and exporters.
- Adding a behavior-bearing kind is a reviewed development change. The app may show kind guidance and allow tag creation, but it does not provide in-app schema or kind construction.
- Renaming preserves stable kind identity and old keys as aliases. Merge and split are replacement/deprecation plus per-record reviewed reclassification; neither silently changes record identity. Historical receipts retain the exact reviewed kind key and version.
- Unknown or retired kinds fail closed into review. There is no `other`, arbitrary free-text kind, or silent fallback to `worldbuilding`.
- The initial entity kinds are `npc`, `pc`, `location`, `faction`, `item`, `event`, `worldbuilding`, and `rules_element`.
- `worldbuilding` covers stable setting subjects such as eras, legends, cosmological structures, and abstract concepts. It is not a bucket for plans, operational records, or unsupported kinds.
- `rules_element` identifies reusable game mechanics. Its initial `rules_kind` vocabulary is `spell`, `feat`, and `ability`; structured mechanics and exports are deferred to TKT-0032.
- `pc` and `npc` are permanent, mutually exclusive agency categories. A PC is played only by its player and an NPC is controlled only by the DM; the system must never infer or predict a PC action.
- Artifacts are deliverables derived from canonical records. Original handouts and character sheets are source evidence; generated handouts, sheets, cards, and Foundry packages are derived artifacts. The item or rules element described by an artifact remains its own entity.
- A campaign session is a future domain record and is distinct from existing internal `workflow_sessions`. Encounter and campaign-session implementation remains deferred until their models are discussed.
- Tags are optional, non-exclusive retrieval facets, not truth, kind, date, or source classification. The initial controlled seed is `history`, `mythology`, `cosmology`, `world`, `continent`, `country`, `region`, `settlement`, `monster`, `deity`, `religion`, and `political`.
- Do not seed `item`, `handout`, `spell`, `feat`, `ability`, dates, or truth states as tags. A disputed classification is a claim, not a tag.
- Tags have stable identity and case-insensitive normalized uniqueness. An NPC tagged `deity` remains discoverable in ordinary NPC lookup.
- Preserve the PC, player-plan, and campaign-direction knowledge boundary in the ADR and entity behavior. First-class plan storage and lifecycle are implemented by TKT-0031.

## Scope

- Add the common `records` identity table, subtype integrity, and cross-record foreign-key model.
- Add the namespaced kind registry and ADR, including amendment, alias, deprecation, replacement, merge, split, and reviewed reclassification rules.
- Replace free-text `entities.entity_type` with the eight controlled entity kinds and safely migrate current canonical entities, proposals, receipts, and retrieval behavior.
- Document each entity kind with purpose, inclusion rule, exclusions, examples, counterexamples, and applicable relationships.
- Add normalized stable tags and auditable tag assignment/removal through exact versioned proposals and canonical change sets.
- Seed only the approved initial tag vocabulary, while allowing explicit case-normalized tag creation from the expanded tag control.
- Update proposal comparison and approval so record type, entity kind/version, and tags are completely visible before approval.
- Add compact entity-kind guidance and a collapsed-by-default tag control with autocomplete, explicit creation, duplicate prevention, and removal before proposal submission.
- Add entity-kind and tag retrieval filters without treating tags as canonical evidence for unrelated claims.
- Preserve legacy Cosmology as source collection metadata and provenance; reviewed records may become `event` or `worldbuilding` entities without rewriting source files.
- Add migration, rollback, backend, retrieval, and React tests for this vertical slice.

## Out of scope

- First-class plan storage, plan lifecycle, and plan projections (TKT-0031).
- Structured rules mechanics and artifact export profiles (TKT-0032).
- In-app schema or kind construction. Behavior-bearing kinds are changed in reviewed code and migrations.
- Campaign encounter and campaign-session record implementation; `workflow_sessions` remains an internal workflow concept.
- Automatically tagging every imported source or candidate.
- Creating an exhaustive ontology or hierarchy of tag categories.
- Treating a player statement, predicted behavior, PC prose, or GM plan as knowable `pc_intent` or `player_intent`.
- Treating `campaign_direction` as authority to control a PC.
- Reclassifying source-document types as entity types.
- Promoting additional live candidates merely to exercise the new model.
- Redesigning campaign calendars or date storage. Dates are structured temporal data rather than tags; TKT-0030 owns the audit-time/campaign-time separation and legacy negative-year normalization.
- Automatically reclassifying all legacy records when a kind is renamed, merged, split, or deprecated.

## Acceptance criteria

- [x] A documented `records` identity table and subtype model gives every referenceable record one stable UUID and enforces references with real foreign keys.
- [x] The implementation neither uses unchecked polymorphic UUID references nor flattens family-specific data into generic JSON.
- [x] An ADR defines record-family/kind boundaries, registry-versus-code ownership, the eight entity kinds, kind-evolution rules, artifact/source boundaries, and PC/NPC agency invariants.
- [x] Kind definitions have stable identity, versioned keys, point-of-use documentation, aliases, and auditable active/deprecated/replacement states.
- [x] Rename, deprecation, merge, split, and reclassification preserve record IDs, source evidence, proposal coordinates, receipts, and historical kind/version values.
- [x] Campaign Core rejects unsupported entity kinds at proposal validation and canonical application boundaries; there is no `other`, free-text, or silent fallback kind.
- [x] Existing entities and immutable receipts remain valid through a documented, tested migration and rollback path, including migration away from any artifact `other` value.
- [x] The controlled entity vocabulary is exactly `npc`, `pc`, `location`, `faction`, `item`, `event`, `worldbuilding`, and `rules_element`.
- [x] PC and NPC remain permanent, mutually exclusive agency kinds; the system does not predict PC behavior.
- [x] Documentation explains the boundaries among kind, tag, claim/truth state, source evidence, and derived artifact, including legacy Cosmology examples.
- [x] The initial tag seed is exactly the approved twelve tags, with normalized case-insensitive identity and auditable assignment/removal.
- [x] An NPC tagged `deity` remains in ordinary NPC lookup; disputed deity status must be represented as a claim rather than a tag.
- [x] The app presents concise entity-kind guidance and no arbitrary kind creation.
- [x] Tags stay collapsed by default; expansion supports autocomplete, explicit creation, case-only duplicate prevention, and removal before proposal submission.
- [x] Proposal comparison shows the complete before/after record type, entity kind/version, and tag state before approval.
- [x] Grounded retrieval filters by entity kind and tags without treating tags as canonical evidence.
- [x] Sanitized tests cover all entity kinds, unsupported-kind rejection, registry evolution, stable-ID reclassification, legacy Cosmology provenance, deity-as-NPC retrieval, tag normalization/UI, exact approval scope, migration, and rollback.
- [x] Relevant repository validation and isolated PostgreSQL integration tests pass, with evidence recorded before the ticket moves to done.

## Validation plan

- Exercise kind rename, deprecation, merge, split, and record reclassification; verify stable record IDs and immutable historical receipts remain unchanged and ambiguous cases enter review.
- Enumerate each entity kind against sanitized examples and audited live structures; document why it cannot be replaced by another kind plus a tag.
- Exercise migration and rollback against a disposable restore before applying either to development data.
- Verify the existing location entity, claims, receipt, and source provenance survive unchanged.
- Verify legacy Cosmology structures can resolve to `event` or `worldbuilding` without arbitrary fallback or loss of original path and collection provenance.
- Verify unsupported kinds and case-only duplicate tags fail atomically without receipts or partial mutations.
- Verify default app use requires no tag choice and expanding the tag control does not mutate anything until an exact proposal is approved and applied.

## Follow-up work

- Do not silently expand this ticket into automated tagging or AI-assisted classification. Create separate tickets after the minimal human-controlled model is proven.
- TKT-0030 follows with calendar-neutral campaign chronology.
- TKT-0031 implements first-class plans and their knowledge/lifecycle boundaries.
- TKT-0032 implements structured rules elements and derived artifact export profiles.

## Implementation notes

### 2026-08-02 first vertical slice

- Added accepted ADR-0005 and updated the domain, schema, and truth-state documentation.
- Added migration 0006 with the thin `records` table, namespaced stable kind definitions and versions, controlled entity-kind resolution, legacy unsupported-kind review, tag identity/history, entity/artifact record registration, and record-level foreign keys for claims and relationships.
- Kept ambiguous legacy `entity_type` values attached to their stable entities and opened review rather than guessing a replacement. New canonical writes fail closed unless their exact entity kind is active.
- Added typed entity kinds and normalized tags to candidate proposals. Proposal hashes and comparison now include `record_type`, `entity_kind`, `entity_kind_version`, and complete tag state.
- Added read-only taxonomy metadata and entity-kind/tag retrieval filters.
- Replaced the free-text entity-type app field with a documented select and added a collapsed optional tag control with existing-tag autocomplete, explicit tag creation, duplicate prevention, and removal before submission.

Remaining before done: none.

### 2026-08-02 completion slice

- Added exact DM-only entity metadata proposals for kind reclassification and full tag replacement, including immutable before/after comparison, exact approval, stale rejection, atomic application, receipts, retained tag-removal history, and stable record identity.
- Added migration 0007 and a dispatcher that keeps `/change-sets/{change_set_id}/apply` as the only canonical HTTP mutation while preventing metadata mutations from being mixed with other mutation kinds.
- Enforced permanent PC/NPC agency kinds during proposal construction and canonical application.
- Added immutable kind-evolution events and source/target membership for rename, deprecation, replacement, merge, and split migrations. Executable tests preserve stable kind/entity IDs and historical proposal coordinates.
- Completed a logical dump/restore rehearsal from the current development database. The disposable restore advanced from 0005 to 0007, retained its one `location` entity, created exactly one `records` identity, produced no unsupported-kind review, and left the original database at 0005 with the same entity count.
- Removed the disposable restore, temporary dump, and isolated test container; the original named development volume remains unchanged.

Validation completed for this slice:

- `ruff check --no-cache src tests`
- `mypy --cache-dir E:\starfall\.mypy-tkt29 src`
- Campaign Core isolated tests: 115 passed, 23 skipped without PostgreSQL.
- Campaign Core full disposable PostgreSQL suite: 137 passed, 1 skipped.
- React strict typecheck passed.
- React/Vitest: 18 passed.
- Windmill raw-app production bundle passed.
- Retrieval acceptance corpus: 38 cases validated.
- Full deterministic repository validation passed.
