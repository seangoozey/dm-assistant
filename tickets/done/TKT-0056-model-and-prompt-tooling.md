---
id: TKT-0056
title: Add model selection and prompt tooling
status: done
priority: P1
milestone: planning-workspace
depends_on: [TKT-0055]
created: 2026-08-09
updated: 2026-08-10
---

# TKT-0056: Add Model Selection and Prompt Tooling

## Outcome

The Tools area exposes Campaign Core-owned AI configuration. Controlled model profiles can be inspected and explicitly activated; `deepseek/deepseek-chat` is the default extraction model. The effective prompt and immutable version are visible without exposing credentials.

## Acceptance criteria

- [x] Tools lists controlled profiles and shows active provider, slug, reasoning, token cap, timeout, retry limits, and suitability.
- [x] `deepseek/deepseek-chat` is the default active extraction profile.
- [x] Activation is explicit, registry-validated, DM-only, durable, and returns an auditable receipt.
- [x] The complete effective prompt and immutable version are visible.
- [x] Extraction resolves the active profile at execution time and snapshots configuration and prompt identifiers with the run.
- [x] Arbitrary model identifiers and provider secrets never reach the browser or Windmill worker.
- [x] Tests cover registry validation, activation, persistence, API authorization, UI behavior, and extraction binding.
- [x] Full validation and local deployment pass.

## Deferred follow-up

Editable prompt-version creation and side-by-side comparison remain follow-up scope after reliable model selection is proven; historical prompt text must never be overwritten.

## Validation evidence

- `tests/validate_repository.py`: 264 passed, 26 skipped; Ruff, mypy, Windmill source policy, React tests/typecheck, raw-app build, and retrieval corpus passed.
- `deploy/test-stack.ps1 up`: rebuilt Campaign Core, applied migration 0014, and deployed the Windmill app.
- Live Campaign Core configuration returned `deepseek/deepseek-chat`, prompt `extraction/7`, and no browser-visible credential.
- Explicit activation receipt: `14ceca11-80bc-4f56-90ec-d46cfc51b480`.

## Follow-up work

- Prompt editing, immutable prompt-version creation, and side-by-side evaluation remain intentionally deferred.
