# ADR-0005: Referenceable Records and Controlled Kinds

- Status: accepted
- Date: 2026-08-02

## Context

The original schema gives entities stable UUIDs but accepts arbitrary `entity_type` text, while claims and relationships reference only entity tables. Campaign material also contains future referenceable families such as plans and campaign sessions. A single untyped JSON table would erase useful constraints, while a `type` plus unchecked UUID pair would allow dangling or cross-family references. Overlapping primary types and catch-all values would make classification unreliable for the DM.

## Decision

Use a thin `records` identity table for every referenceable campaign record. Each family table shares the record UUID as its primary and foreign key. References use real foreign keys to `records.id`; family-specific fields remain in typed family tables.

Separate stable record family from namespaced family-specific kind. `record_type`, `entity_kind`, `plan_kind`, `artifact_kind`, and `rules_kind` are independent vocabularies. Registry rows own stable kind identity, versioned keys and documentation, aliases, lifecycle status, and replacement metadata. Versioned application code and migrations own required fields, validation, storage behavior, and exporters. The application does not construct schemas or behavior-bearing kinds in place.

The initial entity kinds are:

- `npc`: a DM-controlled character.
- `pc`: a character controlled only by its player.
- `location`: a place at any geographic scale.
- `faction`: an organized group with shared identity.
- `item`: an in-world object with canonical identity.
- `event`: a distinct historical, mythical, or cosmological occurrence.
- `worldbuilding`: an era, legend, cosmological structure, or abstract setting concept.
- `rules_element`: a reusable spell, feat, or ability; structured mechanics belong to TKT-0032.

There is no `other` or arbitrary free-text entity kind. Unsupported legacy values remain attached to their stable records and enter explicit reclassification review. Rename preserves the stable kind ID and records the old key as an alias. Merge or split adds replacement kinds, deprecates earlier kinds, and creates per-record reviewed reclassification proposals. It never changes record IDs or rewrites historical receipts.

PC and NPC are permanent, mutually exclusive agency categories. The system cannot infer or predict a PC action. A deity controlled by the DM remains an NPC; `deity` is an optional retrieval tag.

Tags are optional, non-exclusive facets rather than truth. The initial seed is `history`, `mythology`, `cosmology`, `world`, `continent`, `country`, `region`, `settlement`, `monster`, `deity`, `religion`, and `political`. A disputed descriptor belongs in a claim, not a tag. Dates, source classifications, truth states, deliverable kinds, and rules kinds are not tags.

Original handouts and character sheets are source evidence. Generated handouts, sheets, cards, and import packages are derived artifacts. The canonical item or rules element described by a deliverable remains a separate entity. Campaign sessions are future domain records and are not the existing internal `workflow_sessions`.

## Consequences

- Cross-family references gain database-enforced identity without flattening family schemas.
- Entity creation and retrieval use a small vocabulary and optional tags.
- Kind changes require reviewed code and migrations when behavior changes.
- Existing unsupported free-text values remain recoverable and auditable but cannot be used for new canonical writes.
- First-class plan behavior remains separately scoped by TKT-0031.
- Structured rules mechanics and export profiles remain separately scoped by TKT-0032.

## Alternatives considered

- One generic JSON record table: rejected because family constraints and safe migrations would become application conventions.
- Polymorphic `target_type` plus arbitrary UUID: rejected because PostgreSQL could not enforce target existence or family compatibility.
- A large entity ontology or catch-all `other`: rejected because overlapping choices increase classification errors and hide missing domain decisions.
- User-authored schemas in the app: rejected because registry metadata cannot safely define executable validation, storage, or export behavior.
