---
id: TKT-0005
title: Scaffold Campaign Core service
status: backlog
priority: P1
milestone: trustworthy-librarian
depends_on: [TKT-0003]
created: 2026-07-31
updated: 2026-07-31
---

# TKT-0005: Scaffold Campaign Core Service

## Outcome

Create the Python/FastAPI service, typed configuration, migrations, database access boundaries, health endpoint, and initial domain test harness.

## Acceptance criteria

- [ ] Service starts locally and in Compose.
- [ ] Type checking, linting, and tests run from documented commands.
- [ ] Canonical database writes are unavailable outside the Core credential.
- [ ] Domain and adapter packages are separated.
- [ ] One acceptance fixture runs through the domain layer.
