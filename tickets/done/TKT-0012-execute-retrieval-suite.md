---
id: TKT-0012
title: Execute grounded retrieval acceptance suite
status: done
priority: P1
milestone: trustworthy-librarian
depends_on: [TKT-0005, TKT-0010, TKT-0011]
created: 2026-08-01
updated: 2026-08-01
---

# TKT-0012: Execute Grounded Retrieval Acceptance Suite

## Outcome

Run the accepted retrieval corpus through the typed fixture harness and Campaign Core retrieval boundary as a deterministic project test.

## Context

TKT-0011 defines expected retrieval behavior without depending on unfinished application code. This ticket integrates that corpus after TKT-0005 and TKT-0010 establish the service and harness.

## Scope

- Parse the TKT-0011 corpus through the typed fixture schema.
- Load each case's sanitized records into an isolated test store.
- Execute the initial Campaign Core retrieval boundary.
- Assert answer mode, required facts and citations, forbidden claims, visibility, conflict handling, and deterministic ordering.
- Add the suite to the documented standard test command.

## Out of scope

- Model-provider benchmarking.
- Embedding or Cognee optimization.
- Importing live campaign data into a production database.

## Acceptance criteria

- [x] Every accepted TKT-0011 case executes through the typed harness.
- [x] Required facts and citations are asserted without brittle prose matching.
- [x] Forbidden claims, visibility leaks, and non-canon leakage fail deterministically.
- [x] Unknown, conflict, and possible-retcon answer modes are enforced.
- [x] Repeated runs are order-independent and leave no persistent test data.
- [x] The documented standard test command runs the entire retrieval suite.

## Validation

Record the standard test command, case and assertion counts, representative intentional failures, and `git diff --check` output.

## Implementation notes

Keep deterministic retrieval-policy assertions separate from later model-quality evaluations.

Implemented a transport-independent retrieval policy, typed query/result contracts, an isolated in-memory acceptance repository, a read-only PostgreSQL repository, and `POST /retrieval/query`. The policy filters visibility before evaluation, permits accepted canonical records to support answers, labels non-canonical candidates as context only, classifies conflicts and possible retcons, and returns deterministic evidence, citations, and reason codes rather than generated prose.

The strict Pydantic corpus schema rejects extra or malformed data. All 38 cases run through a fresh repository and the same application service used by the API; each case is repeated with reversed record input to prove order independence. Required facts use normalized token evidence across structured assertions and citations instead of exact answer prose.

One corpus inconsistency was corrected during implementation: `chronology-expected-and-observed-differ` now uses the DM requester because its required comparison cites a DM-only preparation source. Preserving the prior party requester would have made the acceptance result require a visibility leak.

No live Starfall collection or historical snapshot was accessed. The implementation and tests use only the sanitized checked-in corpus.

## Validation evidence

- Focused gate: Ruff passed, strict mypy passed over 37 source files, and `test_retrieval_acceptance.py` passed 47 tests. That includes all 38 corpus cases plus corpus cardinality, visibility isolation, non-canonical role, reverse-order, API, and malformed-schema checks.
- Representative intentional failures reject a missing question, duplicate record identifier, unknown category, and empty required-fact collection. Policy assertions also fail on hidden record/citation exposure, a non-canonical support role, a forbidden claim, or changed result ordering.
- `python tests\validate_repository.py` passed: Ruff, strict mypy, 99 tests passed, 12 external-prerequisite tests skipped, Compose policy passed, and all 38 corpus cases passed separate structural validation.
- With `CAMPAIGN_TEST_DATABASE_URL` pointed at a disposable PostgreSQL 16.14 database, the full Campaign Core suite passed 110 tests with one platform-gated symlink test skipped. A production `PostgresRetrievalRepository` query also passed against the migrated database. The temporary container was removed afterward.
- Compose interpolation validation passed with validation-only environment values, and `dm-assistant-campaign-core:0.1.0` built successfully from the pinned `python:3.13.14-alpine3.23` base.
- `git diff --check` passed.
- No migration was required. Rollback is an application-image rollback; the retrieval operation is read-only and creates no persistent retrieval state.

## Follow-ups

- Treat language-model presentation and retrieval-quality benchmarking as separate work; neither may override the deterministic visibility, authority, answer-mode, or citation result.
- TKT-0007 is the next ready vertical-slice dependency.
