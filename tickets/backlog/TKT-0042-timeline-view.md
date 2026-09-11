---
id: TKT-0042
title: Timeline view
status: backlog
priority: P2
milestone: trustworthy-librarian
depends_on: [TKT-0041]
created: 2026-08-04
updated: 2026-08-05
---

# TKT-0042: Timeline View

## Outcome

The canonical timeline (including BCE content) is viewable as a structured, ordered experience rather than raw Markdown, leveraging the chronology model and the campaign's actual dates.

## Context

`lore/timeline.md` is player-facing lore with BCE dates (20,000 BCE, 15,000 BCE) and CE ranges that drove the chronology design. Rendering it as raw Markdown loses the ordering and structure the chronology model now provides. This is the read-side payoff for TKT-0030.

Read `docs/decisions/ADR-0007-campaign-chronology.md`, `docs/product/vision.md`, and TKT-0041.

## Scope

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
