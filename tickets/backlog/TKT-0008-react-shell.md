---
id: TKT-0008
title: Prototype full-code React shell
status: backlog
priority: P1
milestone: trustworthy-librarian
depends_on: [TKT-0005, TKT-0007]
created: 2026-07-31
updated: 2026-07-31
---

# TKT-0008: Prototype Full-Code React Shell

## Outcome

Create a Windmill full-code React application that calls Campaign Core through a typed client and starts one background job through an isolated Windmill adapter.

## Acceptance criteria

- [ ] UI renders without direct database access.
- [ ] Campaign reads use `CampaignClient`.
- [ ] Background work uses `JobPlatform` rather than scattered Windmill calls.
- [ ] Job progress and failure are visible.
- [ ] Refresh does not silently discard pending operation state.
- [ ] The UI can later be hosted outside Windmill by replacing the job adapter.
