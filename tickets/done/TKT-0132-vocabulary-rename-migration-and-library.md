---
id: TKT-0132
title: Vocabulary overhaul — Migration, Library, and Records surfaces rename to ADR-0017
status: done
priority: P1
milestone: trustworthy-librarian
depends_on: []
created: 2026-09-19
updated: 2026-09-19
---

# TKT-0132: Vocabulary overhaul — Migration, Library, and Records surfaces rename to ADR-0017

## Context

ADR-0017 declares the definitive domain vocabulary. This ticket implements it across the Migration workspace, the Library (both modes), the Records hoods, and the Settings that reference them.

## Scope

### Migration surface
- Wizard step 2 "Assertion" → "Claim" (label, aria-labels, "Canonical assertion" → "Canonical claim", "Review extracted assertions" → "Review extracted claims", "Include assertion N" → "Include claim N", "The complete assertion is the record" → "The complete claim text is the record")
- "Document tree" aria → "Source tree"; "Documents" sidebar header → "Sources"; "N files" count → "N sources"
- "Select a document to narrow the queue" → "Select a source to narrow the queue"
- "in this document" → "in this source"
- "No session documents found" → "No session sources found"
- "Sync claim dates from dated documents" → "Sync claim dates from dated sources"
- "Resolved from the document's focal subject" → "Resolved from the source's focal subject"

### Library surface
- "Source files" toggle label stays (meaning is now unambiguous)
- "Loading document…" → "Loading source…"; "Document content" aria → "Source content"; "Unable to load document content" → "Unable to load source content"
- Guard label "the X document" → "the X source"
- "Source file missing" tooltip stays
- "entity↔document links" in Link audit → "entity↔source links"
- Description composer copy: "evidence-class document" → "evidence-class Source" (or just "evidence")

### Records hoods
- Unify summary text to "Records — claims and sources" everywhere (currently varies per view type)
- "Sources" drawer summary stays
- Settings "Show sources & provenance" stays

### Description composer
- "Your prose becomes an evidence-class document" → "Your prose becomes a Source"
- "The revised prose files as a new revision of the same evidence-class page" → adjust "evidence-class page" to Source language

### Out of scope
- Brainstorm copy changes (TKT-0133)
- Glossary/Help rewrite (TKT-0134)
- Kind/Attribute separation (TKT-0135)

## Validation evidence

(to record when built)
