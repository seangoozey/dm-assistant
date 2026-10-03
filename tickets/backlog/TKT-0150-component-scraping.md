---
id: TKT-0150
title: Component scraping — assess the app's machinery for reusability and assign permanent shared components
status: backlog
priority: P2
milestone: trustworthy-librarian
depends_on: []
created: 2026-09-30
updated: 2026-09-30
---

# TKT-0150: Component scraping — assess the app's machinery for reusability and assign permanent shared components

## Context

Sean's ruling (2026-09-30, from the encounter-builder architecture question): "much of the machinery in the app as it stands needs to be assessed for reusability and assigned a permanent component if applicable." The russian-doll problem generalizes beyond claim surfaces (TKT-0142 is the claim-card instance of it): machinery accreted per surface, and every new surface (the encounter builder, the orphan actions, capture flows) re-encounters the same question — build on the shared thing, or add another doll.

Known duplication/repetition candidates at ticket time (the inventory starts here, not ends here):

- **Audit-run panels**: five near-identical "Run audit" + notice + count-line panels (qualified, unpromoted, link, orphan, life-status) — one AuditPanel shape.
- **Evidence-item rows**: lore evidence items, gathered claims, orphan rows, dossier contexts — one row idiom with chips + text + source line.
- **Suggestion machinery**: deterministic name matching duplicated client-side (Lore gather, orphan suggestions server-side, session mentions) — one recognition module.
- **Job polling**: three hand-rolled poll loops (extraction, prose drafts, promotion suggestions, orphan check) — one poll hook.
- **Working-file autosave**: the ADR-0019 pattern implemented per surface (description composer, Lore working item, orphan panel pending) — one working-file module.
- **Queue/chip/select idioms**: role chips, vocabulary chips, truth-state selects, queue panels across pages.
- **Editor guards, drawers/trays, commissioning patterns** for Windmill-backed ops.

## Scope when taken up

1. **The inventory**: sweep `App.tsx` (+ siblings) cataloging machinery by shape — rendered components, hooks, client utilities — marking each: shared-already / duplicated / single-use-but-candidate / single-use-keep.
2. **Assignment**: for every duplicated or candidate piece, assign its **permanent component** (name, props/slots, home file) — the deliverable is the REGISTRY, not the refactor: a "Permanent components" section in `docs/architecture/ui-conventions.md` (and the living Conventions page) naming what exists to be reused.
3. **Phased extraction at natural touchpoints** (no big-bang rewrite — the 0142 principle): extract when a surface touching the machinery is next worked; new surfaces are BORN on the shared component (the standing rule).
4. **Slot composition over flags** (0142's guard) applies to every extracted component.

## Out of scope

- The claim card itself (TKT-0142 — this ticket's registry lists it as the claim-surface entry; its convergence stays there).
- Backend service consolidation (Campaign Core's application layer is already facade-shaped).

## Validation evidence

(to record when built)
