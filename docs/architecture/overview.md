# Architecture Overview

## Tentative Version 1 decision

Windmill Community Edition is application infrastructure, not the domain core.

```text
Windmill full-code React app
          |
          +---- Campaign Core API ---- Campaign PostgreSQL
          |
          +---- Job adapter ---- Windmill server ---- Windmill PostgreSQL
                                      |
                                      +---- workers
                                      +---- schedules and webhooks
```

## Responsibilities

### Campaign Core

- Domain types and invariants.
- Entity and alias resolution.
- Truth-state and authority evaluation.
- Proposal versions and approval scope.
- Retcon and contradiction classification.
- Transactional, idempotent canonical mutations.
- Durable receipts and audit history.
- Retrieval policy and visibility enforcement.

Only Campaign Core receives credentials capable of mutating canonical tables.

### Windmill

- Long-running and asynchronous jobs.
- Scheduling, retries, progress, and operational visibility.
- Import orchestration.
- Transcription and synthesis jobs.
- Index and Cognee rebuilds.
- Deliverable generation.
- Telegram and provider webhooks.

Flows are optional. Use them when orchestration adds value; do not turn simple domain operations into visual pipelines.

### React app

- Thinking workspace and evidence side panel.
- Proposal comparison and approval.
- Session preparation and encounter runner.
- Audio upload and job progress.
- Campaign browsing and grounded questions.

The UI uses separate `CampaignClient` and `JobPlatform` interfaces so Windmill can be replaced without rewriting campaign interactions.

### PostgreSQL

Use separate Windmill and campaign databases and credentials. They may initially share one PostgreSQL service if backups and permissions remain distinct.

## Deployment

TrueNAS hosts the private Docker Compose stack. Authentication is deferred during private development. Remote access will later use the existing reverse proxy with an Authentik Proxy Provider in forward-auth mode.

## Portability

The local Git repository is authoritative. Windmill resources are exported and deployed with the CLI. Rebuilding the Windmill container alone does not redeploy workspace resources stored in Windmill's database.
