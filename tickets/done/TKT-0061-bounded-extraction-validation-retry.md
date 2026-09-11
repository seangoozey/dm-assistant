---
id: TKT-0061
title: Retry transient extraction validation failures
status: done
priority: P1
milestone: planning-workspace
depends_on: [TKT-0060]
created: 2026-08-10
updated: 2026-08-10
---

# TKT-0061: Retry Transient Extraction Validation Failures

## Outcome

A single malformed or semantically invalid model response triggers one fresh bounded extraction attempt inside the same background job instead of requiring manual retry.

## Acceptance criteria

- [x] The harness allows exactly two extraction attempts by default.
- [x] Parsing, schema, grounding, and coverage failures may trigger the second attempt.
- [x] No partial result from a failed attempt is stored.
- [x] The final typed error remains visible when both attempts fail.
- [x] Attempt count is configurable and cannot be below one.
- [x] Extractor version is `extraction/7`; tests and validation pass.

## Validation evidence

- Focused extraction tests: 45 passed, including malformed-first/valid-second, both malformed, and invalid configuration cases.
- Repository validation: 258 Python tests passed, 26 skipped; 27 React tests passed; lint, types, policies, build, and retrieval corpus passed.
- Local Campaign Core image rebuilt and both service health checks passed.
