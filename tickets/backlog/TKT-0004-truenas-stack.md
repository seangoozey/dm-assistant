---
id: TKT-0004
title: Scaffold private TrueNAS stack
status: backlog
priority: P1
milestone: trustworthy-librarian
depends_on: []
created: 2026-07-31
updated: 2026-07-31
---

# TKT-0004: Scaffold Private TrueNAS Stack

## Outcome

Create a pinned Docker Compose development stack for Windmill Community Edition, Campaign Core, and logically separated Windmill and campaign PostgreSQL databases.

## Acceptance criteria

- [ ] Stack starts privately on a development machine and maps cleanly to TrueNAS datasets.
- [ ] Campaign and Windmill credentials are distinct.
- [ ] Only intended UI ports are exposed.
- [ ] Legacy source mount is read-only.
- [ ] Health checks and persistent volumes are defined.
- [ ] `.env.example` contains no secrets.
- [ ] Backup and restore commands are documented.
