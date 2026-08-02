---
id: TKT-0008
title: Prototype full-code React shell
status: done
priority: P1
milestone: trustworthy-librarian
depends_on: [TKT-0005, TKT-0007]
created: 2026-07-31
updated: 2026-08-01
---

# TKT-0008: Prototype Full-Code React Shell

## Outcome

Create a Windmill full-code React application that calls Campaign Core through a typed client and starts one background job through an isolated Windmill adapter.

## Acceptance criteria

- [x] UI renders without direct database access.
- [x] Campaign reads use `CampaignClient`.
- [x] Background work uses `JobPlatform` rather than scattered Windmill calls.
- [x] Job progress and failure are visible.
- [x] Refresh does not silently discard pending operation state.
- [x] The UI can later be hosted outside Windmill by replacing the job adapter.

## Validation evidence

- Eight Vitest tests cover grounded evidence and citations, requester visibility, Campaign Core errors, the job adapter, refresh restoration, visible job-start failure, and runtime configuration.
- Strict TypeScript checking and the Windmill raw-app lint/build pass.
- The full deterministic repository gate passes: 101 Python tests passed, 12 environment-dependent tests skipped, 38 retrieval cases validated, and Ruff plus mypy reported no issues.
- The repository source-policy validator admits exactly the reviewed Windmill folder and app tree, rejects direct database access, and verifies that Windmill SDK calls remain inside `JobPlatform`.
- A disposable Windmill workspace served the app route, executed the Campaign Core health job successfully, and reported zero changes on the final deployment preview.
- A real cross-origin request to the disposable Campaign Core returned `insufficient_evidence` with zero evidence for an unsupported question; both the response and preflight carried the configured exact origin.
- The in-app browser runtime was unavailable in this execution session. Rendered interaction, failure, and refresh behavior were therefore validated through the component suite rather than a manual visual pass.
- `npm audit` reports no vulnerabilities for the app dependency tree. The workspace CLI's previously documented low-severity development-only finding is unchanged.

## Migration and rollback

No campaign schema migration is required. Rollback is removal of the raw-app source and its `wmill-lock.yaml` entries followed by a reviewed scoped workspace deployment; Campaign Core's optional CORS setting may then be cleared.

## Follow-up

Select and ticket the first planning-workspace vertical slice. Keep grounded retrieval through `CampaignClient` and introduce new asynchronous operations only through `JobPlatform`.
