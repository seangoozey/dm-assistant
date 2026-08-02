---
id: TKT-0004
title: Scaffold private TrueNAS stack
status: done
priority: P1
milestone: trustworthy-librarian
depends_on: []
created: 2026-07-31
updated: 2026-08-01
---

# TKT-0004: Scaffold Private TrueNAS Stack

## Outcome

Create a pinned Docker Compose development stack for Windmill Community Edition, Campaign Core, and logically separated Windmill and campaign PostgreSQL databases.

## Acceptance criteria

- [x] Stack starts privately on a development machine and maps cleanly to TrueNAS datasets.
- [x] Campaign and Windmill credentials are distinct.
- [x] Only intended UI ports are exposed.
- [x] Legacy source mount is read-only.
- [x] Health checks and persistent volumes are defined.
- [x] `.env.example` contains no secrets.
- [x] Backup and restore commands are documented.

## Validation

Implemented `deploy/compose.yaml`, `deploy/compose.truenas.yaml`, `deploy/.env.example`, the temporary health-only Campaign Core placeholder, and `deploy/README.md`.

`python tests/validate_compose_policy.py` passes and verifies six services, exact image tags, two isolated database networks and credential sets, one published Windmill UI port, service health checks, persistent volumes, TrueNAS dataset bindings, a profile-gated read-only Starfall mount, and the absence of real passwords in the environment example. `python -m py_compile deploy/placeholders/campaign_core_health.py tests/validate_compose_policy.py` and `git diff --check` pass.

Runtime validation completed on Docker Engine 29.6.2 with Docker Compose 5.3.1:

- `docker compose config --quiet` passed for the development file and the merged TrueNAS override.
- The five default services started and reached `running (healthy)`: two PostgreSQL databases, Windmill server, Windmill worker, and the health-only Campaign Core placeholder.
- Windmill reported `status=healthy`, `database_healthy=true`, and one live worker. The Core placeholder returned `canonical_writes=false`.
- Docker inspection confirmed that only Windmill published a host port, bound to `127.0.0.1:8000`. Campaign Core and both databases had no published host port.
- Environment-key inspection confirmed Windmill server/worker received only `DATABASE_URL`, Core received only `CAMPAIGN_DATABASE_URL`, and each PostgreSQL container received its own database variables.
- Custom-format logical dumps were created for both databases. Each restored successfully into an isolated verification database and passed `SELECT 1`. The Windmill dump was 670,842 bytes; the empty campaign scaffold dump was 827 bytes.
- Docker Desktop rejected the live UNC path as a bind source. The Compose mount remains declaratively read-only, the merged TrueNAS configuration validates with a native dataset path, and the Windows limitation is documented in `deploy/README.md` and `.env.example`.
- Disposable restore databases, dump files, containers, networks, and volumes were removed after validation. No campaign source or persistent user data was deleted.

## Implementation notes

Windmill CE is pinned to release 1.775.2, PostgreSQL to 16.14 on Alpine 3.23, and the temporary Core health container to Python 3.13.14 on Alpine 3.23. The general Windmill worker receives only Windmill database credentials and does not mount the legacy source or Docker socket. The isolated source-check profile receives neither a network nor database credentials.

TKT-0005 replaces the health-only Core placeholder with the real Campaign Core image. TKT-0007 should re-evaluate the privileged Windmill worker setting while validating Windmill's namespace isolation on the target host.

## Follow-ups

- Replace the Campaign Core placeholder in TKT-0005.
- Exercise the live read-only source-check profile on TrueNAS using its native dataset path during TKT-0007 deployment validation.
