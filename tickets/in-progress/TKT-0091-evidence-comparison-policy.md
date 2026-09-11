---
id: TKT-0091
title: Correct evidence comparison and conflict classification
status: in-progress
priority: P0
milestone: shared-campaign-knowledge
depends_on: [TKT-0090]
created: 2026-09-06
---

# Outcome

## Internal path-service wiring (2026-09-07)

Connected the current-path repository protocol to path authorization and conservative
suggestion evaluation via `PathRetrievalService`. A Core-owned registry interface
selects the active scope/generation for the exact requester visibility; provider
metadata cannot select it. Disabled or mismatched scopes fail closed before reads.
The service rechecks the generation after loading the snapshot, limits both paths
and unique loaded IDs, and applies result facets after path authorization. Valid
paths yield context, not automatic answer sufficiency or transitive facts.

101 focused service/path/reader/privacy/acceptance tests passed; mypy passed.
The registry is a protocol, not a durable implementation. Authenticated request
resolution, persisted generation activation/refresh and public route integration
remain pending under the projection/shared-service tickets. The double read detects
generation changes during loading; it is not an atomic publication lease. No live
endpoint changes, canonical writes, deployment or paid model calls.

## Database path-snapshot increment (2026-09-07)

Added a bounded internal `current_paths` reader. Exact records and shared-span
associations are loaded on one connection in a read-only REPEATABLE READ transaction.
Links exist only when two requested claims/relationships cite the same exact source
span; these are evidence-navigation associations, never semantic or inferred edges.
Both endpoint snapshots bind each link's evidence. Hidden/ineligible endpoints
remove links before return. Target facets are deferred so they do not incorrectly
filter intermediate records. Invalid, empty and oversized requests do not connect.

93 focused tests passed; Ruff and mypy clean. Read-only PostgreSQL smoke validation
loaded five evidence-bound records and found 12 directed shared-span links among
100 sampled claim IDs, then rolled back. This proves SQL execution, not concurrent
mutation behavior. Tests verify transaction/connection usage with mocks.

This is the narrow current-state adapter for the existing path boundary, not the
full TKT-0092 projection. Authenticated scope/generation management, semantic and
entity traversal, production service wiring and answer support remain pending.
No deployment, canonical data changes or provider calls.

## Internal path authorization increment (2026-09-07)

Added `domain/retrieval_paths.py` as a narrow safety contract ahead of TKT-0092's
projection implementation. Index paths contain only scope/generation, fingerprinted
record references and edge IDs. Trusted current Core links bind ordered endpoints
and evidence snapshots. Every intermediate node and link-evidence record must be
current and visible; missing/hidden/stale paths return no rejection details.
Wrong scopes/generations, unknown seeds, cycles, reversed or missing edges fail
closed. Requests are limited to 100 paths and two hops. Returned targets still
require the existing suggestion evaluator; paths never prove transitive facts.

Validation: 89 focused path/service/boundary/privacy/acceptance tests passed; mypy
clean. Scope IDs, generation selection, edges and records must be Core-owned.
This does not implement authenticated scope selection, a projection builder,
entity-family traversal, or atomic database path loading. Those remain TKT-0092/
0094 work; no live endpoint integration, deployment, canonical writes or paid calls.

## Evidence-binding validation increment (2026-09-07)

Current-record snapshots now include an internal binding over every linked evidence
span: span/revision IDs, revision content hash, offsets and excerpt hash. The record
fingerprint includes this binding, so changing secondary evidence also invalidates
an old suggestion. This binds linked evidence, not an assertion that an imported
revision is the latest external file. It is not exposed as extra evidence text.

Validated the generated exact-ID SQL in a read-only transaction against local
PostgreSQL: five sampled records loaded, all five with evidence bindings; transaction
rolled back. Reusable check: `deploy/evaluation/validate_current_reader.py`.
64 focused service/boundary/privacy/legacy acceptance tests passed; changed-module
Ruff and mypy checks passed. No canonical writes, paid calls or deployment.
Projection emission, path authorization and answer-support policy remain pending;
the existing endpoint remains unchanged.

## Current-record service increment (2026-09-07)

Added internal DerivedRetrievalService with a CurrentRecordRepository protocol.
Every request reloads exact suggested IDs before fingerprint/eligibility evaluation;
no generated assertion or cached index record is accepted as current Core data.
PostgreSQL implements canonical claim/relationship lookup using a single parameterized
UUID-array statement snapshot, claim-supersession exclusion and visibility/state/
kind/tag filtering. Import candidates do not enter through this canonical reader.
Empty/oversized requests stop before database reads; invalid UUIDs stop before SQL.

63 focused service/boundary/privacy/legacy acceptance tests passed, including a
record changed between two calls. Ruff and mypy clean for changed application and
PostgreSQL modules. Reader tests mock the database; real PostgreSQL execution is
not yet validated. No API routing, live data mutation, provider call or deployment.
Existing endpoint unchanged. Index path authorization, exact source-revision projection
bindings and answer-support policy remain required before production integration.

## Derived-index boundary increment (2026-09-07)

Following the Cognee corpus run, added an internal Core-only `evaluate_suggestions`
boundary. Suggestions contain only stable record IDs and full retrieval-snapshot
fingerprints; caller-supplied current Core records provide all displayed text and
dimensions. Hidden, stale, removed, superseded, rejected and excluded-kind records
are silently omitted without leaking rejection counts or reasons. Kind/tag filters
are enforced. Planning and unaccepted claim records remain context, never support.

Compatible claims do not trigger the legacy count heuristic in this new boundary.
Only Core-validated comparison coordinates yield typed conflicts, and only compared
records get conflict roles. Retrieval similarity alone always remains insufficient
to authorize an answer or mutation. Fingerprints include source and truth dimensions.

Validation: 76 focused derived-boundary/comparison/retrieval tests passed; Ruff and
mypy clean for the new module. No provider calls, migrations, live writes or deployment.

This is not yet wired into the application or a PostgreSQL exact-ID reader. The
existing endpoint and its legacy heuristic remain unchanged pending fixture-compatible
migration. The caller must independently authorize suggestions; this function does
not establish hidden-path safety or a transactionally current projection. Next are
Core-backed snapshot reads, projection scope and explicit answer-support validation.
Ticket remains in progress; no claim of live conflict discovery or completed policy.

Replace claim-count/state-combination conflict heuristics with explicit comparison evidence. Related claims are not automatically contradictory.

## Required reading

- [Shared Campaign Knowledge](../../docs/architecture/shared-campaign-knowledge.md)
- [ADR-0014](../../docs/decisions/ADR-0014-shared-campaign-knowledge.md)
- [ADR-0012](../../docs/decisions/ADR-0012-provenance-first-claims.md)

## Scope

Separate retrieval relevance, suspected conflict, verified conflict and insufficient evidence. Compare same subject/property where explicit structure exists; for unstructured prose return a comparison candidate or unknown result, never invented certainty. Preserve actual conflict/retcon fixtures and PC agency rules.

## Acceptance and validation

Two compatible established claims and compatible observed/background claims do not trigger conflict; explicit supported contradiction still does; hidden claims cannot leak through modes/counts. Unknown comparison does not authorize Lore auto-application.

Factual conflicts must be exposed as typed evidence-linked issues suitable for a
future repair surface, not only an answer-mode string. Include stable snapshot IDs,
verification level, provenance references, scope and review requirement. TKT-0097
owns the later durable queue and repair UI.

## Migration and rollback

Version policy behavior; retain prior receipts and claims unchanged. Revert code without rewriting truth.

## Execution note

The TKT-0090 offline baseline is available. Begin the comparison contract while
0090 remains open for benchmark target agreement and service/path measurement.
This is a deliberate two-ticket overlap; no graph expansion begins yet.

## Progress — comparison contract

- Added a read-only, versioned explicit comparison module. Different values only
  establish conflict for the same subject/property/scope with an exclusive-property
  rule. An observed/background conflict requests possible-retcon review.
- Missing structure, different times/properties, planning and superseded records
  remain unknown. Matching values establish only coordinate equality, not equivalence
  of complete assertions. Results do not authorize mutations.
- Hidden input records produce the same opaque unknown result as missing comparison
  inputs; no hidden IDs or conclusions are exposed.
- Retrieval still uses the legacy policy. Next: supply validated comparison inputs,
  expose unknown versus reviewed comparisons, and replace the old heuristic without
  losing the original conflict/retcon fixtures. Do not add ad hoc prose patterns to
  make those fixtures pass.
- No database schema or live-data changes; no deployment for this isolated contract.
- Validation: Ruff clean; mypy clean for the comparison module; 62 tests passed
  across comparison, connected benchmark and the existing retrieval acceptance suite.

## Progress — repair-ready exposure

- RetrievalResult now exposes structured issues, exact assertion snapshots, provenance
  references, stable content-sensitive IDs, verification, scope and review flags.
- Trusted internal coordinates feed verified comparisons into retrieval modes. The
  query API rejects client-supplied coordinates. PostgreSQL coordinate production is
  not implemented yet; no automatic live factual-conflict discovery is claimed.
- Existing legacy alerts are explicitly unverified; their mode heuristic remains
  pending replacement, and its false positives and mode privacy remain open.
- Added truncation metadata and partial-coverage declaration. Empty issue output does
  not mean the campaign is consistent. Added TKT-0097 for persistent review and repair.
- Validation: 68 comparison/retrieval tests passed; original corpus retained unchanged.
- Not deployed during this increment. No campaign mutations or database migration.

## Progress — visibility and API boundary

- Removed the hidden-authoritative branch that leaked private record existence via
  `restricted` mode; hidden and absent records now give identical policy responses.
- PostgreSQL now filters visibility before its 100-record cap, preventing private
  results from displacing public evidence. Timing side channels are not assessed.
- Added API-level issue serialization/privacy tests and a 150-hidden-row limit test.
- Updated only the two obsolete visibility-mode expectations in the 38-case corpus;
  all original cases/assertions and actual conflict/retcon expectations remain.
  Historical connected baseline retained with explicit security-case deltas.
- Validation: 71 focused tests passed; Ruff clean. Legacy count-based false conflicts
  and trusted production comparison inputs remain unfinished; no deployment yet.
- Broader validation: Campaign Core suite 341 passed / 36 skipped; mypy clean for
  the changed policy and PostgreSQL adapter. Skipped integration tests were not proven.
