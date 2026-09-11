---
id: TKT-0049
title: Durable background AI extraction jobs
status: done
priority: P1
milestone: planning-workspace
depends_on: [TKT-0048]
created: 2026-08-09
updated: 2026-08-09
---

# TKT-0049: Durable Background AI Extraction Jobs

## Outcome

AI extraction runs as durable Windmill background work. The migration workspace stays responsive, survives refreshes, exposes job state, and bounds retry, token, and batch cost exposure.

## Acceptance criteria

- [x] Individual extraction and re-extraction return immediately with a durable job ID.
- [x] Document batches execute sequentially in a background job with an explicit size limit.
- [x] Job state survives browser refresh and completion refreshes candidate data.
- [x] Browsing and review controls are not globally disabled during AI calls.
- [x] Provider timeout, retry, output-token, and batch limits are explicit.
- [x] Partial batch failures are reported without discarding completed extraction results.
- [x] Sanitized tests and full repository validation pass.

## Implementation

- Added a durable Windmill candidate-extraction job with a maximum batch size of 50.
- Individual, repeat, and document-batch extraction now return a job ID immediately.
- Persisted the active extraction job in session storage and recover polling after refresh.
- Kept document navigation and completed review work enabled while extraction runs.
- Returned per-candidate batch outcomes so one failure does not discard successful work.
- Reduced defaults to 4,096 output tokens, a 45-second provider timeout, and one retry.
- Added job adapter and UI regression coverage.

## Validation

- Ruff and strict mypy pass, including three Windmill Python sources.
- 237 Python tests pass with 26 integration skips.
- 24 React tests and strict TypeScript pass.
- Windmill source policy, raw-app build, and 38-case retrieval corpus pass.
