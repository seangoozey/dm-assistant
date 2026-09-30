---
id: TKT-0119
title: Responsive layout strategy — named breakpoints, container queries, and a tested crush path
status: backlog
priority: P2
milestone: trustworthy-librarian
depends_on: []  # TKT-0114 (Settings) shipped 2026-09-16 — the nav-overflow decision is unblocked
created: 2026-09-14
updated: 2026-09-28
---

# TKT-0119: Responsive layout strategy — named breakpoints, container queries, and a tested crush path

## Context (Sean, 2026-09-14, after the clock chip crowded the topbar)

Narrow-window problems keep appearing one component at a time (topbar crowding, panel inputs hanging off the edge, elements pushed out of their grid columns). Fixes so far are ad-hoc media queries per incident. Sean's ruling for the topbar establishes the pattern the whole app should follow: **persistent chrome (date, user) always stays upper-right; identity labels collapse gracefully (brand → logo only, DM badge → avatar only, clock → date only); navigation is the flexible middle; nothing wraps or pushes.** Migration/Conventions become hideable from Settings (TKT-0114) rather than auto-hiding.

## Scope when taken up

- **Named breakpoint set**: one documented, commented set of shared breakpoints (matching the tiers already shipped: 1180 nav gap, 1060 brand collapse, 940 archive-label collapse, 820 clock-kicker collapse) — no scattered magic numbers; new media queries must reference the named tiers.
- **Container queries where components, not windows, are the unit**: dropdown panels (campaign clock, encounter notes, filters) and cards should size to their container (`@container`), which fixes "hangs off the edge" class bugs at the root instead of per-instance media queries.
- **Crush-path testing**: a documented narrow-viewport pass (e.g. 375/768/1024 widths) added to the visual conventions — either a lightweight Playwright screenshot check or a Conventions-page live demonstration row, decided at pickup; at minimum, the topbar rules above become enforceable React assertions (date and identity present and positioned right at narrow widths).
- **Nav overflow policy** (UNBLOCKED — Settings hideable-nav shipped 2026-09-16): today the nav scrolls horizontally when crushed; decide whether scroll remains the fallback or hidden-by-preference replaces it.
- **Wide-workspace crush scope** (added 2026-09-28): the app's widest surfaces postdate this ticket's writing — the Lore working page, the Phase 2 Migrations page, and the viewport-height workspaces. The crush pass must cover them, not just the topbar pattern.
- Conventions page + `docs/architecture/ui-conventions.md` gain a "Responsive behavior" section naming the tiers and the collapse order.

## Out of scope

- Redesigning any page's layout; this ticket is about the strategy and the shared machinery, applied first to the topbar pattern already shipped.
