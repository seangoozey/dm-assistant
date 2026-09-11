---
id: TKT-0034
title: AI extraction harness with typed contracts and grounding
status: done
priority: P1
milestone: trustworthy-librarian
depends_on: [TKT-0033]
created: 2026-08-04
updated: 2026-08-05
---

# TKT-0034: AI Extraction Harness with Typed Contracts and Grounding

## Outcome

A bounded extraction abstraction over the OpenRouter provider that takes source text and a typed schema contract, returns structured candidates, and verifies each extracted assertion is grounded in the cited source span — so the system never trusts an ungrounded model output.

## Context

TKT-0033 provides the connection. This ticket builds the abstraction a domain pipeline uses: a typed contract for what an extraction returns, the call itself, and the grounding check that enforces the records-clerk boundary. Extraction output is always non-canonical; promotion remains the existing human-controlled path.

Read `docs/product/invariants.md`, `docs/product/truth-state-authority.md`, and `docs/architecture/domain-model.md`. Model output is a derived artifact: it does not outrank sources and never authorizes canonical mutation.

## Scope

- A typed extraction-contract schema mapping to claim dimensions (subject, predicate, object, state, authority, visibility, time, confidence) and candidate provenance.
- The harness that calls the provider (TKT-0033), validates the response against the contract, and rejects malformed or incomplete output.
- A grounding check: the extracted assertion text must align to a verifiable span of the submitted source text. Ungrounded output is rejected, not stored as fact.
- Deterministic recorded fixtures for offline testing of the harness, contract validation, and grounding rejection.
- Optional Windmill job scheduling for asynchronous extraction, since a source corpus may be large and extraction is not instantaneous.

## Out of scope

- Wiring the harness into capture or import paths (TKT-0035).
- The assertion-to-canon pipeline and candidate review flow (TKT-0035).
- Contradiction or consequence identification beyond what the extraction contract returns.
- Multi-model or provider-agnostic abstraction unless a demonstrated need exists.

## Acceptance criteria

- [x] A typed extraction contract defines the structured output the harness accepts.
- [x] The harness calls the OpenRouter provider and validates responses against the contract.
- [x] Malformed, incomplete, or contract-violating responses are rejected without partial storage.
- [x] A grounding check rejects extracted assertions that do not align to a cited source span.
- [x] The harness is fully testable offline against recorded fixtures.
- [x] No extraction output becomes canonical or bypasses the existing proposal path.
- [x] Sanitized tests and full repository validation pass.

## Implementation

- Added `domain.extraction` with `ExtractionHarness`, the typed `ExtractionContract`/`ExtractionResult`/`ExtractedAssertion` models, `ExtractionAuthority` enum (mirrors importer `CandidateAuthority` string values to avoid a circular import), and typed `ExtractionError`/`GroundingError` exceptions.
- The harness enforces three gates before returning: (1) the provider response parses as JSON and validates against `ExtractionContract`, (2) each assertion validates against domain enums and bounds (state restricted to observed/established/intended/prepared/possible; confidence 0–1), and (3) each assertion's `supporting_excerpt` appears verbatim in the source text after whitespace normalization.
- The harness takes a `ProviderClient` protocol seam, so production uses the `OpenRouterClient` (TKT-0033) and tests inject a `FixtureClient` with canned JSON — zero network access.
- The system prompt instructs the model to extract only assertions directly supported by the source and to copy excerpts verbatim; the grounding check is the deterministic backstop for confabulation.

## Validation

- 17 offline unit tests cover: clean single and multiple assertion extraction, empty-result handling, whitespace-normalized grounding, invalid JSON, non-object JSON, invalid state/authority/confidence values, missing fields, unknown fields, ungrounded excerpt rejection, too-short excerpt rejection, partial-match (paraphrase) rejection, workflow-state restriction, and custom extractor version.
- Ruff clean, strict mypy clean over 59 source files.
- Full repository validation passed: React tests, strict TypeScript, Windmill raw-app build, infrastructure policy checks, and all 38 retrieval fixtures.
- No schema change; no database path. The harness is a pure domain module with no persistence dependency.

## Validation plan

- Fixtures covering a clean extraction, a contract violation, and an ungrounded assertion rejection. ✓
- Prove no harness path writes to entities, claims, or relationships. ✓

### Live validation

The provider client (TKT-0033) and extraction harness were validated end-to-end against the real OpenRouter service using the configured `deepseek/deepseek-v4-flash-0731` model. Two real-world issues were caught and fixed that offline tests could not:

1. **Provider response fields.** The model returns `refusal`, `reasoning`, and `reasoning_details` on response messages. The original `ChatMessage` model used `extra="forbid"` (correct for outgoing requests), but this rejected valid provider responses. Fixed by adding `ResponseMessage` with `extra="ignore"` for incoming messages.

2. **Markdown-fenced JSON.** The model wraps structured output in ```` ```json ... `````` fences or adds prose around it, which `json.loads` rejects. Fixed by adding `_extract_json` which isolates the JSON payload from surrounding markdown/prose.

After these fixes, the live call produced 5 grounded assertions from synthetic source text ("The archivist Coreferra tends the eastern ledger of the Great Library. She founded the Order of the Golden Quill in 505CE to combat the spreading corruption."). All 5 passed the grounding check (excerpts verbatim from source), all carried correct state/authority/confidence values, and the contract validated cleanly. No canonical mutation occurred.

The throwaway validation script was removed after the check.
