---
id: TKT-0042
title: Timeline view
status: backlog
priority: P2
milestone: trustworthy-librarian
depends_on: []  # TKT-0041 closed long ago; natural sibling = TKT-0130 (ready) — 0130 is the query side (day-ordinal retrieval + when-questions), this is the browse side
created: 2026-08-04
updated: 2026-09-28
---

# TKT-0042: Timeline View

## Outcome

The canonical timeline (including BCE content) is viewable as a structured, ordered experience rather than raw Markdown, leveraging the chronology model and the campaign's actual dates.

## Context

`lore/timeline.md` is player-facing lore with BCE dates (20,000 BCE, 15,000 BCE) and CE ranges that drove the chronology design. Rendering it as raw Markdown loses the ordering and structure the chronology model now provides. This is the read-side payoff for TKT-0030.

Read `docs/decisions/ADR-0007-campaign-chronology.md`, `docs/product/vision.md`, and TKT-0041.

## Ruling enrichment (ADR-0021, 2026-09-28): the Timeline is a unique event Entity

Sean's rulings (2026-09-28, refined): the Timeline is a UNIQUE event — all historical lore — with a dedicated document template. REFERENCE FIRST: it is not an ownership absorber. Dates everywhere are tagged as MENTIONS; the Timeline picks up date-mentioned claims for VIEWING with ownership left alone; it CAN own date records — its own document's history (the 36 `lore/timeline.md` orphans route to its ownership) — but dated claims elsewhere stay owned by their entities and merely appear in the view. Scope additions beyond the original browsing view:

- **The Timeline Entity**: minted once (its kind ruled at build time), owning its document's historical records — the 36 timeline.md orphans (TKT-0138's timeline slice).
- **Date mentions**: the recognition machinery (0100/0101) tags dates as mention targets wherever prose is captured; a date-mentioned claim enters the timeline view at that date. Complements structured campaign dates (the chronology fields claims already carry).
- **A dedicated document template with REFERENCE VIEWING** (the templated-presentation system, ADR-0015): renders owned records AND referenced dated claims from across the library, ordered by campaign date (BCE/CE, approximate, era-level) — the template IS the ordered view.
- Kind registry + glossary entry land with the build (test-enforced vocabulary rule).

## Scope (original)

- A retrieval/browsing view that orders events by campaign date using the chronology model.
- Rendering of BCE, CE, approximate, and era-level dates.
- The timeline as a distinct experience from raw document browsing.

## Out of scope

- Editing the timeline through the UI.
- Cross-calendar timelines.
- Non-lore events mixed into the timeline unless separately scoped.

## Acceptance criteria

- [ ] Timeline events are ordered by campaign chronology within the Gregorian calendar.
- [ ] BCE dates display and order correctly.
- [ ] The timeline is distinct from raw document browsing.
- [ ] Sanitized tests and full repository validation pass.
