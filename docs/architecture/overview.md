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

The Markdown connector runs without a campaign database credential. It scans an explicitly acknowledged read-only root, then submits the typed batch to Campaign Core's `/imports/markdown/scan` operation. Windmill may later schedule that CLI, but it never receives a canonical-table credential.

Human import review reads enter through Campaign Core's typed `/imports/runs`, `/imports/candidates`, and `/imports/reviews` resources. Receipt and review queues are DM-only; candidate assertions and exact source excerpts are visibility-filtered before leaving Core. The read adapter uses deterministic pagination and never changes candidate disposition, review status, or canonical state.

Human candidate decisions enter through DM-only typed proposal and disposition commands. Every proposal item names an exact candidate, evidence revision, immutable target, and explicit entity or claim decision. Campaign Core performs deterministic identity, authority, time, PC-agency, and conflict checks; it does not infer matches or synthesize prose. Versions and evidence bindings are immutable, approvals name exact item IDs, and canonical application remains exclusively behind `apply_change_set`. Reject and defer update only auditable candidate review state.

Grounded reads enter through Campaign Core's typed `/retrieval/query` operation. Visibility is enforced before policy evaluation, accepted canonical evidence is the only source of supporting facts, and non-canonical candidates can appear only as labeled context. The initial lexical policy returns structured evidence, citations, answer modes, and reason codes; a later language-model presentation layer must not weaken those decisions.

### React app

- Thinking workspace and evidence side panel.
- Proposal comparison and approval.
- Session preparation and encounter runner.
- Audio upload and job progress.
- Campaign browsing and grounded questions.

The UI uses separate `CampaignClient` and `JobPlatform` interfaces so Windmill can be replaced without rewriting campaign interactions.

The shell sends grounded questions and human review commands only through `CampaignClient`, renders Campaign Core responses without synthesizing new facts, and starts asynchronous operational work only through `JobPlatform`. Its review workspace loads all source-review pages so quarantine is not hidden by pagination, selects one candidate at a time, shows exact evidence before action, and requires explicit target structure. It displays one immutable proposal version and one exact confirmation scope. Proposal, approval, failure, stale-version, and receipt state use versioned browser session storage; restored proposals are revalidated through Campaign Core before approval or application is enabled.

In the Windmill host, `WindmillCampaignClient` calls typed backend runnables, which reach Campaign Core through the worker's absolute internal `CAMPAIGN_CORE_URL`; the sandboxed browser never calls Campaign Core directly. `HttpCampaignClient` remains the replaceable implementation for a future independently hosted frontend. Pending job identifiers also live in versioned browser session storage so a refresh resumes polling rather than silently losing the operation.

### PostgreSQL

Use separate Windmill and campaign databases and credentials. They may initially share one PostgreSQL service if backups and permissions remain distinct.

## Deployment

TrueNAS hosts the private Docker Compose stack. Authentication is deferred during private development. Remote access will later use the existing reverse proxy with an Authentik Proxy Provider in forward-auth mode.

## Portability

The local Git repository is authoritative. Windmill resources are exported and deployed with the CLI. Rebuilding the Windmill container alone does not redeploy workspace resources stored in Windmill's database.
