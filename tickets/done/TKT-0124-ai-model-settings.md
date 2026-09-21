---
id: TKT-0124
title: AI model configuration moves to Settings with per-purpose profiles
status: done
priority: P2
milestone: shared-campaign-knowledge
depends_on: [TKT-0114]
created: 2026-09-16
updated: 2026-09-16
---

# TKT-0124: AI model configuration moves to Settings with per-purpose profiles

## Context (Sean, 2026-09-16)

"The chosen model for graphing is probably not the right model for prose writing. We are also rapidly approaching a time where we need to move the ai model stuff out of tools and into settings and give it a real selection interface."

Today the AI model surface is a single extraction profile selector buried in the Tools page, backed by a registry with one global active profile (`ai_configuration.py`: PROFILES tuple, one receipt stream, `ai_configuration_activations` has no purpose column). The Fleurite drafting trial (TKT-0120, 2026-09-16) confirmed a prose writer is worth building with its own model needs — a cheap, modestly unintelligent drafter rather than the extraction/graph model.

## Scope

- **Purposes in the Core registry**: `ModelProfile` carries a `purpose`; purposes are declared with label/description/prompt (extraction ships its prompt as today; prose declares with no prompt and **no profiles yet** — the model choice is Sean's upcoming decision, and the interface must exist before the model hunt so a chosen candidate lands as one registry entry).
- **Per-purpose activation**: receipts record purpose (migration 0060 backfills existing rows to `extraction`); snapshot serves per-purpose active keys and last receipts; `activate(purpose, profile_key)`. Extraction's default (`deepseek-chat`) and all existing receipts keep their meaning — no behavior change for the live extraction path.
- **Settings gets a real selection interface**: an "AI models" section in Settings with one panel per purpose — active profile card (provider, reasoning, limits, timeout, retries, suitability), a select over that purpose's selectable profiles, Activate through Core (DM-gated, receipted, toast-bused), and the prompt preview for purposes that have one. Prose shows an explicit empty state ("no prose model chosen yet") so the slot is visible, not missing.
- **Tools loses the AI panel** — the model surface lives in Settings; Tools returns to operations (capture, conflicts, clocks, gaps).

## Out of scope

- Choosing any prose model (that's the model hunt; this ticket builds the shelf it lands on).
- A graph purpose in the registry — the graph/semantic work is parked and has no Core provider consumer; the purpose taxonomy extends when that work resumes.
- Writer profile runtime/wiring — TKT-0120.

## Validation evidence

Delivered 2026-09-16, deployed, live-verified.

- **Core**: `ai_configuration.py` rebuilt around purposes — `PurposeInfo` (key/label/description/prompt), `ModelProfile.purpose`, per-purpose `active_profile_by_purpose`/`last_activation_by_purpose` in the snapshot, `activate(purpose, profile_key)` validates purpose ∈ registry and profile ∈ purpose. Prose purpose declared with no prompt and no profiles (the model hunt decides). `activate` endpoint takes `purpose` defaulting to `extraction` so the windmill review bridge keeps working unchanged. Extraction call site + prompt-version derivation now go through the purpose lookup.
- **Migration 0060**: `ai_configuration_activations.purpose text NOT NULL DEFAULT 'extraction'` — every pre-existing receipt is an extraction receipt; no invented prose receipts.
- **UI**: new `AIModelSettings` section in Settings (per-purpose panels: active model card with provider/reasoning/limits/timeout/retries/suitability, model select with locked options visible, Activate through Core, prompt preview for purposes with one, activation receipt line; prose shows the explicit no-model-chosen empty state and no selector). Activation outcomes emit into the toast bus. The Tools AI panel and its App-level state are removed. Glossary gains "AI model profile" (Workflow and audit) with the test-enforced registry rule satisfied.
- **Tests**: Core local 462 passed/71 skipped (test_ai_configuration rewritten: default extraction, prose-empty purpose, per-purpose durable activation, cross-purpose activation rejected, unknown purpose rejected, endpoint purpose default); docker 9/9 in test_ai_configuration incl. `test_postgres_activations_are_per_purpose` (migration + receipts). React 122/122 incl. per-purpose Settings management (select → activate called with purpose, toast) and Tools-holds-no-AI-panel.
- **Live**: `GET /ai/configuration` after deploy serves both purposes, profiles tagged extraction, active `{extraction: deepseek-chat}`, prior receipt intact — migration preserved history.

## Follow-up

- **DONE 2026-09-16**: the model hunt's first pick landed exactly as designed — `deepseek-v4-flash` (openrouter `deepseek/deepseek-v4-flash-0731`, non-reasoning, suitability `candidate`) as a single `PROFILES` entry with `purpose="prose"`. Settings lists it in the prose panel immediately; activation is Sean's receipted click (deliberately not pre-activated). Tests updated: prose candidate is listed-not-active until activation, prose activation leaves extraction untouched; React prose panel shows the option beside the not-yet-active state. Docker 9/9, React 122/122, live-verified served post-deploy.
- A graph purpose joins the registry only when that parked work resumes with a Core provider consumer.
