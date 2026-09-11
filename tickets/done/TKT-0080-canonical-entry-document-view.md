---
id: TKT-0080
title: Replace source-file Documents with readable canonical entry pages
status: done
priority: P0
milestone: trustworthy-librarian
depends_on: [TKT-0073, TKT-0079]
created: 2026-08-22
updated: 2026-08-27
---

# TKT-0080: Replace Source-File Documents with Readable Canonical Entry Pages

## Outcome

The primary library view presents a campaign record as a coherent entry. A DM can understand its identity, current truth, plans and possibilities, provenance, and superseded history without reading importer files or migration metadata.

## Observed failure

The deployed Documents page is still organized around 143 source files. PC files receive a partial curated projection, while campaign-bible and ordinary files render as large raw Markdown blocks. Navigation exposes paths and `.md` extensions as identity, and canonical claims are not assembled into a record-level page.

## Product boundary

- **Entries** are canonical campaign records and their current evidence-backed claims.
- **Sources** are immutable Markdown or captured evidence used to support entries.
- Source files and importer classifications remain inspectable, but they are not the normal reading experience.

## Scope

- Add a canonical entry read model and API keyed by stable record ID.
- List and navigate entries by canonical name and record family/kind, not source path.
- Render a consistent entry header: canonical name, family, kind, tags, aliases, and relevant structured fields.
- Use family-specific presentation contracts rather than one generic record template:
  - PCs and NPCs render as characters, emphasizing identity, appearance, personality, biography, relationships, abilities, current situation, and the PC/player agency boundary.
  - Encounters render as run-at-table material, preserving purpose and setup followed by progression flow, named areas/scenes, read-aloud text, DC checks, creatures, consequences, branches, and outcomes.
  - Locations emphasize hierarchy, summary, population, factions, notable areas, inhabitants, and connected encounters.
  - Lore/worldbuilding emphasizes overview, established truths, history/myth/cosmology, and related records.
  - Plans emphasize agency, lifecycle, objectives, prerequisites, expected developments, and supporting evidence.
- Group current claims into readable sections: established lore, observed play, active intentions/preparation, and possibilities.
- Show campaign dates and explicit prerequisites when present.
- Keep provenance compact by default, with exact source paths/spans available on demand.
- Keep superseded claims in a separate collapsed history section.
- Preserve specialized character fields: background, race, sex, and player for PCs.
- Move raw source-document browsing to an explicit Sources/Import Evidence surface.
- Remove `.md` extensions and importer classifications from normal entry navigation.

## Acceptance criteria

- [x] Opening an NPC, PC, location, lore concept, encounter, or plan shows a coherent canonical entry rather than raw Markdown.
- [x] Character and encounter pages have materially different layouts suited to their use at the table.
- [x] Encounter progression, named areas, read-aloud blocks, DC checks, and consequences remain visually distinguishable and in source order.
- [x] Current claims are grouped by truth/agency meaning and readable as full assertions.
- [x] Provenance is accessible without dominating the entry.
- [x] Superseded material is visually separate from current truth.
- [x] Entries with multiple source documents present one record page rather than duplicate file pages.
- [x] Source-only material with no canonical record remains available under Sources and is clearly labeled as evidence.
- [x] Navigation uses canonical names without `.md` extensions.
- [x] Representative browser tests cover Coreferra, Romulus, Exile Camp, the unfinished Exile Camp Meeting, and a campaign-bible plan.
- [x] Strict typecheck, frontend tests, Campaign Core tests, and PostgreSQL integration tests pass.

## Out of scope

- Creating new entries or direct-input capture (TKT-0038).
- Rich-text editing of arbitrary entry types.
- Automatic entity linking or renewed subject-predicate-object extraction.

## Progress

- Deployed the first typed reading slice: PC/NPC character views, encounter flow, and structured location/worldbuilding pages.
- Library navigation now shows entry types and human-readable names; source paths remain available only in evidence details and accessible labels.
- Added representative NPC and encounter tests; 26 App tests and strict TypeScript pass.
- Added a single sliding `Source` switch. Off is the normal campaign-entry view; on exposes immutable filenames and importer classifications only when requested.
- Long section-sized canonical assertions now show a readable summary with the unabridged assertion and exact provenance available on demand, preventing imported evidence blocks from overwhelming encounters and other entry pages.
- Added a Campaign Core canonical-entry read model and DM-only API keyed by stable entity ID. It aggregates aliases, tags, current claims, and every supporting source across file boundaries.
- Entries mode now navigates those canonical records and loads a suitable primary source only as presentation material; Sources retains the complete immutable 143-file tree.
- Entries now includes canonical plans and readable source-backed families for encounters, GM material, handouts, lore, and session notes. These are explicitly marked `Source-backed`; session prep and the two excluded location-migration inventories remain omitted.
- Source-backed records use the stable imported document ID until the schema gains an explicit non-entity record identity. The complete evidence tree remains available through Sources.
- Repaired incomplete PC identity coverage with one immutable three-item proposal/change set: Coreferra, Ladir, and Zander Thromius now join Ruhrogue as canonical PC entities. Receipt `40ab6a7b-b64b-4e2b-b11b-b0996fd57460`.
- Entity entry provenance now includes the source document recorded by its creation proposal, allowing newly canonicalized PCs to reuse their existing editable profiles before they acquire canonical claims.
- PC identity is not measured by claim count. Player, race, sex, status, aliases, and former names are canonical curated-profile fields; extraction must not manufacture campaign claims from those fields. Claim counts are not shown in the campaign-facing entry view.
- The campaign-manager view now keeps storage mechanics subordinate to content: entry families are collapsible; row type labels and counts are removed; source-backed labels and the library total are removed; source browsing lives behind the `Source` switch; stable IDs, claim/source totals, claim truth metadata, canonical-record projections, and exact evidence are hidden in record-detail disclosures.
- PC pages now project only character-relevant content: observed play facts, player-communicated plans, and DM plans. Derived Current Status/GM source summaries and the catch-all Facts section are excluded. Empty sections say `None`; truth state, authority, and evidence remain managed below the presentation layer.
- PC fact and plan rows render as content cards with compact edit, source, and hide controls. Hidden cards are recoverable through the page-level visibility control, while source paths/excerpts remain closed until explicitly requested. Page editing and hidden-content visibility use the same unobtrusive icon treatment.
- NPC pages now expose the same compact edit action as PCs. Their versioned character-profile overlay supports race and sex corrections without inventing a player or rewriting immutable imported Markdown.
- The May 9 Chamber of Echoes outcomes are projected as one focused observed real-play card for each of the four canonical PCs, all retaining the shared session-note provenance rather than the derived PC Current Status summaries.
- All migrated PC campaign-sculpting directions are now focused, source-backed, and linked to their canonical PC identities. The unlinked migration remnants were explicitly superseded. A PC DM plan remains possible/prepared, DM-only, and non-predictive; it is not forced to claim a concrete condition when none exists.
- Canonical entry reads now aggregate current claims and all supporting sources across documents while returning superseded claims as a separate history collection.
- Current record information is visible and grouped as real-play facts, established information, plans/preparation, and possibilities. Truth mechanics and exact provenance remain collapsed beneath the campaign-facing content.
- Canonical NPC dossiers include known facts, NPC intentions, DM plans, relationships, and earlier versions on one page. Multi-source locations likewise render one entry with a complete Sources drawer.
- Added focused coverage for Romulus, Exile Camp, and campaign-bible GM planning alongside the existing Coreferra and Exile Camp Meeting coverage. Final validation: 304 Campaign Core tests passed, 63 React tests passed, strict typecheck and Windmill build passed, and 38 retrieval cases validated.
