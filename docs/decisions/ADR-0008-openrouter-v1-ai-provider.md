# ADR-0008: OpenRouter as the V1 AI Provider

- Status: accepted
- Date: 2026-08-04

## Context

Assertion extraction, contradiction surfacing, and consequence identification are AI tasks that require a language-model provider. Campaign Core needs an initial provider connection before any extraction pipeline or thinking-workflow experience can be built.

The provider is infrastructure: a typed, cost-bounded HTTP connection to an external service. Model output is a derived artifact that never outranks Campaign PostgreSQL and original sources. The extraction boundary (TKT-0034) enforces grounding and keeps output non-canonical; the provider itself carries no domain authority.

The owner selected OpenRouter as the v1 provider. Structured extraction initially used `deepseek/deepseek-v4-flash-0731`, but live runs exhausted the entire completion allowance on mandatory reasoning without returning content. TKT-0054 proved the non-reasoning extraction path with `deepseek/deepseek-chat`; TKT-0055 evaluates the owner-selected `openai/gpt-5-nano`. OpenRouter model metadata reports that GPT-5 Nano requires reasoning and supports `minimal`, `low`, `medium`, and `high`, so reasoning cannot be disabled for this model.

## Decision

Use OpenRouter as the AI provider for version 1, targeting `openai/gpt-5-nano` for structured extraction with `reasoning.effort` set to `minimal` and reasoning output excluded. The provider client (TKT-0033) is a typed boundary with configurable credentials, timeout, retry, and token/cost limits.

Structured extraction requests use strict `json_schema` response mode generated from the Pydantic extraction wire contract. All properties are required, nullable values are explicit, and additional properties are forbidden. Campaign Core still parses, validates, checks coverage, and grounds the returned data locally; provider enforcement is not a canonical trust boundary. The fixed 8,192-total-token completion allowance accommodates both mandatory minimal reasoning and representative claim JSON. A response ending with `finish_reason=length` is rejected explicitly as truncated rather than passed to JSON parsing. An HTTP-success response with empty assistant content remains unusable provider output: the client retries it within the existing retry count and, if exhausted, reports only bounded finish-reason and completion-token diagnostics.

This decision names the v1 provider and model only. It does not guarantee OpenRouter or this model for future versions. The provider boundary is a single interface; a future version may target a different OpenRouter model, a different OpenAI-compatible endpoint, or a local model without changing the extraction harness or any domain logic, provided the new provider satisfies the same typed contract.

Provider credentials are isolated inside Campaign Core. Windmill workers never receive AI-provider credentials, consistent with the canonical-credential boundary in ADR-0001 and the overview architecture.

## Consequences

- Campaign Core can make typed, bounded AI requests against a real provider for the first time.
- The provider connection is testable offline against recorded fixtures with no network access.
- Changing the provider or model in a future version is a bounded modification to the provider client, not a domain or extraction-harness change.
- OpenRouter availability, latency, cost, and the selected model's quality constrain v1 extraction behavior. These are operational properties of the v1 choice, not architectural commitments.
- Reasoning tokens count against the configured output cap. GPT-5 Nano's lowest supported effort limits that overhead; reasoning text is excluded from the response.
- A dependency on OpenRouter is introduced; the rationale is documented as required by the engineering expectations.

## Alternatives considered

- **Direct OpenAI API:** rejected for v1 because the owner selected OpenRouter, which provides model selection flexibility including the chosen DeepSeek model without a separate account per provider.
- **A local/self-hosted model:** deferred. No local inference infrastructure exists yet, and the provider boundary is designed so a local model can replace OpenRouter in a future version without changing the extraction layer.
- **A provider-agnostic multi-provider abstraction from the start:** rejected as premature. The v1 client targets one provider behind a typed interface; generalization follows a demonstrated second-provider need, not speculation.
