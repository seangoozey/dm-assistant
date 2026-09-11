---
id: TKT-0033
title: OpenRouter AI provider integration
status: done
priority: P1
milestone: trustworthy-librarian
depends_on: []
created: 2026-08-04
updated: 2026-08-05
---

# TKT-0033: OpenRouter AI Provider Integration

## Outcome

Campaign Core can make typed, cost-bounded, retryable requests to OpenRouter using the `deepseek/deepseek-v4-flash-0731` model, with credentials isolated from Windmill workers per the architecture boundary.

## Context

Assertion extraction, contradiction surfacing, and consequence identification are AI tasks. The system needs a provider connection before any of that is possible. This ticket is strictly plumbing: the HTTP connection, credentials, contracts, and testability. It contains no domain logic and no extraction behavior.

Read `docs/decisions/ADR-0008-openrouter-v1-ai-provider.md`, `docs/architecture/overview.md`, `docs/product/invariants.md`, and `docs/product/truth-state-authority.md`. ADR-0008 names OpenRouter as the v1 provider with the model `deepseek/deepseek-v4-flash-0731` without guaranteeing it for future versions. The provider is infrastructure; derived artifacts and model output never outrank Campaign PostgreSQL and original sources (invariant: derived systems).

## Scope

- An HTTP provider client targeting OpenRouter with the pinned model `deepseek/deepseek-v4-flash-0731`.
- Credential configuration through environment/config, never committed, never available to Windmill workers.
- Typed request and response contracts at the boundary (Pydantic models).
- Timeout, retry, and per-request cost/token limits so a runaway request cannot exceed a bounded budget.
- A test harness using recorded fixtures so the provider client is testable without real API calls or network access.
- Documentation of why this dependency is needed (engineering expectation: no dependency without justification).

## Out of scope

- Extraction contracts, grounding checks, or any domain logic (TKT-0034).
- Wiring into capture, import, or any workflow (TKT-0035).
- Windmill job scheduling (TKT-0034 where async work lives).
- Streaming, tool-use, or multi-turn conversation unless a demonstrated need exists.
- Provider selection UI or runtime model switching.

## Acceptance criteria

- [x] A typed provider client sends a request to OpenRouter and validates the response against a typed contract, implementing ADR-0008.
- [x] The pinned model is `deepseek/deepseek-v4-flash-0731`.
- [x] The client is structured as a single interface so a future provider or model change is a bounded modification, not a domain change (per ADR-0008).
- [x] Credentials are supplied through configuration and are never committed or passed to Windmill workers.
- [x] Requests are bounded by configurable timeout, retry, and token/cost limits.
- [x] The client is fully testable offline against recorded fixtures with no network access.
- [x] A documented rationale for the dependency is recorded.
- [x] Sanitized tests and full repository validation pass.

## Implementation

- Added `adapters.openrouter` package: typed `ChatCompletionRequest`/`ChatCompletionResponse` models (Pydantic, frozen, extra-forbid/ignore at the boundary), typed exceptions (`OpenRouterAuthError`, `OpenRouterTimeoutError`, `OpenRouterRateLimitError`, `OpenRouterServerError`, `OpenRouterContractError`), and `OpenRouterClient` — the single typed interface with configurable timeout, retry (exponential backoff on 429/5xx), max-tokens cap, and the v1 model `deepseek/deepseek-v4-flash-0731`.
- The client uses a `Transport` protocol seam; production uses `httpx` (promoted from dev to production dependency), tests inject `FixtureTransport` so the entire client is exercisable offline with zero network access.
- Added OpenRouter settings to `Settings` (`openrouter_api_key`, `openrouter_base_url`, `openrouter_model`, `openrouter_max_tokens`, `openrouter_timeout_seconds`, `openrouter_max_retries`) under the `CAMPAIGN_` env prefix. The API key defaults to empty and is supplied only through configuration.
- Documented the dependency rationale in ADR-0008 (Alternatives + Consequences) and the README tentative stack.

## Validation

- 19 offline unit tests cover client construction (missing key, default model, custom model), successful completion (typed result, request payload, authorization header, URL targeting), error handling (401/403 auth, 429 rate-limit-after-retry, 503 server-error-after-retry, unexpected status), contract validation (missing choices, missing usage, empty choices), retry (rate-limit-then-recover), and request validation (empty messages, empty content, non-positive max_tokens).
- No credential appears in source, tests, or fixtures; the test key is the literal `"test-key"` and no real key is present.
- Ruff clean, strict mypy clean over 58 source files.
- Full repository validation passed: React tests, strict TypeScript, Windmill raw-app build, infrastructure policy checks, and all 38 retrieval fixtures.
- No database schema change; this ticket is infrastructure-only.

## Validation plan

- Unit-test the client against recorded fixtures covering success, retry, timeout, and contract-violation responses. ✓
- Verify no credential appears in source, tests, or fixtures. ✓
- Confirm the configuration boundary keeps the credential inside Campaign Core only. ✓
