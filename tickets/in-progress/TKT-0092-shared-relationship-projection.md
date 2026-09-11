---
id: TKT-0092
title: Build shared relationship and provenance projection
status: in-progress
priority: P0
milestone: shared-campaign-knowledge
depends_on: [TKT-0090, TKT-0091]
created: 2026-09-06
---

# Outcome

## Expanded generation activated (2026-09-08)

Completed and deployed live-pilot-v3: 50 current claims, 375 nodes, 1,069 edges.
All 50 documents have exact stored source chunks; offline nonlexical discovery audit
passes. Rebound all 50 against current Core assertions/provenance before activation.
Testing Compose now mounts v3 read-only; v2 retained for rollback. Four oversized
relevant claims remain excluded, not truncated; this is not full-campaign indexing.

Recorded user-confirmed cumulative <=$0.50 bound through stopped attempt 1,186,
retaining all attempt history. Gateway queues temporary reservation shortages until
active calls settle; max two upstream requests. Added byte-aware embedding batches
without truncation, fixing the native viewer's oversized embedding request. Final
search-only check succeeds without re-extraction; all 375 viewer embeddings resolved.
Ledger: 1,335 attempts, $0.036196 new provider cost, zero uncertain reservations,
conservative cumulative <=$0.536196. Existing $2 local guard remains unchanged.

20 focused tests pass. Live DM query returns 49 traced results; party query returns
zero. Native viewer is available at http://127.0.0.1:8767/graph.html and browser
shows 375 nodes / 1,069 edges. Automatic refresh, full-campaign coverage and semantic
quality/precision remain separate unfinished work; no canonical data was changed.

## Expanded generation attempt (2026-09-08)

Created separate live-pilot-v3 snapshot: 50 relevant current claims / 46,431
assertion characters. Four oversized claims remain outside the existing 7,000
character input bound; no truncation. Versioned index input includes original
state/authority and modality instructions, without editing canonical assertions.
Added offline chunk-coverage/nonlexical-discovery audit. Core supports up to 64
records / 8 MB, but testing Compose still points to v2; v3 is NOT active.

Initial concurrent extraction exhausted temporary budget reservations. Added a
two-request upstream semaphore with a real local-server/mocked-provider test.
Retry progressed but again encountered reservation limits; stopped both runs and
retained partial derivatives, original snapshots, and all uncertain reservations.
No ledger reset/refund. Final ledger: 1,186 attempts, provider-reported $0.347851
after earlier <=$0.06 checkpoint, unresolved $1.40, conservative $1.807851 under
the $2 guard. This is not evidence that the provider's ~$3 key limit was reached.
V3 expansion remains incomplete; do not bind/deploy until coverage audit passes.
11 evaluation tests and six Core graph tests pass. Current v2 deployment unchanged.

## Source-context-safe connections (2026-09-08)

Generated relation verbs are no longer displayed as event claims. Traversal uses
neutral associated names and requires common exact-chunk source context for each
edge. This is co-occurrence context, NOT entailment validation. Typed graph_sources
return unchanged current assertions, citations and states for the selected path.
Related cards expose these through Read connection context. Whole-generation
fingerprint/visibility checks still protect all intermediate sources.

Six backend tests pass, including a misleading destroys label over intended prose;
strict React typecheck and all 52 App tests pass. Deployed successfully. Live Ishi
query still finds Mythis Regions with three connection sources retaining planning
language. No canonical edits or provider calls.
Final lint passes after removing an unused edge-label variable; the test fixture
uses the typed intended state and no longer emits serializer warnings.

Read-only next-batch inventory finds 54 relevant current claims: 2 observed,
24 established, 1 intended, 27 prepared (112,604 total characters). Only 12 are
currently indexed; expanding this coverage remains pending. The pilot's extraction
input currently lacks structured truth dimensions and needs a new generation
format before a larger extraction. Do not silently relabel source truth states.

## Useful discovery cards (2026-09-08)

Replaced the debug trace dump with separate Related discoveries and Direct matches
groups. Each result occurs once, remains expandable/pinnable, and related cards
carry a compact suggested connection rather than UUIDs/repeated warnings. Graph
traversal now follows incoming and outgoing semantic edges for up to two hops,
preserving original edge direction; 40-node and broad-intermediate-hub limits
bound expansion. Existing whole-generation freshness and visibility checks remain.

Five backend tests pass, including a reverse/two-hop result without the seed name
and exclusion beyond the two-hop limit;
three focused React tests and strict typecheck pass. Live Core query for Ishi'go'dan
retrieves the Mythis Regions assertion identifying Mythis Minor and Tsunadis, which
contains no Ishi'go'dan text. This proves added nonlexical retrieval, not correctness
of Cognee's edge labels: the stored `destroys` edge compresses a planned action.
Cards explicitly identify connections as suggestions; source assertion stays intact.
No new provider calls. This remains the 12-record pilot, not full-campaign discovery.
Deployment completed successfully. Visual QA remains pending: the in-app Windmill
iframe stayed about:blank after two post-build refreshes. React tests verify card
grouping/expansion/pinning; live API verifies the nonlexical result above. Ruff passes.
Follow-up validation: all 52 App tests pass. Both the existing and a fresh in-app
tab still rendered a blank embedded app; the temporary verification tab was closed.
Windmill supplied a blob iframe URL but it did not render. Visual QA remains open.

## Brainstorm graph trace visibility repaired (2026-09-08)

The top-ten lexical re-ranking discarded graph matches, hiding the conditional
explanation. Preserve graph context through ranking, including results without
query words. Added a UI regression with ten competing lexical matches. Three
focused search/pin tests and strict TypeScript checks pass. The deployed in-app
browser now shows and expands 'Why these graph results appeared' for Ishi'go'dan,
including stored entity/contains paths and source citations. No canon changes or
provider calls were needed.

## Deployed bounded pilot (2026-09-07)

Added development-only GraphPilotRetrieval, opt-in via graph_pilot_bundle. Testing
Compose mounts the v2 bundle read-only. Reads use exact entity-name seeds, at most
one stored entity edge and an exact contains/source-text association. Full current
Core fingerprints for all 12 pilot records are checked before any graph result;
any drift disables the entire pilot generation. Source claims, not edge labels,
are returned. Graph-only additions have context role; existing fallback policy
results/modes remain unchanged (including its unfinished legacy heuristics).

Brainstorm content search now exposes a collapsed 'Why these graph results appeared'
trace. No provider request occurs at query time. Missing/invalid bundle falls back
to existing retrieval; party requests never load the DM graph. This is a bounded
pilot adapter, not the completed durable projection/registry integration.

53 focused pilot/retrieval/privacy tests passed; Ruff, mypy and React strict typecheck
passed. Authorized test-stack down/up completed, including fresh Windmill bundle.
Live DM query returned 12 traced results; party query verification recorded separately
in the task. Bundle binding corrected JSON timestamp normalization to match psycopg
record fingerprints. Migrations through 0041 deployed with this stack rebuild.

Still required: automatic refresh/rebuild after changes, actual correction lifecycle
integration test, scope-wide production projection, graph discovery quality handling,
UI visual QA and replacement of legacy comparison heuristics. Canonical data was not
edited for this pilot; stale-correction behavior is currently a regression test.

## Verifiable live slice (2026-09-07)

Live pilot v2 completed: 12 claims / 6,989 characters, 100 stored nodes and 246
edges. Native viewer served locally at http://127.0.0.1:8766/graph.html. Raw graph,
source snapshot and query passage traces remain in ignored private runtime storage.
Both graph context queries completed. Inspection found a useful `tsunadis located_on
mythis minor` edge but also an incorrect `tsunadis enables_summoning_of ragganaken`
edge: the source says Tsunadis opposes the cultists; destroying its castle removes
that opposition. Therefore semantic edges are NOT approved as factual evidence.
This is precisely why stored graph inspection is an acceptance requirement.
Brainstorm integration and correction propagation remain incomplete.

Final combined ledger after both pilots: 804 attempts, provider-reported costs
after the first-27 checkpoint $0.130198, earlier upper bound $0.06, unresolved
reservations $0.40, conservative accounted exposure $0.590198. No limit hit.
v1 reported success despite embedding errors; success flags alone are insufficient.

User requested a visible proof that the graph actually connects records, ideally
Cognee's own viewer. Native offline inspection now exported the existing synthetic
store: 111 nodes and 162 edges, with JSON and SHA256 alongside HTML. User authorized
a small real campaign subset through OpenRouter under the key's approximate $3 cap;
the existing stricter $2 ledger guard is retained. Twelve current claims with complete
provenance were exported read-only for an isolated DM-only pilot.

End-to-end acceptance must include actual stored edge/path IDs, source passage
bindings, native graph inspection, Brainstorm display, and a correction/revalidation
test. Viewer existence alone does not prove useful retrieval or factual correctness.
Pilot v1 exposed oversized embedding batches and an incomplete topic selection;
v2 splits batches and prioritizes the relevant destination/summoning passages.
Neither run mutates canonical claims. Live application wiring remains unfinished.

## Artifact read-back gate (2026-09-07)

Added a trusted adapter contract for independent enumeration of a complete sealed
generation. Registry verification recomputes its manifest, checks scope/generation,
hash and node/edge counts, then records verification only against the immutable
validated build. Publication and active reads now require artifact verification.
Migration 0041 leaves earlier manifests unverified until read-back succeeds.

57 artifact/build/registry/service/migration tests passed. Tests use mocked readers;
no Cognee read-back adapter or real external artifact verification is claimed yet.
The adapter must enumerate stored contents rather than echo upload buffers, reject
partial reads, and enforce generation immutability. Semantic/generated associations
must stay separate from the authoritative projection manifest. No migrations applied,
live deployment, canonical writes or provider calls.

## Snapshot validation gate (2026-09-07)

Added manifest validation for Core-owned records and evidence associations. Rejects
duplicate IDs, invisible/unaccepted/retired records, missing evidence bindings,
dangling endpoints and stale edge evidence. Deterministic manifest hashes bind
visibility, node fingerprints and links. Migration 0040 stores immutable generation
manifests; retries cannot replace a different/revoked manifest. Publication locks
and requires a validated same-scope manifest in its transaction. Active reads also
require validated status, so revoked builds cannot serve retrieval.

51 build/registry/service/migration tests passed; Ruff and mypy passed. Neither
migration is deployed. This validates the supplied Core snapshot only: source-wide
completeness, external index artifact loading/verification, refresh and build producer
are still pending. No claim of end-to-end build readiness, deployment or paid calls.

## Execution increment (2026-09-07)

Started registry lifecycle work alongside unfinished TKT-0091 and benchmark work;
this does not waive their live-integration gates. Migration 0039 adds disposable
scope/active-generation/version metadata. Core's registry separates requester scopes,
publishes/disables via compare-and-swap, and includes monotonic version in the active
generation token to reject ABA reuse during retrieval. No public activation route.
Build readiness, manifests, outbox refresh and persistent activation audit remain
unfinished. A trusted build validator must precede publication. Migration not deployed.

Validation: 44 registry/service/migration tests passed; Ruff and mypy clean.
PostgreSQL temporary-table smoke check validated the DDL and version compare-and-swap:
version 1 updated to 2 once; a stale version-1 update affected zero rows. Transaction
rolled back. This is not a multi-connection concurrency test or persistent deployment.
Rollback leaves canonical data untouched; disable the derived pointer to withdraw it.

Implement typed nodes and connections projected from existing entities, relationships, claim-related entities, source spans, plans and workflow references.

## Required reading

- [Shared Campaign Knowledge](../../docs/architecture/shared-campaign-knowledge.md)
- [ADR-0014](../../docs/decisions/ADR-0014-shared-campaign-knowledge.md)
- [ADR-0012](../../docs/decisions/ADR-0012-provenance-first-claims.md)

## Scope

Expose both relationship endpoints and direction. Separate semantic edges from mentions/support links. Include time, visibility, supersession, exact origins and complete provenance. Add durable refresh watermark/outbox handling and idempotent rebuild with atomic generation switch.

## Acceptance and validation

PostgreSQL tests prove joins and provenance, refresh after correction/merge/alias/visibility changes, hidden intermediate exclusion, no superseded resurrection, repeated rebuild equivalence and fallback during index outage.

## Migration and rollback

Additive schema; projection is disposable. Backfill from authoritative rows, verify before switching, rollback to previous generation or direct reads.
