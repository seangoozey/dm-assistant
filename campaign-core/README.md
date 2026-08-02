# Campaign Core

Campaign Core is the only application service allowed to mutate canonical campaign data. The pure `domain` package owns deterministic rules, `api` exposes transport contracts, and `adapters` contains PostgreSQL access. Domain code does not import either adapter package.

## Local development

Use Python 3.12 or 3.13. Production currently runs 3.13. From this directory:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install --requirement requirements-dev.txt
.\.venv\Scripts\python -m ruff check .
.\.venv\Scripts\python -m mypy
.\.venv\Scripts\python -m pytest
```

With the environment active, the repository-wide deterministic validation entry point is:

```powershell
python ..\tests\validate_repository.py
```

To run the API without a local PostgreSQL instance, provide a syntactically valid development URL and disable startup migrations:

```powershell
$env:CAMPAIGN_DATABASE_URL='postgresql://campaign:development-only@localhost:5432/campaign'
$env:CAMPAIGN_RUN_MIGRATIONS='false'
.\.venv\Scripts\python -m dm_assistant_core.bootstrap
```

The health endpoint is `http://127.0.0.1:8000/health`. When migrations are enabled, startup fails closed if PostgreSQL is unavailable or an applied migration's checksum has changed.

Campaign Core exposes one canonical mutation operation:

```text
POST /change-sets/{change_set_id}/apply
```

Its typed body names the exact `reviewed_version`, `approval_id`, and SHA-256 `content_hash`. A successful response is the durable receipt; an exact retry returns that same receipt with `idempotent_replay: true`. A stale version, mismatched hash, revoked or cross-version approval, invalid scope, or unsupported mutation receives `409 Conflict` without a partial canonical write.

Grounded retrieval is available through:

```text
POST /retrieval/query
```

The typed request carries a question and requester visibility. The response is intentionally structured: an answer mode, evidence roles, exact citations, and policy reason codes. Visibility filtering occurs before evaluation; accepted canonical records may support an answer, while candidates and other non-canonical records can appear only as context. The initial policy is deterministic and lexical, providing a safe boundary for a later presentation layer rather than generating prose itself.

The 38-case acceptance corpus runs as part of the ordinary `pytest` and repository validation commands. See `docs/testing/retrieval-harness.md` for its isolation and assertion rules.

## Migrations

Forward-only SQL migrations live under `src/dm_assistant_core/adapters/postgres/migrations`. Startup acquires a PostgreSQL advisory transaction lock, creates `campaign_schema_migrations` if needed, verifies hashes of applied files, and transactionally applies pending files.

Never edit an applied migration. Add a new migration. Compatible rollback means running the previous application against an expand-compatible schema. After a destructive contract migration, restore the last tested logical backup into a new database and validate it before cutover, as specified in `docs/architecture/campaign-core-schema.md`.

Migration `0001` creates the specified storage model, immutable evidence guards, and PC-agency trigger. Migration `0002` adds the approval binding and `apply_change_set` database function. The function locks the change set, proposal, immutable version and items, approval, and mutation target identities; it then creates every authorized entity or evidence-backed claim, its change-set item records, the receipt, and final statuses in one transaction.

Migration `0002` is expand-compatible with the prior application: its new column is nullable and the old health-only service can run against the expanded schema. Application rollback therefore deploys the prior image without reversing the migration. Schema reversal is intentionally not automated; if operational recovery requires removing an applied migration, restore the last tested logical backup into a new database and validate before cutover.

PostgreSQL integration tests are opt-in so the ordinary test command does not require a local service. Point them only at a disposable database whose name ends in `_test`:

```powershell
$env:CAMPAIGN_TEST_DATABASE_URL='postgresql://campaign_test:secret@127.0.0.1:55432/campaign_test'
.\.venv\Scripts\python -m pytest tests\test_change_sets_postgres.py -vv
```

Those tests apply the real migrations and cover HTTP-to-PostgreSQL scoped application, evidence-backed direct lore, candidate proposals and dispositions, stale-version rejection, injected failure after a prior item, and concurrent idempotent retries.

## Markdown imports

The connector requires an explicitly acknowledged read-only root. A dry run reads admitted bytes once and prints aggregate classifications without submitting content:

```powershell
.\.venv\Scripts\python -m dm_assistant_core.importer.cli `
  --root '\\server\share\starfall' `
  --root-identifier starfall-live `
  --read-only `
  --dry-run
```

Remove `--dry-run` and add `--core-url http://campaign-core:8000` to submit the typed batch to `POST /imports/markdown/scan`. The connector has no database dependency or credential. Campaign Core verifies hashes and policy-scoped paths, then records source revisions, path history, non-canonical candidates, reviews, observations, and one immutable receipt transactionally. An exact retry returns the prior receipt.

Migration `0003` adds path history, candidate/evidence records, import-opened reviews, revision metadata, and immutable import receipts. It is additive and compatible with the previous application. Application rollback uses the prior image; reversing persisted import evidence requires restore into a new database rather than deleting source history.

Imported evidence is inspectable through read-only Campaign Core operations:

```text
GET /imports/runs
GET /imports/runs/{run_id}
GET /imports/candidates
GET /imports/candidates/{candidate_id}
GET /imports/reviews
```

Every request includes `requester_role`; character requests also include `character_id`. Full receipts and review items are DM-only. Candidate lists enforce visibility before returning assertions or exact evidence excerpts. Lists use deterministic `limit`/`offset` pagination and support run, source status, review status, classification, state, authority, visibility, and source filters as applicable. Candidate detail returns only its cited spans with immutable revision hash and offsets, never a bulk raw-source export. These operations do not update candidate or review state.

DM-only candidate decisions use these typed operations:

```text
POST /imports/proposals
GET  /imports/proposals/{proposal_id}
POST /imports/proposals/{proposal_id}/versions
POST /imports/proposals/{proposal_id}/approvals
POST /imports/candidates/{candidate_id}/disposition
```

Proposal requests name every candidate, evidence revision, canonical target UUID, and entity or claim decision. Campaign Core copies the exact candidate assertion into claim payloads, creates an immutable source span, hashes the complete version, and accepts approval only for explicitly named item IDs from that version. Revising creates a new version and revokes unapplied older approvals. Reject and defer are auditable non-canonical dispositions. Applying an approval still uses only `POST /change-sets/{change_set_id}/apply`; candidate status changes occur in that same database transaction.

Migration `0004` adds candidate review status, immutable candidate-to-proposal evidence bindings, disposition history, and transaction-bound applied-status reconciliation. It is additive: the prior application ignores these structures, while new candidate commands require the new migration.

## Credential boundary

`CAMPAIGN_DATABASE_URL` is required and is loaded through typed settings. In Compose it is supplied only to `campaign-core`; Windmill receives only its own database URL. PostgreSQL access appears only in the adapter package. Workers call typed Campaign Core operations and must never receive this credential. The import endpoint persists evidence and review candidates but cannot mutate canonical entities, claims, or relationships.
