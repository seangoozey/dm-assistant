---
id: TKT-0083
title: Polish prepared encounters for table use
status: done
priority: P1
milestone: trustworthy-librarian
depends_on: [TKT-0081, TKT-0082]
created: 2026-08-26
updated: 2026-08-26
---

# TKT-0083: Polish Prepared Encounters for Table Use

## Outcome

Prepared encounters remain readable under table pressure, including clean attendee presentation, an unobtrusive collapsible NPC dossier handle, and compact controls that do not compete with read-alouds, checks, or live notes.

## Scope

- Replace the current dossier handle with a visually integrated rail control.
- Render Markdown attendee tables as readable responsive tables rather than raw monospaced text.
- Tune section rhythm, control density, and narrow-screen behavior with the notes timeline and dossier both available.
- Add a focused table mode only where it materially improves live use.

## Acceptance criteria

- [x] Attendees render as a responsive semantic table.
- [x] The dossier collapse/expand handle reads as part of the drawer rail.
- [x] Encounter content, notes, and the NPC dossier remain usable together at common laptop widths.
- [x] Keyboard and accessible names remain intact.

## Progress

- Reduced the NPC dossier handle from a 34-pixel grip/rail to an 18-pixel grip and 22-pixel collapsed rail.
- Added a matching collapsible Library rail on the left. It preserves the selected entry and document scroll state, remembers the preference locally, and lets the encounter expand into the released space.
- Added accessible expand/collapse names and focused regression coverage; strict TypeScript and 45 focused tests pass.
- Markdown encounter matrices now render as semantic tables with column headers, readable typography, alternating row treatment, wrapped content, and contained horizontal scrolling. The parser preserves wiki-link display aliases and escaped pipes.
- Replaced the floating dossier tab with a full-height integrated rail control. Its visible grip, focus treatment, and accessible expand/collapse names remain available in both open and collapsed states.
- Added laptop-width behavior that narrows the Library and dossier before the mobile drawer breakpoint, keeping encounter content usable alongside table notes and the NPC dossier.
- Verified the renderer against the live Exile Camp attendee table and other encounter matrices. Strict TypeScript and 50 focused UI/Windmill tests pass; the rebuilt raw app deployed successfully.
