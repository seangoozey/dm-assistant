---
id: TKT-0096
title: Evaluate Cognee and graph retrieval backends against shared contract
status: in-progress
priority: P1
milestone: shared-campaign-knowledge
depends_on: [TKT-0094]
created: 2026-09-06
---

# Outcome

Measure whether Cognee or a dedicated graph backend improves the shared campaign knowledge service over the PostgreSQL baseline.

The user confirmed that Cognee's intended purpose includes LLM-based discovery of
relationships in prose, not only traversal of links already recorded in Core.

## Required reading

- [Shared Campaign Knowledge](../../docs/architecture/shared-campaign-knowledge.md)
- [ADR-0014](../../docs/decisions/ADR-0014-shared-campaign-knowledge.md)
- [ADR-0012](../../docs/decisions/ADR-0012-provenance-first-claims.md)

## Scope

Verify current versions/capabilities at evaluation time. Use the same sanitized corpus and resource budget; compare direct/connected retrieval plus optional vector passages. Evaluate incremental correction, deletion/supersession, visibility, rebuild and restore, latency, quality and operational burden. Keep generated links derived.

Compare three explicit arms: current lexical retrieval, traversal using only known
links, and Cognee with LLM relationship discovery. Do not credit Cognee with discovery
when expected connections have already been supplied as graph edges. Keep gold
answers/required IDs/paths out of provider input. Test paraphrased relationships and
cross-entry questions, not only exact-name co-occurrence.

Use OpenRouter as the first provider route to verify; do not assume Cognee's installed
version supports the application's existing configuration unchanged. Pin Cognee,
provider/model, extraction configuration and embedding model independently. Embeddings
are not a substitute for relationship extraction. No local LLM is required by this plan.

Derived, evidence-grounded suggestions may automatically help retrieve source passages;
manual approval of every indexing edge is not required. Such edges cannot independently
support a canonical answer, verify a conflict or authorize a mutation. Preserve
negation, attribution, planning and temporal scope. Keep ambiguous identity unresolved.

Measure extraction grounding/error rate, relation/path recall, retrieval quality,
tokens and monetary cost, repeat-run variance, ingestion/query latency, retry/failure
behavior and correction invalidation. Preserve sanitized failure artifacts for analysis.
Test rebuild, provider outage and budget exhaustion without blocking normal capture.

## Acceptance and validation

Produce repeatable comparative results and a documented adopt/defer decision; no unsupported canonical relationships or hidden-path leakage permitted. External backend has no canonical write credentials; disable it without losing campaign function.

Report LLM-discovered improvements separately from known-link traversal. Demonstrate
that wrong model edges cannot survive source correction or masquerade as reviewed
canon. Begin with synthetic inputs; live campaign transfer and a paid evaluation
budget must be established before running that stage. This clarification does not
mean Cognee has been installed, selected, or benchmarked.

## Preparation available

User authorized a $2 total OpenRouter cap for synthetic evaluation only. Early isolated
compatibility trial begins before TKT-0094; adoption/comparative acceptance still waits
on that dependency. Cognee 1.5.3 wheel downloaded into ignored local trial storage;
installation uses a separate virtual environment, never Campaign Core's environment.
Budget must be enforced across embeddings, extraction, retries and repeat runs.

Added ignored trial environment and `deploy/evaluation/cognee_preflight.py` for a
network-blocked import/signature check. Cognee dependency installation is underway;
preflight lint passed but import has not yet been verified. No paid calls made.
See `deploy/evaluation/README.md` for wheel hash, isolation and outstanding budget guard.

Installation subsequently completed; pip check passed and resolved dependencies were
captured in `deploy/evaluation/requirements-windows.lock`. After prewarming a local
tokenizer cache, the network-blocked import/signature preflight passed with zero
network attempts. `add`, `cognify` and `search` are present. No provider calls made:
$0 of the $2 authorized cap spent. Request-budget enforcement and the paid synthetic
adapter/trial remain outstanding; this is not a quality evaluation result.

[Offline saved-result scorer](../../docs/testing/knowledge-backend-evaluation.md)
is available under TKT-0090. It is not an executed backend comparison.

`python -m tests.support.knowledge_discovery_input` (from campaign-core) exports
synthetic prose/provenance inputs without gold required IDs, expected paths or answers.
Tests ensure changing the answer key cannot alter discovery input. This is input
preparation only, not a Cognee run. The synthetic mixed-visibility corpus is suitable
for an isolated evaluator; do not reuse this exporter for live user-scoped indexing.

Validation: three input-isolation tests plus connected corpus regression passed (4
tests total); no provider calls, model installation or campaign changes.

## First paid synthetic smoke result

User selected Gemini 3.5 Flash Lite. Added and tested a persistent conservative
reservation gateway (four tests pass) covering requests, retries and concurrent
callers. Text-only, fixed models, bounded input/output, no paid tools/plugins, and
provider price ceilings. Failures retain reservations.

Cognee ingestion/extraction and graph export succeeded: 12 total nodes, 18 total
edges including infrastructure, four inspected domain edges. Two chat and six
embedding calls completed; $0.80 reserved of $2, actual cost unknown. Distinct islands
preserved; missed opposition relation and Eastwatch/castle conflation require attention.
See `deploy/evaluation/first-trial-findings.md`. Full benchmark/retrieval still pending.

## Retrieval follow-up and billing reconciliation

User confirmed $0.06 cumulative actual cost for the first eight calls. Added an
immutable billing checkpoint without deleting attempts; unknown/failed calls remain
reserved. Five guard tests and evaluation Ruff checks pass.

Three context-only questions against the existing graph succeeded; original source
text was returned for command destination, summoning location and opposition. No
re-extraction or answer generation. The missing opposition edge did not prevent
retrieval in this one-chunk corpus, but unsupported castle identity still appears
among generated descriptions. This does not establish cross-document retrieval quality.

Three additional embedding calls completed: $0.06 confirmed plus $0.30 reserved,
$1.64 unreserved under the $2 total cap. Query billing remains unconfirmed. Reports
stay in isolated local storage; findings document records limitations. Next work is
separate-source evaluation and stable claim/revision evidence binding, followed by
correction and privacy tests. Ticket remains in progress; no adoption decision yet.

## Separate-source probe

Two separately identified synthetic DataItems produced the Mara–Frostgate–Northreach
connection without pre-supplied edges. Stable data/source/revision bindings survive
in graph documents and chunks. `travelled_to` overstates "sent to", so generated labels
still cannot supply canonical assertions. Query embedding was denied by the budget
guard and Cognee retried until timeout; cross-document query success is not claimed.

Removed only the verified synthetic geography/r1 derivative with provider forwarding
disabled. Island, geography content and relationship disappeared; shared Frostgate
and dispatch survived (12/16 nodes/edges -> 8/10). Original synthetic text is preserved.
Replacement indexing, vector retrieval and visibility tests remain outstanding.

Nine offline tests pass. 27 completed calls total; $0.06 confirmed plus $1.90 reserved,
so additional paid requests wait on billing reconciliation. Full findings and next
steps: `deploy/evaluation/cross-document-findings.md`. No application redeploy or
canonical data change. Budget-denial retries need a terminal adapter status.

## Corrected billing and replacement follow-up

User corrected the earlier exact $0.06 report: first 27 calls together cost less than
$0.06. Appended an upper-bound checkpoint, retaining historical reports. New calls
automatically record provider `usage.cost`; invalid/missing billing and uncertain
failures keep reservations. Integer microdollar rounding is conservative.

Retired and replaced geography searches completed. No stale Northreach appeared;
Southreach appeared after geography/r2 indexing. However top_k=5 returns that detail
only in a generated description, not the supporting geography chunk. This is a
source-recall/grounding gap, not full shared-contract success. Source expansion and
revision/visibility revalidation are next. See cross-document-findings.md.

37 total calls; ten new costs sum to $0.000888 rounded upward, accounting ceiling
$0.060888 including the first-27 upper bound. Eleven offline tests plus Ruff pass.
No live-data transfer or application deployment. Full comparison remains open.

## Migration and rollback (trial)

Full corpus evidence-only run (2026-09-07): 24 queries completed across separately
prefiltered DM/party/conflict stores. All required evidence returned in 21 nonempty
target cases; mean recall@10 100% vs lexical 88.10%, precision 59.91% vs 50.66%.
No forbidden evidence IDs exposed; unknown query still returned unrelated context.
No answer-mode, semantic-path or support-role success claimed. Eighteen evaluator
tests and Ruff pass. Findings: `deploy/evaluation/corpus-findings.md`.
594 total attempts; conservative accounting $0.527012 includes $0.40 unknown-cost
reservations and first-27 upper bound. Adoption remains deferred pending Core-backed
projection/eligibility, known-link comparison, larger/repeated grounding tests and
dynamic permission/lifecycle validation. No production integration this turn.

Evidence expansion follow-up: evaluator now follows returned entity IDs to incoming
source chunks and emits exact excerpts, current manifest source/revision IDs, offsets
and association paths. Repeating the probe recovered both dispatch/r1 and geography/r2;
the raw context still omitted geography, verifying the expansion's specific benefit.
Summaries remain non-evidence. Fifteen tests and Ruff pass; 38 calls total, accounting
ceiling $0.060890. Whole-graph export and synthetic manifest are evaluation-only;
Core-backed scope/visibility/revision validation and full-corpus scoring remain open.
No adoption or production rollout is claimed.

Isolated evaluation data/indexes; no live cutover or provider content transfer without established provider authorization. Any adoption gets a separate rollout ticket.
