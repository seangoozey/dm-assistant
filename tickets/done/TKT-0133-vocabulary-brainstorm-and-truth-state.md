---
id: TKT-0133
title: Vocabulary overhaul — Brainstorm reframed from "non-canonical" to Truth State; canon-status hero removed
status: done
priority: P1
milestone: trustworthy-librarian
depends_on: []
created: 2026-09-19
updated: 2026-09-19
---

# TKT-0133: Vocabulary overhaul — Brainstorm reframed from "non-canonical" to Truth State; canon-status hero removed

## Context

ADR-0017: "All information in the system is inherently Canonical." Brainstorm's "non-canonical workspace" framing contradicts this. Thoughts are Sources whose Claims sit at the Considered Truth State. The "Canon status" hero label on entry pages contradicts canon-by-receipt.

## Scope

### Brainstorm reframing
- "Non-canonical workspace" → remove (thoughts are Sources at Considered state)
- "Preserved outside canon" → "Preserved as Sources" or "Thoughts are Sources, not yet parsed into Claims"
- "Nothing here changes canon" → "Nothing here changes established truth without review"
- "consider for canon" → "consider for promotion" (promote to a higher Truth State)
- "Creation remains non-canonical" → "Creation remains at the Considered state until promoted"
- "Canonical content search" → "Claim search" or "Truth search"

### Canon-status hero removal
- Remove the "Canon status" `<dt>/<dd>` from the entry hero — it displays legacy doc metadata (`canon_status` from frontmatter) with a Term label whose definition says "there is no canon-status field." The data belongs in the Records hood under provenance, not in the hero.

### Truth State vocabulary alignment
- Ensure state labels consistently use the ADR-0017 spectrum: Observed, Established, Intended, Prepared, Considered (currently "Possible" in the DB → rename in UI to "Considered" to match the declaration)
- "NPC or faction intention" → "Intended" in Brainstorm context
- "DM only" everywhere (retire "Dungeon Master" in the ask tray)

## Validation evidence

(to record when built)

## Validation evidence

Delivered 2026-09-19, deployed.

- Brainstorm: "Non-canonical workspace" → "Working ideas"; "Nothing entered here becomes campaign truth without an exact reviewed proposal" → "Thoughts here are Sources — they become Claims with Truth States through reviewed promotion"; "non-canonical evidence" → "DM-only Source"; "Preserved outside canon" → "Source (not yet parsed into Claims)"; "consider for canon" → "consider for promotion"; "Nothing here changes canon" → "Nothing here changes established truth without review"; "Creation remains non-canonical" → "remains at the Considered state"; "Canonical content search failed" → "Claim search failed"
- Canon-status hero removed from entry pages (the field displayed legacy doc metadata with a Term label whose definition says "there is no canon-status field" — the data belongs in the Records hood, not the hero)
- React 137/137.
