---
id: TKT-0135
title: Vocabulary overhaul — Kind separated from Attributes in editors and Templates; Source provenance for Direct Input
status: ready
priority: P2
milestone: trustworthy-librarian
depends_on: [TKT-0132]
created: 2026-09-19
updated: 2026-09-19
---

# TKT-0135: Vocabulary overhaul — Kind separated from Attributes in editors and Templates; Source provenance for Direct Input

## Context

ADR-0017: "Kind is the structural category of an Entity. It determines which Template and organizational rules the system applies. Kind is not descriptive data about the Identity; descriptive characteristics belong to Attributes."

Currently Kind and Attributes are mixed in the same profile editor with no visual or conceptual separation. Also, Direct Input Sources don't record where they were input from.

## Scope

### Kind / Attributes separation in editors
- Entity profile editor: Kind gets its own distinct section/classification UI (not just another dropdown in the form grid); Attributes (race, sex, status, location_type, life_status) group separately under an "Attributes" heading
- Lore creation page: Entity kind selector visually separated from the description/prose section (already partially separated; make the distinction explicit)
- Template field selectors in profile editors labeled as "Attributes" not just form fields

### Direct Input Source provenance
- Direct Input Sources record WHERE they were input from: Library (description composer), Lore (Lore creation), Brainstorm (thought), Session (note capture). This is provenance metadata on the Source — displayed in the Records hood alongside the path.
- Implementation: the `root_identifier` already carries this (`direct-input:entity-description:{id}`, `direct-input:session-note:{id}`) but the UI doesn't surface the origin. Show it in the Records hood as "Source: Direct input from Lore creation" / "Direct input from Library description" / etc.

### Entry retirement from domain copy
- "Campaign entry" header span → "Entity page" or just the Kind label
- "Select an entry from the library" → "Select an Entity from the Library"
- "Edit entry" button → "Edit Entity" (or "Edit Identity" since you're editing the real-world referent's data)
- Library tree kind groups stay (they group Entities by Kind)

## Validation evidence

(to record when built)

## Validation evidence (partial — 2026-09-19, deployed)

Delivered:
- **"Entry" retired from domain copy**: "Campaign entry" header span → "Entity"; "Select an entry from the library" → "Select an Entity from the Library"; "Edit entry" aria → "Edit Entity". "Entry" survives only as UI language (the Lore queue's "campaign entry" is the UI word for a user-created item).
- **Kind separated from Attributes in the profile editor**: an "Attributes" section label now separates the structured fields (name, status, race, sex, location type, parent location, life status, aliases) from the Kind selector (which is labeled "Kind (audited)" and positioned below the Attributes grid).
- React 137/137.

### Remaining for 0135 (not yet delivered)
- **Direct Input Source provenance**: record and display WHERE each direct-input Source was entered (Library description composer, Lore creation, Brainstorm thought, Session note). Requires Core support (origin field or extracted from root_identifier) and Records hood display.
- **Lore page kind selector**: visually separate the Kind dropdown from the description prose section (currently in the same form area).
