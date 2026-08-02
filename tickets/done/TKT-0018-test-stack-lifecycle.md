---
id: TKT-0018
title: Automate the local UI test stack lifecycle
status: done
priority: P1
milestone: trustworthy-librarian
depends_on: [TKT-0008, TKT-0017]
created: 2026-08-01
updated: 2026-08-01
---

# TKT-0018: Automate the Local UI Test Stack Lifecycle

## Outcome

Provide one safe PowerShell entry point that starts, verifies, deploys, reports, and stops the complete local browser-test environment without erasing persistent Windmill or Campaign data.

## Acceptance criteria

- [x] `up` validates configuration, starts the Compose stack, waits for health, and deploys the selected Windmill workspace.
- [x] Campaign Core is published only on loopback for browser testing.
- [x] The script prints the exact stable Windmill app URL.
- [x] `status` reports containers and HTTP health without changing state.
- [x] `down` removes test containers and networks while preserving named database volumes.
- [x] Static validation checks script syntax and safety-critical Compose behavior.
- [x] Documentation includes first-run prerequisites and routine commands.

## Validation evidence

- A real `up -SkipWorkspaceDeploy` run built Campaign Core, started all five services, and reached healthy Windmill and Campaign Core endpoints on `127.0.0.1:8000` and `127.0.0.1:8001`.
- A real `status` run reported the five containers, both HTTP health results, and loopback-only published ports.
- A real `down` run removed the containers and three Compose networks; all four named volumes remained present.
- Static validation parses the PowerShell source and enforces the loopback-only override, volume-preserving shutdown, stable app URL, and workspace deployment path.
- The full repository gate passes: 101 Python tests, 9 React tests, 38 retrieval cases, Ruff, mypy, strict TypeScript, the raw-app build, and infrastructure policy checks.

## Migration and rollback

No database migration is required. The testing override affects only commands that explicitly include it through `test-stack.ps1`. Rollback is removal of the script, override, validator, and their documentation; existing named volumes are unaffected.

## Follow-up

The initial Windmill browser setup and creation of the remote workspace remain intentional one-time human steps. After the CLI profile exists, routine `up` performs the scoped application deployment automatically.
