---
id: TKT-0007
title: Establish Windmill source deployment
status: backlog
priority: P1
milestone: trustworthy-librarian
depends_on: [TKT-0004]
created: 2026-07-31
updated: 2026-07-31
---

# TKT-0007: Establish Windmill Source Deployment

## Outcome

Make repository source capable of recreating the Windmill development workspace through controlled CLI synchronization.

## Acceptance criteria

- [ ] `wmill.yaml` uses narrow, documented scopes.
- [ ] Secrets are excluded.
- [ ] Deployment previews changes before applying them.
- [ ] A disposable workspace can be recreated from repository source.
- [ ] Repeating deployment is idempotent.
- [ ] Container rebuild and workspace deployment responsibilities are documented separately.
