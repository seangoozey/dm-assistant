---
id: TKT-0019
title: Proxy raw-app campaign reads through Windmill
status: done
priority: P1
milestone: trustworthy-librarian
depends_on: [TKT-0017, TKT-0018]
created: 2026-08-01
updated: 2026-08-01
---

# TKT-0019: Proxy Raw-App Campaign Reads Through Windmill

## Outcome

Make grounded Ask requests work in Windmill's deployed raw-app sandbox by implementing the Windmill `CampaignClient` adapter with a typed backend runnable instead of direct browser fetch.

## Acceptance criteria

- [x] The deployed Windmill entrypoint performs campaign reads through `CampaignClient` and a generated backend binding.
- [x] The backend runnable calls the absolute internal `CAMPAIGN_CORE_URL` and receives no database credential.
- [x] `HttpCampaignClient` remains available for future hosting outside Windmill.
- [x] Browser query-parameter configuration is no longer required for the Windmill app.
- [x] Tests cover the Windmill adapter and backend request/error behavior.
- [x] Workspace metadata, source policy, test lifecycle, and architecture documentation are consistent.

## Validation evidence

- Ten React tests pass, including the Windmill adapter, absolute backend request, successful structured response, and Campaign Core error propagation.
- Strict TypeScript checking and the Windmill raw-app build pass with three backend runnables.
- Source policy validates the exact 27-file Windmill scope and rejects a direct-browser client in the deployed entrypoint or a database credential in the query runnable.
- The updated app deployed successfully to `dm-assistant-dev`; a subsequent metadata check and deployment preview reported zero changes.
- The stable deployed app route returned HTTP 200 while Windmill and Campaign Core were healthy.
- The full repository gate passes: 101 Python tests, 10 React tests, 38 retrieval cases, Ruff, mypy, infrastructure policy, and raw-app build checks.

## Migration and rollback

No database migration is required. Rollback would restore the direct-browser `HttpCampaignClient` entrypoint and query-parameter configuration, but that implementation is known not to work in Windmill's raw-app sandbox. The backend runnable owns no durable state.
