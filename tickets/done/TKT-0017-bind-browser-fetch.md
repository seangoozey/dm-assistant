---
id: TKT-0017
title: Bind CampaignClient browser fetch correctly
status: done
priority: P1
milestone: trustworthy-librarian
depends_on: [TKT-0008]
created: 2026-08-01
updated: 2026-08-01
---

# TKT-0017: Bind CampaignClient Browser Fetch Correctly

## Outcome

Ensure the deployed React shell can call Campaign Core without invoking the browser's native `fetch` with an illegal receiver.

## Acceptance criteria

- [x] `HttpCampaignClient` invokes native browser `fetch` with the global receiver.
- [x] A regression test reproduces the receiver-sensitive behavior.
- [x] React tests, strict type checking, and the Windmill raw-app build pass.
- [x] Deployment instructions identify the required app redeployment.

## Validation evidence

- A receiver-sensitive fetch double throws `TypeError: Illegal invocation` unless called with `globalThis`; the regression test passes through `HttpCampaignClient`.
- Nine React tests pass.
- Strict TypeScript checking and the Windmill raw-app lint/build pass.
- Windmill metadata generation reports all app metadata up to date.

## Deployment and rollback

Redeploy the scoped Windmill workspace with `windmill/deploy_workspace.py --apply` to replace the existing browser bundle. No database migration or service restart is required. Rollback is restoration and redeployment of the previous `campaignClient.ts`; it would also restore the reported browser failure.
