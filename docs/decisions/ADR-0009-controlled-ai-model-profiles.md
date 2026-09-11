# ADR-0009: Controlled AI Model Profiles

- Status: accepted
- Date: 2026-08-10
- Supersedes: the model-selection portion of ADR-0008

## Context

OpenRouter remains the provider boundary selected in ADR-0008. Representative GPT-5 Nano extraction repeatedly failed through malformed output, missing coverage references, unsupported excerpts, and provider errors. The extraction model must be changeable without accepting arbitrary browser-supplied identifiers, hiding the effective prompt, or losing which configuration produced an extraction run.

## Decision

Campaign Core owns a controlled registry of model profiles. `deepseek/deepseek-chat` is the default and recommended extraction profile. The DM-only Tools interface may inspect and explicitly activate selectable profiles. Activation is durable and returns a receipt. Provider credentials remain server-side.

Every extraction resolves the active profile when execution begins and snapshots the profile key, provider model slug, and immutable prompt version on its append-only extraction run. The complete effective system prompt and its version are visible in Tools. Prompt editing and arbitrary model identifiers are outside the initial interface.

## Consequences

- Model changes are explicit and auditable.
- Historical extraction runs retain configuration provenance.
- Unsuitable evaluated profiles can remain visible without being selectable.
- Adding a model requires a code-reviewed registry change until a later governed schema-builder exists.
