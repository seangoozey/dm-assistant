# ADR-0017: Domain Vocabulary Declaration

- Status: accepted (user ruling 2026-09-19)
- Context: TKT-0131 terminology and architecture review
- Supersedes: implicit terminology in ADR-0005, ADR-0011, ADR-0012, ADR-0015, ADR-0016

## Context

The app's vocabulary accumulated incrementally through migration-driven development: "Document" meant the source file, "Entity" and "Identity" were used interchangeably, "Claim" / "Assertion" / "Record" were synonyms, and "File" existed as a concept only because the original campaign material was .md files. The Lore creation workflow (TKT-0099) surfaced these frictions as concrete user-facing problems: the same object had four names depending on which surface displayed it, the glossary contradicted the UI, and the migration origin was baked into the architecture.

This ADR declares the definitive domain vocabulary. All surfaces, Help entries, ADRs, and backend naming must conform.

## Decision

### Core declarations

1. **A Document is the page that a user views in the Library.** It is the presentation layer — the assembled page. It is NOT the source file. The Document displays the information encompassed by an Entity using Templates.

2. **A Claim is the atomic assertion on which truth is built.** "Assertion" is not a separate term — the Claim IS the assertion. Every Claim has a Truth State; a Claim without a Truth State should not exist. The Truth State spectrum runs from Canonically Considered (lowest) through Prepared, Intended, and Established up to Canonically Observed (highest). All information in the system is inherently Canonical — the Truth State tells you where it sits, not whether it counts.

3. **An Attribute is an Enumerable or Named field assigned to an Entity.** Location type, status, race, sex, life status are Attributes. Attributes are the structured data fields on the Entity.

4. **An Entity is an assembled collection of Attributes and Claims that defines an Identity.** The Entity is the data model — the structured object. It is not the real-world thing itself.

5. **The Identity is the person, place, thing, event being defined.** The real-world referent. The Entity defines it; the Identity is what's being defined.

6. **A Template is a predefined method of arrangement for Documents, separated by Kind.** Templates are per-Kind layout rules. They arrange how the Document displays the Entity's information.

7. **Kind is the structural category of an Entity.** It determines which Template and organizational rules the system applies. Kind is NOT descriptive data about the Identity — descriptive characteristics belong to Attributes. Kind sits above Attributes as a classification.

8. **A Source is the port of entry from which the information came.** Sources carry provenance. An imported .md file is a Source. A direct-input description is a Source. A session note is a Source. Direct Input Sources record where they were input from (Library, Lore, Brainstorm, etc.).

9. **There are no Files.** The .md file paths of imported material are Source provenance, not system concepts. The system does not use .md as names for Entities or Documents. Files may exist in the future as attachments (images, etc.) but are not part of the current domain model.

10. **All information in the system is inherently Canonical.** The system defines Canon via storage and presentation. There is no "non-canonical" zone — Brainstorm thoughts are Sources whose Claims sit at the Considered Truth State. The "non-canonical workspace" framing is retired.

### Lifecycle declarations

11. **Migration** is the act of ingesting data into the system and structuring it to match the system's architecture. The system is in Migration until the original source material is fully ingested and Migration is deemed complete.

12. **Seeded** is the state after Migration completes. A Seeded system does not use its original source material as a definition of its system architecture. Sources remain as provenance but stop being structural concepts.

13. **A Proposal** is the whole submitted lore entry before canonicalization. It is a structured draft of changes being reviewed. Proposals are part of the Claim lifecycle even when Seeded.

14. **A Candidate** is an atomic assertion extracted from a Proposal that has not yet been assigned a Truth State. Candidates are part of the Claim lifecycle even when Seeded.

### UI declarations

15. **Entry** is a UI term exclusively. It means anything the user chooses or types. An Entry is not a domain concept — it is the interface's word for the user's current selection or input target. Entries exist only in the UI layer.

16. **A Record** is a real-world term meaning any piece of data in the database. "Records" is fine for referring to data collectively where the list includes more than Claims. Claims with their Sources and history are collectively Records.

17. **The Description is a templated section on the Document** that displays Claims in a user-accessible way. When a Source is Direct Input (Lore, Brainstorm, etc.), its Claims need to be separated and parsed for Canonical Truth State. Those Claims make up the Description section.

### What retires

- **"Assertion" as a standalone UI term** — Claim IS the assertion. The Migration wizard's "Assertion" step becomes "Claim."
- **"File" as a domain concept** — .md paths are Source provenance, not identity.
- **"Non-canonical" as a state label** — everything has a Truth State; nothing is outside canon.
- **"Entry" as a domain concept** — it survives only as a UI word for user selection/input.
- **The Document/Source conflation** — Document is the page; Source is where it came from. One word, one job.

## Consequences

- The Migration tree's "Documents" header becomes "Sources."
- The Library's "Source files" toggle stays but its meaning is now unambiguous: browsing Sources.
- The description filing path (`entities/{slug}.md`) is internal Source provenance, not Entity naming.
- The glossary's "Document" entry redefines to "the page a user views" (currently it says "text preserved as evidence" — that becomes "Source").
- The Brainstorm page's "non-canonical workspace" framing changes to reflect Truth State (thoughts are Sources at the Considered state).
- The Migration wizard renames "Assertion" to "Claim" throughout.
- "Kind" gets its own classification surface, distinct from the Attributes editor.
- All ADRs that use "assertion" or "document" in the old senses are superseded by this declaration.

## Alternatives considered

- **Keep the current vocabulary** — rejected: three synonyms for one concept, four names for one object, and a glossary that contradicts the UI is not maintainable.
- **Collapse to "Source" everywhere** — rejected: this was the Option A proposal, but Sean's declaration goes further by redefining Document as the page (not the source file), which is cleaner.

## Implementation

Recorded in TKT-0131; implementation tickets follow.

## Amendment: The Canonical Truth State (CTS) spectrum — fully defined

The original declaration named the states but did not fully define their semantics. This amendment (Sean, 2026-09-19) completes the definition. Short name: **CTS**.

### The six states

| State | What the system asserts | Known blockers? |
|-------|------------------------|-----------------|
| **Considered** | "I worked through this and found a route that precludes it" | Yes — that's the point |
| **Possible** | "This scenario is available to happen" | No — no known blockers |
| **Prepared** | "DM material exists but hasn't been encountered" | N/A — the material exists |
| **Intended** | "A character or faction has a stated plan or goal" | N/A — pressure, not prediction |
| **Established** | "Confirmed fact of the world" | N/A — the fact floor |
| **Observed** | "Directly witnessed at the table" | N/A — highest authority |

### Transition rules

- Any state → Observed: always possible (anything can happen in real play). Considered → Observed is legitimate.
- Considered → Possible: when a blocker clears (the NPC who was the blocker dies).
- Considered → Prepared: the DM skips further brainstorming and builds material from a considered idea.
- Prepared stays Prepared even when the scenario becomes impossible — you can't un-prepare; the material exists. It's dead-ended, not un-prepared.
- Direct → Established promotion should be avoided. Considered exists specifically to catch things that would otherwise skip review and jump to Established.
- Considered originates primarily in Brainstorm (a statement superseded by a later statement in the same session), but not exclusively — any surface where a DM acknowledges "I explored this and parked it" can produce it.

### Implementation note

The DB `claim_state` enum currently has: observed, established, intended, prepared, possible. `considered` must be added as a new value (below possible). The display rename from 0115/0133 that collapsed Possible into Considered must be undone.
