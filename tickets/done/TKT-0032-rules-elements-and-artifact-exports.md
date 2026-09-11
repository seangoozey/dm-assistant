---
id: TKT-0032
title: Add structured rules elements and derived artifact export profiles
status: done
priority: P2
milestone: trustworthy-librarian
depends_on: [TKT-0029]
created: 2026-08-02
updated: 2026-08-03
---

# TKT-0032: Add Structured Rules Elements and Derived Artifact Export Profiles

## Outcome

Represent reusable spells, feats, and abilities as canonical rules-element entities, then generate deterministic deliverables from those entities without confusing source evidence, canonical identity, and derived artifacts.

## Model

- The entity kind is `rules_element`; its initial `rules_kind` values are `spell`, `feat`, and `ability`.
- An item remains an `item` entity even when a Foundry item document or printable card is generated from it.
- Original handouts and character sheets are source evidence. Generated handouts, sheets, cards, and import packages are derived artifacts.
- Artifact records identify a deliverable, its export profile/version, source record/version, generation inputs, checksum, and reproducibility status.
- Registry metadata documents kinds and compatibility; reviewed code owns mechanics validation and exporter behavior.

## Scope

- Define the minimum structured mechanics shared by demonstrated spells, feats, and abilities, with kind-specific extensions only where necessary.
- Add proposal, approval, versioning, and retrieval behavior for rules elements.
- Define versioned export profiles and implement one narrow end-to-end export proof selected from demonstrated needs.
- Preserve a clear link from each artifact to its canonical source record and exact source version.
- Replace or deprecate the current artifact `other` escape hatch without invalidating historical receipts.
- Document authoring and export boundaries, migration, rollback, and extension rules.
- Add sanitized backend, exporter, and UI tests.

## Out of scope

- Treating an export file as the canonical item or rules element.
- In-app schema or exporter construction.
- Exhaustive modeling of every game-system mechanic before a demonstrated use case exists.
- Full Foundry integration unless it is separately scoped after the first export proof.
- Automated rules design or balance judgment.

## Acceptance criteria

- [x] `spell`, `feat`, and `ability` are accepted only as namespaced `rules_kind` values under a `rules_element` entity.
- [x] Canonical rules-element identity and version history survive regeneration of any artifact.
- [x] Source evidence, canonical records, and derived artifacts are visibly and structurally distinct.
- [x] At least one versioned export profile produces a deterministic artifact from an approved canonical record.
- [x] Artifact provenance records the exact source record/version, exporter/profile version, generation inputs, and checksum.
- [x] Unsupported mechanics or export profiles fail into review rather than arbitrary JSON, free-text kinds, or `other`.
- [x] Historical artifact receipts remain interpretable through the migration away from `other`.
- [x] Migration, rollback, backend, exporter, and UI tests pass with validation evidence recorded.

## Implementation

- Added `domain.rules_elements` with `RulesKind` (`spell`/`feat`/`ability`), `RulesElementMechanics` (validates per-kind structure via `SpellMechanics`/`FeatMechanics`), and `render_markdown_card` (the deterministic versioned `markdown-card/1` export profile).
- Migration `0010_rules_elements.sql` adds the `rules_element_mechanics` table (entity-keyed, kind-validated, immutable-before-delete), the `rules_card` artifact kind, the `markdown_card` export profile under a widened `export_profile` namespace, an `entity_id` column on `artifact_inputs` for rules-element provenance, an `export_profile_kind_id` on `derived_artifacts`, and a change-set trigger (`apply_created_rules_element_mechanics`) that persists mechanics when a rules-element entity is applied. The deprecated `other` artifact kind is retained, not dropped.
- Added `application.artifact_exports` (`ArtifactExportService`) that reads a canonical rules element + mechanics, renders the card, and stores a `derived_artifact` with full provenance. Regeneration under the same profile version is idempotent on content hash. Added `adapters.postgres.artifact_exports` for the persistence path.
- Extended `CreateEntityDecision` to require and validate `rules_element_mechanics` for `rules_element` entities and reject it for any other kind. The postgres candidate-proposal path threads mechanics into the proposal payload so the trigger persists them on application.
- Added `POST /entities/{entity_id}/rules-card` export endpoint to the Campaign Core API.
- Updated the schema, domain-model, and taxonomy documentation.

## Validation

- 17 domain unit tests cover kind validation, mechanics-shape validation per kind, mismatched-kind rejection, unknown-field rejection, level bounds, cantrip rendering, feat/ability mechanics, card content, and profile determinism.
- The migration structural test asserts `0010` adds the mechanics table, the rules_card kind, the export_profile namespace, the entity_id input column, and the mechanics-persistence trigger, and that no destructive type drops occur.
- Full non-postgres suite passes: ruff clean, strict mypy clean over 54 source files, all Python tests with environment-dependent skips.
- Full repository validation passed: React tests, strict TypeScript, Windmill raw-app build, infrastructure policy checks, and all 38 retrieval fixtures.
- **PostgreSQL integration tests passed against a real migrated database.** Migration `0010` applied transactionally on top of `0001`–`0009`. A dedicated integration test (`test_rules_elements_postgres.py`) proved the complete chain end-to-end: a rules-element entity created through the candidate-proposal path with mechanics, mechanics persisted by the change-set trigger, Markdown-card export producing a deterministic `rules_card` artifact with provenance, and a second export returning the same artifact as an idempotent replay. Six existing candidate-proposal and plans integration tests continued to pass against the migrated schema.

## Follow-up work

- A Foundry VTT item export profile, separately scoped after a demonstrated need.
- A DM-facing UI for browsing, creating, and exporting rules elements.
- Richer per-kind mechanics (casting time, components, range, duration for spells) if demonstrated use cases require them.
