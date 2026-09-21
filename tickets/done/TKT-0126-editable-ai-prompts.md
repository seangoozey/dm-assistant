---
id: TKT-0126
title: Editable, versioned AI prompts in Core configuration
status: done
priority: P2
milestone: shared-campaign-knowledge
depends_on: [TKT-0120, TKT-0124]
created: 2026-09-17
updated: 2026-09-17
---

# TKT-0126: Editable, versioned AI prompts in Core configuration

## Context (Sean, 2026-09-17, closing TKT-0120)

"The prompts that get called need to be in config, and they need to be editable."

Prompts currently live as constants in Core (`prose/3` in prose_drafting.py, `extraction/8` in domain/extraction.py). Prompt quality is now a live iteration surface — Sean's Fleurite tests have already driven two revisions (description-not-summarization; anti-meta-language + kind-aware relevance) — and each iteration should not require a code deploy.

## Scope

- **Prompt overrides stored in Campaign Core** (receipted, like model activation): a prompt override per purpose (extraction, prose) with its text, a version label, and a filed receipt. Overrides sit on top of built-in defaults; clearing an override restores the default.
- **Settings → AI models gains a prompt editor** per purpose: current effective prompt (default or override) with version, edit + save (receipted), reset-to-default. DM-gated through Core like activation.
- **Version discipline**: saving an override stamps its version (e.g. `prose/local-3`); drafts and extraction runs record the version they used (already part of receipts/results).
- **Quality iteration continues here**: prompt rules are the lever for drafting behavior Sean flags in real use — currently open findings from the Route B test are addressed by prose/3 (shipped), but further findings (over-inclusion of testimony, pacing, voice) land as prompt edits, not code.

## Out of scope

- Multi-prompt regimes (A/B) — one effective prompt per purpose.
- Editing the extraction prompt's structural contract (the JSON schema expectations) — text only.

## Validation evidence

(to record when built)

## Validation evidence

Delivered 2026-09-18, deployed, live-verified.

- **Core** (`application/prompt_configuration.py` + migration 0061): `prompt_overrides` with a `prompt_override_receipts` audit table — every save/clear files a receipt; versions stamp `<purpose>/default` or `<purpose>/local-<n>` (receipt count per purpose). Both prompts are editable (extraction + prose); the prose override is validated to keep its JSON response contract (the structural contract cannot be edited away). `GET /ai/prompts`, `PUT /ai/prompts/{purpose}`, `DELETE /ai/prompts/{purpose}` (DM-gated, 422 on bad purpose/contract).
- **Harnesses consume effective prompts**: ProseHarness and ExtractionHarness take an optional `system_prompt` (defaulting to the built-ins); the prose draft endpoint and the extraction builder fetch the effective prompt per request and record its version label on results/runs (drafts now report `prose/local-N` while overridden).
- **Settings editor**: the AI models section gains per-purpose prompt panels — version badge (built-in vs Override active · label), textarea, Save override (receipted, toast with version + receipt), Reset to default, and the contract note. Bridge routes + client methods shipped with the backend from day one.
- Validation: Core — 6 local prompt-configuration tests (defaults, version stamping, clear+audit, contract enforcement, unknown purpose, API DM-only/edit/reset) + docker 7/7 (migration 0061 + durable overrides); full local suite 481 passed. React 131/131 incl. the Settings editor flow (edit → save through Core → Override active · prose/local-1 + toast). Live: GET /ai/prompts serves both defaults post-deploy.
