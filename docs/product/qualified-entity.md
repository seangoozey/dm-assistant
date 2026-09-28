# Qualified Entity — the standard

Status: ACCEPTED spec (all rulings from Sean, 2026-09-21). Amendment to ADR-0017's vocabulary; glossary entry shipped with the audit. TKT-0140's campaign audits against this; the audit endpoint (`GET /campaign/qualified-entities`) is its machine-checkable proof.

## Purpose

ADR-0017 defines what an Entity *is* — the digitally structured representation of an Identity: Attributes and Claims defining it. This standard defines what makes one **Qualified**: the checkable bar every library entity must clear so that "everything in the library is a Qualified Entity" is a computable, standing truth. The point is to move the system from **Migration** to **Seeded** — and then never have an unQualified Entity again.

One sentence: **an entity is Qualified when its Identity is asserted, evidenced, and owned through the declared machinery — with nothing living outside it.**

## The standard

An entity is Qualified when all of the following hold; the result is **binary**. The Migration-phase surface (TKT-0140's queue) does not care to what degree something is unQualified — unQualified is unQualified, and each finding routes to its repair lane by per-criterion reasons (implementation detail, surfaced for routing only).

### 1. It asserts something — and empty Entities do not exist

- **Q1 — at least one current (non-superseded) claim.** With claim-backed Attributes, an Entity with a Name is ≥1 Claim; "attributes but no claims" is not constructible. An Entity with literally no associated data **should not exist and should not be allowed to exist**: creation paths require at least one claim (statements promoted through review, or attribute claims minted), and any existing truly-empty Entity surfaces for resolution — populate it through a reviewed lane or remove it through the audited path (never automatic deletion). *[computed: current-claim count]*
- **Q2 — every claim carries Truth State, authority, and provenance** (evidence span to a Source). *[structural — the claim machinery admits nothing else; the audit verifies no bypass has appeared]*

### 2. Ownership is clean

- **Q3 — no unowned claim whose evidence names this entity awaits assignment**: the orphan review's (TKT-0138) pending suggestions for this entity's name are resolved (assigned, bridged to Lore, or dispositioned "no owner needed"). *[computed from the orphan queue once TKT-0138 lands; reported as pending until then]*

### 3. Its Attributes are claim-backed and dated

- **Q4 — Kind is structurally correct** for what the record is (structural sanity where computable — e.g. a `parent_location` that is not a location flags; the audit flags suspects, never auto-corrects). *[computed where checkable]*
- **Q5 — every populated attribute is claim-minted**: its value is the projection of a dated backing claim (anchored to evidence, or explicitly unanchored-but-dated DM knowledge — the life_status pattern generalized; the Romulus ruling). *[pending the minting mechanism, TKT-0143; reported as pending until it lands]*
- **Q6 — vocabulary-backed where a vocabulary exists** (status, location_type, race, sex ∈ the active Core vocabulary). *[computed]*
- **Q7 — anchoring is the nudge target, not the gate.** Unanchored-but-dated attributes qualify; their count surfaces as advisory on the entity.

### 4. Nothing renders as canon outside the machinery

- **Q8 — presentation discipline holds**: no free-prose blobs on the canonical record (the profile `summary` retires into Descriptions via the pipeline); what renders derives from claims, attributes, and authored documents only. A synthesized stand-in never does a Description's job. *[structural after retirement; the audit verifies the field is empty]*
- **Q9 — Truth States are visible where the record presents** (state chips on evidence surfaces). *[structural; UI convention]*

### Descriptions are advisory polish, not qualification (ruling 2026-09-21)

A Description is authored prose for *reading* (ADR-0015 layer 2) — it is not part of what makes an Entity an Entity. An entity with claims and attributes and no Description is Qualified; absence surfaces as a nudge (the existing no-page flag), never a gate — exactly symmetric with attribute anchoring. A Seeded app's entities qualify from birth: creation promotes claims through review, attributes mint dated claims, and Descriptions accrete as curation. Under mandatory statement review, "Description without claims" cannot be created — empty shells are pre-pipeline residue the repair lane clears, caught by Q1. ("Page" is undeclared UI vernacular — the declaration used it once to gloss Document — and this standard speaks only in declared terms.)

### Derived record types (ruling 2026-09-21)

Plans, Encounters, Notes, and the like are not Entities — an Entity is the structured representation of an Identity. They may be extended or derived versions of an Entity. **For the sake of completing migration: the Qualified Entity bar is assumed to be the floor of these types** — each must at least clear this standard, and where a type needs more (a plan's lifecycle and evidence spans, an encounter's notes), the type extends upward from the floor.

### The Migration → Seeded arc

The standard exists to be crossed once, system-wide (TKT-0140's campaign drives unQualified to zero through the reviewed lanes), and then held permanently: qualification is computed live, degrades when truth moves (a new orphan, a retired vocabulary value), and the standing surface catches it. Binary, always.

## Work items

1. **Claim-backed attribute minting** — TKT-0143 (its own ticket; also gates TKT-0137's attribute promotion). The editor stays a one-click fast path that mints dated claims behind the dropdown; presumed-retcon supersession on change per TKT-0141.
2. **The audit endpoint** — `GET /campaign/qualified-entities` computing Q1, Q4, Q6 now; Q3 pending TKT-0138, Q5 pending TKT-0143 (reported as pending, never silently passed); Q2/Q8/Q9 verified structurally. Per-criterion reasons route 0140's queue.
3. **Summary retirement** — 0140 scope (migrate the one live summary into a Description via the pipeline, then retire the field).
