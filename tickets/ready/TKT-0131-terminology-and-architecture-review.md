---
id: TKT-0131
title: Terminology and architecture review — ADRs, Help terms, and the Document question
status: ready
priority: P1
milestone: trustworthy-librarian
depends_on: []
created: 2026-09-19
updated: 2026-09-19
---

# TKT-0131: Terminology and architecture review — ADRs, Help terms, and the Document question

## Context (Sean, 2026-09-19, after Lore creation surfaced the confusion)

"I think we need to take a hard look at our terms and conclude definitively what is going on in the back end. Make a ticket to review the ADR's and the Help terms so I don't keep stubbing my toe on this."

The Lore creation workflow exposed multiple terminological and architectural frictions that have been accumulating:

### The Document question

"Does Document need to exist?" — The system distinguishes Documents (source files) from Entities (identities), but the distinction serves migration, not the domain. Sean created campaign files, migrated them into this system, and the system's architecture still references those original documents as a first-class structural concept.

The trajectory: new system data will eventually outweigh migrated data by a magnitude. If released to others, they'll never have a migration path involving "documents." At that point: why does Document exist as a structural concept? Why was Sean's data migration baked into the system's bones?

This is NOT about deleting evidence — provenance must survive. It's about whether "Document" deserves to be a primary architectural concept or whether it should collapse into "evidence" or "source" as a property of assertions rather than a first-class navigational/category entity.

### Terminology drift

- "Entity" in Help doesn't match how factions are treated (factions are called Entities in the backend but Help describes entities differently)
- "Document" vs "source" vs "evidence" vs "file" — used interchangeably, mean different things in different contexts
- "Assertion" vs "claim" vs "record" — sometimes the same thing, sometimes not
- The glossary was built incrementally and may not reflect the current actual model

### The migration artifact problem

The system was designed around importing Sean's pre-existing campaign files. That origin shaped the architecture: Documents are first-class, the Library has a "Source files" mode, entity pages compete with document pages, the Records hood mixes claim provenance with document paths. A user who starts fresh in this system would never encounter half these concepts — they'd just create entities and assertions directly.

## Scope when taken up

1. **Comprehensive ADR review**: Read every ADR, identify decisions that were shaped by the migration origin rather than the domain's permanent needs. For each: keep, amend, or supersede.

2. **Glossary/Help reconciliation**: Map every term in the glossary to what the backend actually calls the concept. Identify: terms that describe implementation details rather than domain concepts, terms that are synonyms for the same thing, terms that mean different things in different surfaces.

3. **The Document question** (design ruling needed from Sean):
   - What would the system look like if "Document" were not a first-class concept?
   - What replaces it? Assertions carry their own provenance (source path, excerpt, span) — is that sufficient?
   - What happens to the Source files tree view? To document paths as entity page candidates?
   - What is the migration path FROM the current model (documents as first-class) to whatever comes next?

4. **Terminology normalization**: Propose a definitive vocabulary that works for both the DM and future users who never migrated. Each term should have one meaning, used consistently across UI, Help, ADRs, and backend naming.

5. **Clean separation ruling**: If migration-related concepts (documents, file paths, source trees) are demoted or removed, what replaces them for provenance? The answer must preserve the standing rule that evidence chains to original material.

## Out of scope

- Actually implementing any model changes (this ticket is the review and design rulings).
- Deleting or modifying any existing data.
- The graph bundle's disposition (parked separately).

## Validation evidence

(to record when the review is complete)

## Full ADR + app + glossary audit (2026-09-19 — the working data)

### ADR findings (16 ADRs read)

**Documents as a first-class concept** appears only in ADR-0015 (authored documents as a named layer) and ADR-0016 (imported evidence documents as a page-source category). Earlier ADRs use "source evidence," "source segments," "immutable source text" — presupposing imported files without naming "document" as a concept. ADR-0005 classifies document-like things as "source evidence" or "derived artifacts."

**Migration-origin dependencies, ranked:**
1. ADR-0012 (provenance-first claims) — "The migration workflow made subject resolution a prerequisite" — the canonical shape of claims was driven by import throughput
2. ADR-0016 (every page editable) — the three-way page taxonomy (page-less / authored / imported) exists because of legacy import; imported documents are permanently read-only
3. ADR-0005 (controlled kinds) — "unsupported legacy values remain attached… enter explicit reclassification review" — machinery for imported free-text kinds
4. ADR-0007 (chronology) — the "single-forward migration" shortcut was enabled by the empty canonical store at import time
5. ADR-0015 (three layers) — the question arises from imported document pages, though the ruling itself is permanent

**Terminology arc across ADRs:** early ADRs say claims/records/entities/evidence; ADR-0011–0012 establish "assertion" as the authoritative unit; ADR-0015–0016 elevate "documents" and "pages" to first-class concepts.

### UI vocabulary audit (glossary's 36 terms vs. actual usage)

**The seven breaks, ranked by severity:**

1. **Claim / Assertion / Record — three-way synonym.** The migration wizard says "Assertion" (step name, "Canonical assertion", "The complete assertion is the record"); every other surface says "claim" (100+ occurrences); "record" is used generically for claims, entries, plans, AND the Records hood ("Campaign record", "Plan records", "Affected record", "Search records"). The glossary defines all three but the UI uses them interchangeably.

2. **Document / Source / File — same object, four names.** The same class of thing is "Documents" in Migration, "Source files" / "Source" in the Library toggle, "Sources" in drawers and Settings, and "files" in counts and errors. The glossary's "Document" only leads in the Migration context. No single name is used consistently.

3. **"Canon status" hero label contradicts "canon-by-receipt."** The glossary says "There is no canon-status field; something is canon because an audited action says so." The entry hero renders `<Term term="canon-by-receipt">Canon status</Term>` — labeling a legacy doc's metadata field with a term whose definition denies the field exists.

4. **Entity vs. Identity — two vocabularies for one concept.** "identity" owns the registry UX (Identity page, Identity Review, Save identity profile); "entity" owns the creation/kind UX (Entity kind, Create entity). The glossary defines "Entity (identity)" acknowledging the dual naming, but the systematic split means the user encounters two names for the same thing depending on which surface they're on.

5. **Glossary terms with no UI presence.** "Supersession" is never named (surfaced as "Earlier versions" and "Superseded claim history"); "Change set" appears once in a message; "Graph trace" is called "Connected through." These are vocabulary that exists in Help but can't be found by searching the UI.

6. **State/visibility value drift.** "DM only" vs "Dungeon Master"; "Real-play facts" (group label) vs "Observed" (state value) vs "Real play" (authority value); "Intended" vs "NPC or faction intention."

7. **Records hood summary text varies** per view ("claims, provenance, history" vs "session claims…" vs "known facts, real-play, plans") despite the glossary's "same label everywhere" promise.

## Sean's Domain Vocabulary Declaration (2026-09-19 — the definitive ruling)

Recorded as **ADR-0017** (accepted). The complete declaration:

### Core terms
- **Document** = the page the user views in the Library (presentation layer)
- **Claim** = the atomic assertion on which truth is built (has a Truth State; "assertion" is not a separate term)
- **Attribute** = an Enumerable or Named field on an Entity (location_type, status, race, sex, life_status)
- **Entity** = an assembled collection of Attributes and Claims that defines an Identity
- **Identity** = the person, place, thing, event being defined (the real-world referent)
- **Template** = a predefined method of arrangement for Documents, separated by Kind
- **Kind** = the structural category of an Entity (determines Template; NOT descriptive data — that's Attributes)
- **Source** = the port of entry from which information came (carries provenance; Direct Input Sources record where they were input from)
- **File** = does not exist (.md paths are Source provenance, not identity)

### Truth State as the canonical spectrum
All information is inherently Canonical. The Truth State tells you WHERE on the spectrum something sits, not WHETHER it counts. Spectrum: Considered → Prepared → Intended → Established → Observed. A Claim without a Truth State should not exist. Brainstorm is not "non-canonical" — its Claims sit at Considered.

### Lifecycle
- **Migration** = ingesting and structuring data to match the architecture (temporary state)
- **Seeded** = after Migration completes; original source material is provenance, not architecture
- **Proposal** = the whole submitted lore entry before canonicalization (permanent lifecycle term)
- **Candidate** = an atomic assertion extracted from a Proposal without a Truth State yet (permanent lifecycle term)

### UI terms
- **Entry** = anything the user chooses or types (UI term exclusively, not a domain concept)
- **Record** = any piece of data in the database (used collectively where the list includes more than Claims)
- **Description** = a templated section on the Document displaying Claims accessibly

### What retires
- "Assertion" as a standalone UI term (Claim IS the assertion)
- "File" as a domain concept
- "Non-canonical" as a state label
- "Entry" as a domain concept (survives as UI-only)
- The Document/Source conflation

### Direct Input provenance
Direct Input Sources must record WHERE they were input from: Library, Lore, Brainstorm, etc. This is provenance metadata on the Source.
