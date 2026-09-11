---
id: TKT-0081
title: Encounter NPC dossier drawer
status: done
priority: P0
milestone: trustworthy-librarian
depends_on: [TKT-0080]
created: 2026-08-25
updated: 2026-08-25
---

# TKT-0081: Encounter NPC Dossier Drawer

## Outcome

A DM running a prepared encounter can inspect an NPC dossier without navigating away from the encounter or losing the current reading position.

## Scope

- Conservatively link canonical NPC names found in prepared encounter prose.
- Open a closable, independently scrollable dossier drawer over the right side of the encounter.
- Keep the encounter mounted and preserve its scroll position.
- Allow direct switching between linked NPCs and preserve dossier scroll positions during the encounter.
- Show identity, background, useful dossier sections, real-play facts, and NPC/DM plans.
- Provide an explicit option to navigate to the full NPC entry.
- Close with the close button or Escape.

## Acceptance criteria

- [x] Clicking a canonical NPC name opens its dossier without changing the selected encounter.
- [x] Closing the dossier returns to the same encounter scroll position.
- [x] The drawer scrolls independently of the encounter.
- [x] Only canonical NPC names and aliases are linked; ordinary text is not guessed as an NPC.
- [x] The dossier exposes a deliberate full-entry navigation action.
- [x] Strict typecheck and UI regression tests pass.
