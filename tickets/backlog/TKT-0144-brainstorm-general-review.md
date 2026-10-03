---
id: TKT-0144
title: Brainstorm general review — unfinished works, library display, and Entity promotion
status: backlog
priority: P2
milestone: trustworthy-librarian
depends_on: []
created: 2026-09-22
updated: 2026-09-28
---

# TKT-0144: Brainstorm general review — unfinished works, library display, and Entity promotion

## Context

Sean's live testing (2026-09-22, the open "Wrath of Romulus" WIP): **the system doesn't keep brainstorms grouped in a cohesive way.** Observed: the five thoughts each listed separately under GM planning in the Library's source tree (each row labeled with the session title — the WIP appears five times), and the unpromoted-material audit originally double-counted the session as six records (five per-thought document rows plus the session row; fixed same day — thought documents now fold into the session's single finding). The deeper issue is cohesion: an unfinished brainstorm is ONE work, and every surface should present it as one. This ticket reviews Brainstorm as a whole across three axes.

## Scope when taken up

- **Unfinished works (WIP sessions)**: how open brainstorms live over time — visibility (where an open WIP surfaces: Brainstorm page, Migration page audits, Library?), aging/resurfacing (a WIP left for weeks should be findable, not lost), session count hygiene (many open sessions vs one active), and reopening/resuming flow. The Wrath of Romulus stays open deliberately as the test case.
- **Library display**: brainstorm thought documents currently render as individual rows in the source tree (gm/brainstorming/*, each labeled with the session title → N rows for N thoughts). Rule the display: collapse thoughts under their session (one row, thought count), or hide WIP thought docs from the Library tree entirely until promoted, or another shape — the audit's collapse (one finding per session) is the precedent.
- **Entity promotion**: review the free-surface promotion path from real use. FACT PINNED 2026-09-28: the current flow CLOSES THE SESSION ON ANY COMMIT ("Approve promotion · N claims + M new records", then close with the applied proposal) — partial promotion of a WIP (promote some thoughts, keep working) is genuinely impossible today, not merely unreviewed. Rulings needed: partial promotion shape, how promotion interacts with session closing, and whether WIP sessions should appear in the qualified-entities/unpromoted audits differently from abandoned ones (open-for-testing vs stalled — an aging rule may be wanted).
- Deliverable: rulings + implementation slices; the Wrath of Romulus is the living fixture throughout.

### Library display DELIVERED (2026-10-02, deployed, from Sean's live ruling)

"Let's rename GM Planning to Brainstorms, Group all the current Brainstorm The Wrath of Romulus into a single listing, we'll need a template for it at some point. Give it an in-progress icon."

- **The family renamed**: `gm/brainstorming/` is its own **"Brainstorms"** family in the Library's entries view (gm/ stragglers — campaign-bible.md, plot-threads.md — keep "GM Planning" until they migrate to Campaign, TKT-0151).
- **One listing per brainstorm session**: the direct thought docs (`gm/brainstorming/direct/{sessionId}/{thoughtId}`) group under their session title from a new `GET /campaign/brainstorm-sessions` read (title, open state, thought count). Single-file legacy brainstorms (dated .md files) list individually. **The Wrath of Romulus = one listing, "5 thoughts."**
- **In-progress icon**: a new `draft` RecordIcon (pencil-on-paper, stroked) marks OPEN sessions; tooltip "Open brainstorm — in progress." ADR-0022's refreshLibrary also refreshes the brainstorm sessions read.
- **Template noted for 0144's later scope**: a dedicated brainstorm template joins the Campaign/Timeline template family when picked up.
- React 93/93 (the grouping + icon + family split + gm/ stragglers test); backend brainstorm tests green.

## Out of scope

- The fixed audit double-count (already collapsed, same day).
- The AI Promotion Assistant (TKT-0137) — this review shapes what it sees, but builds nothing of it.

## Validation evidence

(to record when built)
