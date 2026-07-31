# Ticket System

Tickets are version-controlled Markdown files. The directory is the workflow state.

## States

- `backlog/`: valid work not yet ready.
- `ready/`: sufficiently specified and unblocked.
- `in-progress/`: actively being implemented.
- `blocked/`: cannot proceed; the blocker is documented.
- `done/`: acceptance criteria and validation are complete.

## Ticket lifecycle

1. Create a ticket from `templates/ticket.md`.
2. Assign the next `TKT-####` identifier.
3. Add it to `tickets/index.md`.
4. Move it to `ready` only when dependencies and acceptance criteria are clear.
5. Move it to `in-progress` before implementation.
6. Record decisions, implementation notes, validation commands, and results.
7. Move it to `done` and update the index in the same commit.

Do not use ticket filenames as permanent domain identifiers. Git history preserves ticket movement.

## Priorities

- `P0`: blocks all meaningful progress or protects data integrity.
- `P1`: required for the current milestone.
- `P2`: important but can follow the milestone.
- `P3`: optional or exploratory.

## Ticket quality

A good ticket describes the outcome and acceptance evidence without prematurely dictating implementation details. If a decision needs durable explanation, add an ADR rather than burying it in a ticket.
