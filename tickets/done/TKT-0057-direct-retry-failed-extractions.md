---
id: TKT-0057
title: Retry failed extractions from Background Tasks
status: done
priority: P1
milestone: planning-workspace
depends_on: [TKT-0049]
created: 2026-08-10
updated: 2026-08-10
---

# TKT-0057: Retry Failed Extractions from Background Tasks

## Outcome

A failed single or grouped extraction can be retried directly from its Background Tasks card without navigating through the document and candidate workflow.

## Acceptance criteria

- [x] Extraction job state retains the submitted candidate IDs across polling and session persistence.
- [x] A failed task offers a direct retry action.
- [x] A partially failed grouped task retries only its failed candidates.
- [x] The prior failure remains visible until a replacement job is successfully queued.
- [x] Tests cover direct retry and targeted grouped retry behavior.
- [x] Full repository validation passes.

## Validation evidence

- React tests: 27 passed, including direct failed-task retry and failed-only grouped retry.
- Repository validation: 253 Python tests passed, 26 skipped; Ruff, mypy, policies, strict TypeScript, raw-app build, and retrieval corpus passed.
- Local stack deployment succeeded and pushed the four updated raw-app files to `dm-assistant-dev`.
