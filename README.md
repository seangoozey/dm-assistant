# DM Assistant

A private, self-hosted campaign knowledge and continuity system for a single Dungeon Master.

The application captures unstructured notes, retrieves supporting campaign information, distinguishes canon from planning, and applies approved changes through deterministic rules. Language models interpret and generate bounded outputs; they do not decide whether required workflow steps occur.

## Current status

The specification, Campaign Core transaction boundary, incremental Markdown connector, grounded-retrieval boundary, reproducible Windmill workspace deployment, and full-code React shell are in place and browser-verified. Live Starfall evidence is ingested as immutable, non-canonical provenance with idempotent receipts and zero canonical side effects.

Every path to canon now runs through the Promotion Pipeline (ADR-0018): mandatory statement review and one receipted Approve action across the Description, Lore, and Brainstorm surfaces, plus a standing unpromoted-material repair audit — no unreviewed write path exists. Claim-backed attribute minting, `::` description claim breakpoints with never-lose-work autosave (ADR-0019), one renderer and one editor per Entity Kind, and an AI promotion assistant (restatement matching, duplicate checking) are delivered. The Qualified Entity standard governs the library through a live audit — 71 of 120 entities qualified, zero vocabulary failures. The active front is the orphaned-claims review: 186 ownerless claims that no surface currently surfaces (TKT-0138). See [docs/plan.md](docs/plan.md) for current execution state.

## Start here

1. Read [AGENTS.md](AGENTS.md).
2. Use the [documentation index](docs/README.md) to understand which documents are authoritative.
3. Read [docs/product/vision.md](docs/product/vision.md).
4. Read [docs/architecture/overview.md](docs/architecture/overview.md).
5. Read [docs/plan.md](docs/plan.md).
6. Select work from [tickets/index.md](tickets/index.md).

## Confirmed stack

- Windmill Community Edition for job infrastructure, workers, schedules, retries, progress, webhooks, and optional flows.
- Windmill full-code React app for the interface.
- Python and FastAPI for the dedicated Campaign Core.
- PostgreSQL for canonical campaign data.
- A separate PostgreSQL database for Windmill state and its job queue.
- Docker Compose on TrueNAS (the production end-state once the system is seeded and built to occasional-upgrade maturity).
- Local Git as the authoritative source; Windmill deployment through the CLI.
- The **graph service is foundational to project completion** (ruled 2026-09-28); its infrastructure is **unconfirmed** — **Cognee is the leading candidate** given evaluation results to date (native Cognee 4/6 vs the deployed stack 2/6 on the shared corpus). The decision is tracked behind TKT-0105; Cognee's evaluation stores are disposable and never the canonical index.
- OpenRouter as the v1 AI provider, with a DM-visible controlled model profile selector and `deepseek/deepseek-chat` as the recommended extraction profile. See ADR-0008.

Windmill, Campaign Core, and PostgreSQL are confirmed as the stack (ADR-0001/0002/0003, accepted 2026-09-28). ADR-0004 (local Git/CLI deployment) remains open pending the production deployment story.

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
