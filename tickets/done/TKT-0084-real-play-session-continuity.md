---
id: TKT-0084
title: Preserve real-play sessions across encounter boundaries
status: done
priority: P0
milestone: session-support
depends_on: [TKT-0038, TKT-0080, TKT-0082]
created: 2026-08-27
updated: 2026-08-30
---

# TKT-0084: Preserve Real-Play Sessions Across Encounter Boundaries

## Outcome

A live-play session is the chronological container for what happened. It may begin outside an encounter, move through several encounters, or stop partway through one. An encounter may span several sessions. Closing a session preserves where play stopped without implying that an encounter or any authored section was completed.

## Domain boundary

- A session and an encounter have a many-to-many relationship.
- A table note may have no encounter context, encounter-level context, or section-level context.
- Encounter participation is operational play context, not canonical evidence that authored material occurred.
- Closing a session never completes an encounter automatically.
- Encounter progress tracks visited context and an optional resume point, not a linear percentage.
- The session note remains the immutable evidence source; encounter/run state is mutable table-support state.

## Scope

- Represent the distinct encounters touched by an open session and preserve their first/last chronological activity.
- Permit general session notes with no encounter association.
- Preserve an optional encounter/section resume checkpoint when a session is closed.
- Keep encounter lifecycle independent, with explicit `not_started`, `in_progress`, `completed`, and `abandoned` operational states.
- Allow a later session to resume an in-progress encounter without reopening the earlier session.
- Show the open session timeline across navigation and across multiple encounters.
- At session closeout, assemble all notes strictly by capture time and show the encounters touched plus any saved resume point.
- Feed the resulting immutable session note into the streamlined real-play claim review: edit, split, abandon, commit, and automatically advance.
- Refresh affected canonical entries after applied observations.

## Acceptance criteria

- [x] A session can contain chronological notes from no encounter, one encounter, or multiple encounters.
- [x] One encounter can be linked to multiple sessions without duplicating its prepared content.
- [x] Moving between encounters does not close the session or lose its timeline.
- [x] Closing a session does not mark any encounter complete.
- [x] A partial encounter can retain a resume checkpoint and be resumed in a later session.
- [x] Encounter completion or abandonment requires an explicit DM action.
- [x] General notes and encounter-context notes assemble together in capture order.
- [x] Closeout shows and preserves the encounter context without inserting operational labels into claim text.
- [x] Real-play assertions can be reviewed efficiently and applied with receipts through Campaign Core.
- [x] Focused frontend, Campaign Core, PostgreSQL, and full repository validation pass.

## First implementation slice

- Add a typed session encounter summary/checkpoint to Campaign Core's session-run read model.
- Derive touched encounters from durable notes while preserving context-free notes.
- Add explicit checkpoint persistence without coupling it to encounter completion.
- Expose the open session and its cross-encounter timeline outside a single encounter document.

## Out of scope

- Assuming authored encounter order matches play order.
- Automatically marking unvisited or earlier sections complete.
- Treating prepared encounter text as observed play.
- Inventing NPC reactions or PC decisions during closeout.

## Progress

- Accepted ADR-0013: sessions and encounters are independent many-to-many operational contexts; session close and encounter completion are intentionally unrelated.
- Migration `0033` gives durable table notes an explicit `general` or `encounter` context. General notes carry no fabricated encounter or section identity.
- Campaign Core derives each run's touched encounters, first/last activity, last visited section, and note count from the chronological durable notes.
- The session timeline can now be opened from anywhere in the Library, captures general notes outside encounters, names every encounter touched, and assembles all notes strictly by capture time.
- `New Session` is now the single entry point: start a live session or write a completed session log directly. An open live session reopens instead of offering a competing start path.
- Migration `0034` persists encounter lifecycle, optional section resume checkpoints, and the many-to-many session/encounter association independently from canonical claims.
- Migration `0035` backfills any pre-upgrade durable encounter notes without overriding an explicit lifecycle decision.
- The session panel surfaces unfinished encounters, resumes them into a later session, and requires explicit Complete or Abandon actions. Any encounter note can become the next-session checkpoint.
- Session closeout now previews touched encounters and the saved resume point separately from the editable chronological evidence text.
- Applying a direct-input observation refreshes library and source projections after the authoritative receipt without allowing a refresh failure to misreport the applied transaction.
- Validation: 307 Campaign Core tests, 64 React tests, Ruff, mypy, strict typecheck, Windmill raw-app build, 38 retrieval cases, and the disposable PostgreSQL two-session checkpoint integration test pass.
