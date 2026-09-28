---
id: TKT-0144
title: Brainstorm general review — unfinished works, library display, and Entity promotion
status: backlog
priority: P2
milestone: trustworthy-librarian
depends_on: []
created: 2026-09-22
updated: 2026-09-22
---

# TKT-0144: Brainstorm general review — unfinished works, library display, and Entity promotion

## Context

Sean's live testing (2026-09-22, the open "Wrath of Romulus" WIP): **the system doesn't keep brainstorms grouped in a cohesive way.** Observed: the five thoughts each listed separately under GM planning in the Library's source tree (each row labeled with the session title — the WIP appears five times), and the unpromoted-material audit originally double-counted the session as six records (five per-thought document rows plus the session row; fixed same day — thought documents now fold into the session's single finding). The deeper issue is cohesion: an unfinished brainstorm is ONE work, and every surface should present it as one. This ticket reviews Brainstorm as a whole across three axes.

## Scope when taken up

- **Unfinished works (WIP sessions)**: how open brainstorms live over time — visibility (where an open WIP surfaces: Brainstorm page, Migration page audits, Library?), aging/resurfacing (a WIP left for weeks should be findable, not lost), session count hygiene (many open sessions vs one active), and reopening/resuming flow. The Wrath of Romulus stays open deliberately as the test case.
- **Library display**: brainstorm thought documents currently render as individual rows in the source tree (gm/brainstorming/*, each labeled with the session title → N rows for N thoughts). Rule the display: collapse thoughts under their session (one row, thought count), or hide WIP thought docs from the Library tree entirely until promoted, or another shape — the audit's collapse (one finding per session) is the precedent.
- **Entity promotion**: review the free-surface promotion path from real use — how an unfinished session's thoughts promote (partial promotion of a WIP: promote some thoughts, keep working?), how promotion interacts with session closing, and whether WIP sessions should appear in the qualified-entities/unpromoted audits differently from abandoned ones (open-for-testing vs stalled — an aging rule may be wanted).
- Deliverable: rulings + implementation slices; the Wrath of Romulus is the living fixture throughout.

## Out of scope

- The fixed audit double-count (already collapsed, same day).
- The AI Promotion Assistant (TKT-0137) — this review shapes what it sees, but builds nothing of it.

## Validation evidence

(to record when built)
