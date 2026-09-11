---
id: TKT-0054
title: Use a non-reasoning model for structured extraction
status: done
priority: P1
milestone: planning-workspace
depends_on: [TKT-0053]
created: 2026-08-09
updated: 2026-08-09
---

# TKT-0054: Use a Non-Reasoning Model for Structured Extraction

## Outcome

Structured extraction uses DeepSeek's non-reasoning chat model so the bounded completion budget is available for claims, and provider exceptions become ordinary per-candidate failures rather than Campaign Core 500 responses.

## Acceptance criteria

- [x] The pinned extraction model is `deepseek/deepseek-chat`.
- [x] Extraction requests send no reasoning configuration.
- [x] The 4,096-token output and existing retry/timeout limits remain unchanged.
- [x] Provider exceptions return a typed extraction error result instead of HTTP 500.
- [x] Deployment defaults, documentation, and tests agree on the model.
- [x] Full validation and a live extraction succeed.

## Implementation

- Replaced the reasoning-only Flash model with non-reasoning `deepseek/deepseek-chat` for structured extraction.
- Omitted unset request fields so no `reasoning` key reaches OpenRouter.
- Wrapped provider exceptions at the extraction boundary so they become per-candidate error results rather than HTTP 500 responses.
- Updated the provider ADR, repository overview, Compose default, runtime default, and tests.

## Validation

- Full validation passes: 249 Python tests with 26 integration skips, 25 React tests, Ruff, strict mypy and TypeScript, Windmill build/source policy, Compose policy, and the retrieval corpus.
- Campaign Core rebuilt and deployed successfully.
- A live `extraction/3` run for the representative PC backstory completed in about 58 seconds with 15 claims, 14 source segments, 14 coverage entries, and no error.
