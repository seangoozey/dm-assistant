# ADR-0002: Dedicated Campaign Core

- Status: proposed
- Date: 2026-07-31

## Context

Canon safety cannot depend on LLM judgment, frontend behavior, or correct construction of every Windmill flow.

## Decision

Create a dedicated Python/FastAPI Campaign Core that owns domain invariants and all authoritative mutations.

## Consequences

- Only Core receives canonical write credentials.
- Windmill and the React UI call typed Core APIs.
- Promotions can be atomic, idempotent, version-checked, and tested independently.
- The project adds one service but gains a clear trust boundary.

## Acceptance conditions

- Core enforces authority, PC agency, proposal versions, and approval scope.
- A forced mid-promotion failure commits no partial changes.
- Retrying an applied command creates no duplicates.
