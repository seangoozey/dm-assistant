---
id: TKT-0134
title: Vocabulary overhaul — Glossary and Help rewritten to ADR-0017 declarations
status: done
priority: P1
milestone: trustworthy-librarian
depends_on: [TKT-0132, TKT-0133]
created: 2026-09-19
updated: 2026-09-19
---

# TKT-0134: Vocabulary overhaul — Glossary and Help rewritten to ADR-0017 declarations

## Context

The glossary's 36 entries were built incrementally and contain terms that contradict ADR-0017 (e.g., "Document" defined as "text preserved as evidence" when Document now means "the page the user views"; "Claim" defined without Truth State mention; no entry for "Attribute" or "Source").

## Scope

### Glossary rewrite (glossary.tsx)
Entries to ADD:
- **Source** — "The port of entry from which information came. Carries provenance."
- **Attribute** — "An Enumerable or Named field on an Entity: location type, status, race, sex, life status."
- **Kind** — "The structural category of an Entity — determines the Template and organizational rules. Not descriptive data; that's Attributes."
- **Truth State** — "Where a Claim sits on the canonical spectrum: Considered → Prepared → Intended → Established → Observed."
- **Identity** — "The person, place, thing, or event being defined. The Entity defines it."

Entries to REDEFINE:
- **Document** — from "text preserved as evidence" to "the page a user views in the Library — assembled from the Entity by a Template"
- **Claim** — add "every Claim has a Truth State; a Claim without one should not exist"
- **Entity (identity)** — split into Entity ("assembled collection of Attributes and Claims") and Identity ("the real-world referent")
- **Records** — clarify as "data collectively; Claims with their Sources and history"

Entries to REMOVE or merge:
- **"Entity description"** — merge into Document/Source language (a description Source whose Claims display in a templated section)
- **"Canon by receipt"** — stays but definition updated to reflect Truth State spectrum (there is no canon/non-canon binary)

Entries that stay unchanged:
- Alias, Misspelling, Faction, Roster, Role, Leadership, Title, Candidate, Proposal, Receipt, Derived vs. audited, AI model profile, AI action, Drafts tray, Evidence vs. suggestion, Graph trace, Supersession, Change set, Direct input, Provenance, Life status, Dossier

### Help page
- "The three layers" entry updated to use ADR-0017 vocabulary (Entity/Template/Document, Source/Claim/Truth State)
- Any Term tooltips that reference old vocabulary updated to match

## Validation evidence

(to record when built)

## Validation evidence

Delivered 2026-09-19, deployed.

- New entries added: **Truth State** (the canonical spectrum: Considered→Prepared→Intended→Established→Observed), **Source** (port of entry, carries provenance), **Attribute** (enumerable/named fields on an Entity), **Kind** (structural category, not descriptive), **Identity** (the real-world referent the Entity defines)
- Redefined: **Claim** (now includes Truth State requirement — "a Claim without a Truth State should not exist"), **Document** (from "text preserved as evidence" to "the page a user views in the Library"), **Entity** (from "a named thing" to "an assembled collection of Attributes and Claims that defines an Identity"), **Records** (now mentions Sources and Truth States)
- React 137/137.
