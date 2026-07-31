# DM Assistant

A private, self-hosted campaign knowledge and continuity system for a single Dungeon Master.

The application captures unstructured notes, retrieves supporting campaign information, distinguishes canon from planning, and applies approved changes through deterministic rules. Language models interpret and generate bounded outputs; they do not decide whether required workflow steps occur.

## Current status

Planning and specification. No application code is authoritative yet.

The immediate objective is to define the truth-state model and build acceptance fixtures from the existing Starfall campaign before implementing the Campaign Core.

## Start here

1. Read [AGENTS.md](AGENTS.md).
2. Use the [documentation index](docs/README.md) to understand which documents are authoritative.
3. Read [docs/product/vision.md](docs/product/vision.md).
4. Read [docs/architecture/overview.md](docs/architecture/overview.md).
5. Read [docs/plan.md](docs/plan.md).
6. Select work from [tickets/index.md](tickets/index.md).

## Tentative stack

- Windmill Community Edition for job infrastructure, workers, schedules, retries, progress, webhooks, and optional flows.
- Windmill full-code React app for the initial interface.
- Python and FastAPI for the dedicated Campaign Core.
- PostgreSQL for canonical campaign data.
- A separate PostgreSQL database for Windmill state and its job queue.
- Docker Compose on TrueNAS.
- Local Git as the authoritative source; Windmill deployment through the CLI.
- Cognee as an optional, disposable graph/retrieval index.

All platform choices remain revisable until a vertical slice proves them.

## Local paths

- Intended repository: `E:\studio\dm-assistant`
- Current legacy snapshot: `E:\studio\starfall`
- The legacy campaign remains active and changes independently. Treat any copied snapshot as a fixture, not production truth.

Do not hard-code these paths into domain logic. Use configuration.

## Repository map

```text
campaign-core/       Python domain and API code (future)
windmill/            Scripts, flows, workers, and full-code app (future)
integrations/        Telegram, Cognee, transcription, Foundry (future)
docs/                Product, architecture, migration, and test specifications
tickets/             File-based development tickets
tests/fixtures/      Sanitized acceptance fixtures (future)
deploy/              TrueNAS Compose and deployment scripts (future)
```

## Development rule

No implementation is complete merely because an LLM produced plausible output. Domain behavior must be enforced by code and covered by acceptance tests derived from real campaign interactions.
