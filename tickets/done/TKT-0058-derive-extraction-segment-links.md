---
id: TKT-0058
title: Derive extraction segment links deterministically
status: done
priority: P1
milestone: planning-workspace
depends_on: [TKT-0052]
created: 2026-08-10
updated: 2026-08-10
---

# TKT-0058: Derive Extraction Segment Links Deterministically

## Outcome

Campaign Core derives claim-to-segment citations and coverage claim indexes from verbatim supporting excerpts rather than rejecting otherwise grounded output because of model bookkeeping mistakes.

## Acceptance criteria

- [x] Supporting excerpts remain verbatim-grounded before reconciliation.
- [x] Claim segment IDs are derived from deterministic source segments.
- [x] Coverage claim indexes are derived from the reconciled claims.
- [x] Missing, duplicate, unknown, and genuinely uncovered coverage remains rejected.
- [x] The extractor version is incremented to `extraction/4`.
- [x] Tests and full repository validation pass.

## Validation evidence

- Focused extraction tests: 40 passed, including deliberately inconsistent model bookkeeping reconciled to grounded segment `s1` and claim index `0`.
- Repository validation: 253 Python tests passed, 26 skipped; 27 React tests passed; lint, types, policies, build, and retrieval corpus passed.
- Local Campaign Core image rebuilt and health checks passed.
