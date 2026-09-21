---
id: TKT-0090
title: Establish cross-workflow knowledge benchmark
status: done
priority: P0
milestone: shared-campaign-knowledge
depends_on: [TKT-0089]
created: 2026-09-06
---

# Outcome

Create a sanitized corpus of at least 24 connected-knowledge cases and capture the current retrieval baseline. Cover Ask, encounters, Lore, Brainstorm, and lifecycle/visibility boundaries.

## Required reading

- [Shared Campaign Knowledge](../../docs/architecture/shared-campaign-knowledge.md)
- [ADR-0014](../../docs/decisions/ADR-0014-shared-campaign-knowledge.md)
- [ADR-0012](../../docs/decisions/ADR-0012-provenance-first-claims.md)

## Scope

Cases specify required and forbidden evidence and paths, not exact generated prose; measure recall@10, precision@10, unsupported connections, latency and deterministic ordering. Include the Tsunadis/Mythis Minor/Ragnok distinction and preserve the existing 38-case regression corpus.

## Acceptance and validation

Benchmark runner produces a reproducible machine-readable report; at least four cases per primary workflow; remaining cases cover hidden paths, supersession and ambiguity. Record measured baseline and agreed relevance targets before backend comparison.

## Migration and rollback

Test fixtures only; do not mutate live campaign data.

## Progress — 2026-09-06

- Added 24 typed synthetic scenarios with required/forbidden evidence and paths.
- Added offline lexical-policy runner, deterministic regression checks and captured JSON baseline.
- Baseline recall@10 0.881, precision@10 0.463, mode accuracy 0.333; paths unsupported.
- Existing retrieval tests plus benchmark: 48 passed.
- See [benchmark scope and targets](../../docs/testing/connected-knowledge-benchmark.md).
- Remains in progress: targets need agreement; service/database latency and executable
  path-safety scoring are not established by this offline simulation. Do not treat
  this report as a completed backend evaluation or live workflow verification.

## Offline comparative scoring preparation

Added a typed saved-result scorer for lexical, known-link and LLM-discovery arms.
Reports missing/error cases, ranking metrics, mode/path matches and forbidden or
unknown returned evidence. Validates duplicate inputs and records model/configuration
identity; cost and timing remain unknown unless supplied. Semantic grounding is
explicitly unassessed, not claimed safe. See
[runner documentation](../../docs/testing/knowledge-backend-evaluation.md).
Validation: 9 evaluation/input/corpus tests passed; Ruff clean. No Cognee run yet.

## Closure

Delivered: benchmark corpus (24 typed scenarios), offline lexical-policy runner, deterministic regression checks, and captured baselines (2026-09-06). Its backend-comparison role was absorbed by TKT-0096/0104. Closed 2026-09-14 at ticket audit — Sean confirmed delivered.
