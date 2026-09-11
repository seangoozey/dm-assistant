---
id: TKT-0050
title: Preserve immutable extraction revisions and report task outcomes accurately
status: done
priority: P1
milestone: planning-workspace
depends_on: [TKT-0049]
created: 2026-08-09
updated: 2026-08-09
---

# TKT-0050: Preserve Immutable Extraction Revisions and Report Task Outcomes Accurately

## Outcome

Re-extraction appends a new immutable extraction run, review reads expose only its latest result, and a background job whose every candidate fails is displayed as failed rather than succeeded.

## Acceptance criteria

- [x] Re-extraction never updates or deletes an immutable extraction row.
- [x] An extraction run is recorded even when it produces zero claims.
- [x] Candidate review reads return only the latest extraction run.
- [x] Historical extraction rows remain available for audit.
- [x] A transport-successful Windmill job with zero successful candidate results is reported as failed.
- [x] Partial batches retain successful results and report their failed item count.
- [x] Regression tests and full repository validation pass.

## Implementation

- Added append-only `candidate_extraction_runs` and grouped both legacy and new extraction rows by run.
- Replaced destructive re-extraction with a new run plus immutable claim inserts.
- Changed candidate and document review projections to count and return only the latest run.
- Classified an all-item batch failure as a failed background task while preserving partial success semantics.
- Normalized the single and batch extraction action styles.

## Validation

- Focused candidate extraction and migration tests pass.
- Ruff and strict mypy pass.
- 238 Python tests pass with 26 integration skips.
- 25 React tests and strict TypeScript pass.
- Windmill source policy, raw-app build, Compose policy, and the 38-case retrieval corpus pass.
- Migration `0012_candidate_extraction_runs` applied successfully to the local development database.
