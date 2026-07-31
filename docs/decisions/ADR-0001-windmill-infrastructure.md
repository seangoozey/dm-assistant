# ADR-0001: Windmill as Application Infrastructure

- Status: proposed
- Date: 2026-07-31

## Context

The project needs Docker-compatible job execution, scheduling, retries, progress, webhooks, workers, and a customizable interface without relying on an autonomous agent to choose mandatory steps.

## Decision

Use Windmill Community Edition tentatively as Version 1 application infrastructure and use its full-code React app for the initial UI. Use flows only where orchestration adds value.

## Boundaries

- Windmill does not own domain rules or canonical mutations.
- Windmill operational history is not the durable campaign audit.
- UI integration is isolated behind a job adapter.
- Windmill uses its own database and credentials.

## Consequences

- Background infrastructure does not need to be built from scratch.
- Workspace resources must be exported and reproducibly deployed.
- Community-edition limitations must not become domain limitations.
- Replacing Windmill remains possible but would require a new job-platform adapter.

## Acceptance conditions

- Full-code app supports the two-panel workspace.
- A background job reports progress through the UI.
- Campaign Core remains usable without a Windmill flow.
- Workspace source can recreate a disposable Windmill instance.
