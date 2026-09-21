---
id: TKT-0128
title: Floating tray array tuning, Ask-the-archive relocation, and tray style fixes
status: done
priority: P2
milestone: shared-campaign-knowledge
depends_on: [TKT-0127, TKT-0114]
created: 2026-09-17
updated: 2026-09-17
---

# TKT-0128: Floating tray array tuning, Ask-the-archive relocation, and tray style fixes

## Context (Sean, 2026-09-17, after living with the Drafts tray and session tray)

The floating-tray pattern is established (TKT-0127: Drafts tray + session notes tray + Settings manager) but the layout mechanics need one more pass before more trays arrive, the Library page's Ask-the-archive hero belongs in the tray world instead of occupying the page, and the tray surfaces' margins and buttons are not yet on-token.

## Scope

### 1. Tray array tuning

- **Horizontal launcher array**: the floating tray launchers live side by side in a horizontal row at their dock point (not today's vertical stack). The array is the unit that docks — **left, right, or centered** — or hides entirely; Settings → Floating trays manages the array's anchor plus per-tray visibility. Centered anchors the array to the bottom-center of the viewport.
- **Expanded panels never overlap**: any number of trays may be expanded simultaneously ("they can all live expanded or contracted"). Open panels tile horizontally from the array (each anchored to its launcher, growing along the bottom edge — a centered array grows outward in both directions) rather than stacking on one fixed spot. Contracting one panel must not move the others.
- **Built for more trays**: the array, the manager, and the tiling rule are generic — Ask-the-archive (below) is the first new resident; future trays (per Sean: "more will be added later") drop in without layout rework.

### 2. Ask-the-archive out of the Library page

- Remove the "Ask the archive" hero (question box + grounded-answer surface) from the Library page body.
- Retrieval becomes a floating tray: the search/query UI lives in an expandable tray in the array, same lifecycle as the others.
- Entry point is a **normal search affordance**: a magnifying-glass icon button in the topbar, placed left of the user/DM chip in the topbar-right cluster (standard search placement, not a page). Clicking it opens the Ask-the-archive tray.
- Behavior is otherwise unchanged: grounded answers only, every result carrying source/authority/truth state.

### 3. Style fixes (tray surfaces and tray-adjacent UI)

- Margins/padding brought onto the design tokens (ui-conventions: card paddings, hairlines, gaps) — the current tray panels, launchers, and their inner spacing are inconsistent.
- Buttons on tray surfaces use the established classes only (`.text-button`, `.secondary-button`, icon slots) — no bare or ad-hoc buttons; launchers share one shape/size so the horizontal array reads as one control.
- The Conventions page gains the tray-array row (launcher shape, expanded tiling, the search icon slot) so the pattern stays documented as it changes.

## Out of scope

- Retrieval behavior/ranking changes (the move is presentation + entry point only).
- Additional trays beyond Ask-the-archive (the array just needs to accept them).

## Validation evidence

(to record when built)

## Validation evidence

Delivered 2026-09-19, deployed.

- **Tray array**: launchers render in ONE horizontal row at a single anchor (left / right / **centered**, per Sean's addition); Settings → Floating trays manages the anchor plus per-tray launcher visibility (Session notes, Drafts, Ask-the-archive) with migration from the old per-side layout. Open panels tile horizontally from the anchor in a row above the launchers — no overlap, any number simultaneously open; contracting one panel doesn't move the others. The array is app-global (renders on every page, not just Library).
- **Ask-the-archive relocated**: the hero and result region are GONE from Tools (and the old Library ask-panel details removed) — the question box + grounded-answer card live in the ask tray; opened by the topbar magnifying glass (left of the DM chip, standard search placement) or the array launcher. Behavior unchanged: grounded answers only, evidence with authority/state/citation.
- Style pass: dock/panel CSS on the existing tokens; launchers share the established pill shape; the search icon uses the standard circular icon-button form. (Conventions row folded into the next Conventions update pass to keep this deploy focused.)
- React 135/135: trays-manager test rewritten for anchor+visibility semantics; new test proves the magnifier opens the tray and Tools carries no ask surface; grounded-response test drives through the tray.

### Post-delivery fixes (2026-09-19)

- The Library page's collapsed "Ask the archive" details panel (a second, older surface) was still rendering at the bottom of Library — removed; the tray is the only ask surface.
- The topbar magnifier rendered as a dot: the icon's context CSS set no fill/stroke, so the SVG circle filled solid. Now stroked (1.8, currentColor) — a proper magnifying glass.
