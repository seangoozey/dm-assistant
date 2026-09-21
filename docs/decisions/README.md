# Architecture Decision Records

ADRs capture durable technical decisions and their consequences.

## Status values

- `proposed`
- `accepted`
- `superseded`
- `rejected`

## Rules

- Use the next numeric ID.
- Describe context, decision, consequences, and alternatives.
- Do not silently rewrite an accepted decision. Add a new ADR that supersedes it.
- Tentative platform choices remain `proposed` until their acceptance criteria are demonstrated.

## Index

- [ADR-0014: Shared campaign relationship and retrieval layer](ADR-0014-shared-campaign-knowledge.md) — proposed
- [ADR-0015: Three-layer system — canon under the hood, authored documents, derived presentation](ADR-0015-three-layer-presentation.md) — accepted (user ruling 2026-09-15)
- [ADR-0016: Every page is editable, and edit mode has a guarded lifecycle](ADR-0016-editable-pages-guarded-lifecycle.md) — accepted (user ruling 2026-09-16)
- [ADR-0017: Domain Vocabulary Declaration](ADR-0017-domain-vocabulary-declaration.md) — accepted (user ruling 2026-09-19)
- [ADR-0018: The Promotion Pipeline — one Proposal → Candidate → Claim progression for every surface](ADR-0018-promotion-pipeline.md) — proposed (shaping rulings 2026-09-20)
- [ADR-0001: Windmill as application infrastructure](ADR-0001-windmill-infrastructure.md) — proposed
- [ADR-0002: Dedicated Campaign Core](ADR-0002-dedicated-campaign-core.md) — proposed
- [ADR-0003: PostgreSQL canonical store](ADR-0003-postgresql-canonical-store.md) — proposed
- [ADR-0004: Local Git and CLI deployment](ADR-0004-local-git-cli-deployment.md) — proposed
- [ADR-0005: Referenceable records and controlled kinds](ADR-0005-referenceable-records-and-controlled-kinds.md) — accepted
- [ADR-0006: First-class plans and agency boundaries](ADR-0006-first-class-plans-and-agency.md) — accepted
- [ADR-0007: Campaign chronology as integer-year values with a calendar spec](ADR-0007-campaign-chronology.md) — accepted
- [ADR-0008: OpenRouter as the V1 AI provider](ADR-0008-openrouter-v1-ai-provider.md) — accepted
- [ADR-0009: Controlled AI model profiles](ADR-0009-controlled-ai-model-profiles.md) — accepted
- [ADR-0010: Minimal AI fact-discovery contract](ADR-0010-minimal-ai-fact-discovery-contract.md) — accepted
- [ADR-0011: Assertion-primary claims](ADR-0011-assertion-primary-claims.md) — accepted
- [ADR-0012: Provenance-first claims with optional structure](ADR-0012-provenance-first-claims.md) — accepted; supersedes ADR-0011's required-subject decision
- [ADR-0013: Sessions and encounters are independent many-to-many contexts](ADR-0013-sessions-and-encounters.md) — accepted
