---
id: TKT-0007
title: Establish Windmill source deployment
status: done
priority: P1
milestone: trustworthy-librarian
depends_on: [TKT-0004]
created: 2026-07-31
updated: 2026-08-01
---

# TKT-0007: Establish Windmill Source Deployment

## Outcome

Make repository source capable of recreating the Windmill development workspace through controlled CLI synchronization.

## Acceptance criteria

- [x] `wmill.yaml` uses narrow, documented scopes.
- [x] Secrets are excluded.
- [x] Deployment previews changes before applying them.
- [x] A disposable workspace can be recreated from repository source.
- [x] Repeating deployment is idempotent.
- [x] Container rebuild and workspace deployment responsibilities are documented separately.

## Implementation

Added a pinned Windmill CLI project and lockfile, a narrow `wmill.yaml`, folder metadata, a locked Campaign Core health script, and a cross-platform Python deployment wrapper under `windmill/`. The configuration owns only `f/dm_assistant/**`; it excludes variables, resources, resource types, secrets, flows, apps, schedules, triggers, users, groups, settings, encryption keys, and workspace dependencies.

The wrapper uses an external named CLI profile, previews by default, and requires explicit `--apply`. Apply always runs another dry-run first, repeats safety-critical skip flags on the command line, verifies the scoped source digest did not change between preview and push, and never enables secret or full-diff flags. CLI and server are pinned to `1.775.2`.

The seeded job calls Campaign Core through `CAMPAIGN_CORE_URL`; it does not accept a caller-controlled URL and has no database credential. Compose now supplies that non-secret service endpoint only to the Windmill worker.

Container and workspace responsibilities are documented separately in `deploy/README.md`, `windmill/README.md`, and the architecture deployment specification. Worker privilege was re-evaluated: the pinned worker's namespace isolation retains privileged mode, while the worker remains without a Docker socket, campaign source mount, or Campaign PostgreSQL credential. This is an explicit private-development infrastructure risk, not authority to weaken isolation silently.

## Validation evidence

- `python tests\validate_repository.py` passed: Ruff over Campaign Core, tests, and Windmill source; strict mypy over 37 Campaign Core and 2 Windmill source files; 99 tests passed with 12 external-prerequisite skips; Compose, Windmill source, and 38-case retrieval validations all passed.
- `tests/validate_windmill_source.py` enforces the exact four-file synchronization scope, server-matched CLI pin, lock requirement, excluded resource classes, secret-pattern checks, preview-before-apply ordering, and command-line safety flags.
- `npm ci` installed the exact lockfile and `wmill --version` reported `1.775.2`. The full audit reports two linked low-severity entries for `GHSA-g7r4-m6w7-qqqr` in the CLI's transitive esbuild development dependency; the affected Windows development-server behavior is not used by this workflow, and no compatible audit fix exists. The production-only audit reports zero vulnerabilities. This accepted tooling risk is documented in `windmill/README.md`.
- A fresh isolated five-service Compose project reached healthy state with Windmill CE `1.775.2`, Campaign Core, a worker, and two PostgreSQL databases.
- A new disposable workspace was created from repository source. The deployment preview reported four additions, apply created the folder and script, and the deployed job returned `{"status":"ok","service":"campaign-core","version":"0.1.0"}` through a real worker.
- The immediate repeat preview reported `0 changes to apply`, proving idempotency against the final source bytes.
- Both disposable Compose projects, their containers, networks, and volumes were removed. The temporary external CLI profile files were emptied after their backing disposable instances and tokens ceased to exist.
- `git diff --check` passed. No live or historical Starfall data was accessed.

## Follow-ups

- TKT-0008 is unblocked and should add the full-code React shell without widening synchronization scope beyond the exact app and job resources it introduces.
- Exercise the source-check profile on native TrueNAS storage during the actual host deployment; Docker Desktop cannot validate the live UNC bind.
