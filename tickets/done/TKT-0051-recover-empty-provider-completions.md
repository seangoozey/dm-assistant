---
id: TKT-0051
title: Recover empty provider completions during extraction
status: done
priority: P1
milestone: planning-workspace
depends_on: [TKT-0050]
created: 2026-08-09
updated: 2026-08-09
---

# TKT-0051: Recover Empty Provider Completions During Extraction

## Outcome

Extraction reserves enough output budget for structured claims, retries unusable empty provider completions, and reports diagnostic finish/token information if the provider still returns no content.

## Acceptance criteria

- [x] Extraction requests bound reasoning separately from the existing total output-token cap.
- [x] Extraction requests ask for a JSON object response.
- [x] HTTP-success responses with empty content are retried within the existing retry limit.
- [x] Exhausted empty responses report finish reason and completion-token usage without exposing prompts or credentials.
- [x] Existing provider timeout, retry, and cost limits remain bounded.
- [x] Tests and full repository validation pass.

## Implementation

- Reserved at most 1,024 of the existing 4,096 output tokens for model reasoning.
- Requested JSON-object responses for extraction calls.
- Retried empty HTTP-success completions within the existing single-retry bound.
- Added safe exhausted-retry diagnostics containing finish reason and completion-token count.

## Validation

- 42 focused provider/extraction tests pass.
- Ruff and strict mypy pass.
- 241 Python tests pass with 26 integration skips.
- 25 React tests, strict TypeScript, Windmill build/source policy, Compose policy, and the retrieval corpus pass.
- Campaign Core rebuilt successfully with the updated provider client.
