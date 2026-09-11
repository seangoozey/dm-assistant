# ADR-0013: Sessions and Encounters Are Independent Many-to-Many Contexts

- Status: accepted
- Date: 2026-08-27

## Context

Actual play does not follow prepared encounter boundaries. A session may begin outside an encounter, stop halfway through one, or move through several encounters. An encounter may continue across multiple sessions. Treating either record as the other's lifecycle container would falsely imply that prepared sections occurred or that closing a session completed an encounter.

## Decision

- The live session is the chronological container for table observations.
- A table note has either general session context or optional encounter and section context.
- Sessions and encounters are many-to-many through operational run context; prepared encounter content is not copied into a session.
- Encounter participation and resume position are mutable table-support state, not canonical evidence.
- Closing a session never completes an encounter. Completion and abandonment are explicit DM actions.
- Encounter progress records visited context and an optional resume point, never a linear percentage or an assumption that earlier authored sections were played.
- The assembled immutable session note, not operational encounter state, supplies provenance for real-play claims.

## Consequences

- One chronological session log can contain general notes and notes from several encounters.
- An unfinished encounter can be resumed from a later session without reopening or rewriting the earlier session.
- Real-play truth remains grounded in captured observations, while the runner can remember where play stopped.
- The interface must keep an open session timeline available across document navigation.

## Alternatives considered

- **One encounter per session:** rejected because it does not match actual play.
- **Automatically complete an encounter when a session closes:** rejected because session boundaries do not establish encounter outcomes.
- **Infer linear progress from authored section order:** rejected because encounter play is nonlinear.

