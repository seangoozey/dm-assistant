# DM Assistant

A private, self-hosted campaign knowledge and continuity system for a single Dungeon Master.

The application captures unstructured notes, retrieves supporting campaign information, distinguishes canon from planning, and applies approved changes through deterministic rules. Language models interpret and generate bounded outputs; they do not decide whether required workflow steps occur.

## Current status

The specification foundation, Campaign Core transaction boundary, typed acceptance harnesses, incremental Markdown connector, deterministic grounded-retrieval boundary, reproducible Windmill workspace deployment, and first full-code React shell are in place. The service preserves source evidence, reconciles repeated scans, records review candidates and immutable receipts, keeps canonical promotion behind exact versioned approval, and enforces citation, visibility, conflict, and non-canon policies on retrieval.

The verified Starfall scope has been ingested into the local development database as immutable, non-canonical evidence with an idempotent receipt and zero canonical mutations. Its review queues and exact, human-controlled candidate proposal, disposition, versioning, and approval commands are implemented. The React review slice is deployed and browser-verified with import totals, quarantine, exact evidence, explicit target resolution, immutable proposal scope, approval, application, and receipts. The next objective is the first deliberately scoped live canonical promotion.

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

- Current repository checkout: `E:\dm-assistant`
- Previously audited Starfall snapshot: `E:\studio\starfall`
- Current live Starfall collection: `\\HOMESERVER\projects\projects\starfall`
- Historical OpenClaw workspace: `\\HOMESERVER\openclaw\.openclaw\dnd-workspace`

The live Starfall collection remains active and changes independently. It is the legacy source for live-data confirmation and eventual cutover, but it must remain strictly read-only. The audited snapshot and any Starfall copy inside the historical OpenClaw workspace are reference fixtures, not current production truth. The OpenClaw workspace may be consulted for historical workflows, scripts, and failure evidence; it does not establish campaign canon.

Do not hard-code these paths into domain logic. Use configuration.

## Repository map

```text
campaign-core/       Python domain, PostgreSQL adapter, migrations, and FastAPI service
windmill/            Scoped workspace source, controlled CLI deployment, and React app
integrations/        Telegram, Cognee, transcription, Foundry (future)
docs/                Product, architecture, migration, and test specifications
tickets/             File-based development tickets
tests/fixtures/      Sanitized interaction and retrieval acceptance fixtures
deploy/              Private Compose scaffold and TrueNAS dataset override
```

## Development rule

No implementation is complete merely because an LLM produced plausible output. Domain behavior must be enforced by code and covered by acceptance tests derived from real campaign interactions.

## Local UI test cycle

After completing the one-time environment and Windmill workspace setup in [the deployment guide](deploy/README.md#complete-local-ui-test-lifecycle), run:

```powershell
.\deploy\test-stack.ps1 up
.\deploy\test-stack.ps1 status
.\deploy\test-stack.ps1 down
```

Routine shutdown preserves both database volumes.
