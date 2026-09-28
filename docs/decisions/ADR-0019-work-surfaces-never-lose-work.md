# ADR-0019: Work Surfaces Never Lose Work

- Status: accepted (user ruling 2026-09-24, promoted from the ui-conventions rule of thumb)
- Date: 2026-09-24
- Extends the ADR-0016 guarded edit lifecycle and the Lore working-file precedent (TKT-0099).

## Context

The Lore working file already auto-saves (ui-conventions rule 6), but the guarantee is not system-wide: description prose in the composer lives only in component state until filed, and a candidate-promotion review's edits (row text, includes, state changes) are lost on navigation or refresh. Sean kept the Far Realm Entity prose in a notepad file "because of my lack of trust right now" — the system had trained its user to keep an external backup. That is the failure condition: the user should always trust that nothing they are doing needs to be backed up somewhere else in case the system goes haywire.

## Decision

**Every work surface auto-saves its working state, continuously, before the user thinks about it.** Prose in any composer auto-saves as it is typed. Candidate-promotion state (row text, inclusion, truth-state choices, ordering) auto-saves with it. Restoring is automatic on return — re-entering a workspace restores the working file including the in-flight review state, not just the prose. Nothing awaits an explicit save; explicit actions remain only where canon changes (Approve, File, Create) — the guarded lifecycle (ADR-0016) governs navigation away from dirty editors, and autosave is the safety net beneath it, never a replacement for the review gate.

The trust bar: **the user never keeps a copy elsewhere out of distrust.** If a user exports prose to a notepad "just in case," the surface has failed.

## Consequences

- The description composer (and its claim-breakpoint review, TKT-0146) persists prose + marker text + candidate rows continuously (client-side working store per the Lore precedent; canonical state still changes only through reviewed commits).
- Every new surface ships with autosave in its first cut — the working-file machinery joins the component checklist like the leave-editor guard did (ADR-0016).
- The Lore queue's working file extends to cover its promotion review state.
- ui-conventions rule 6 is superseded by this ADR (its text remains as the pointer).
