# ADR-0014: Shared Campaign Relationship and Retrieval Layer

- Status: proposed
- Date: 2026-09-06
- Supplements ADR-0012; optional claim structure remains unchanged.

## Context

Relationships underpin encounters, Ask, Lore, Brainstorm and library navigation. Existing PostgreSQL relationships and provenance are not consistently traversed by lexical retrieval. Per-page search additions cannot supply a consistent model of campaign connections.

## Decision proposed

Introduce one Campaign Core knowledge service with typed record references, evidence paths, common ranking, and visibility/time/lifecycle filtering. Distinguish recorded semantic relationships, evidence associations and suggested associations. Keep complete assertions authoritative and enrichment optional. Implement an initial rebuildable PostgreSQL projection and compare alternate retrievers against the same acceptance corpus before selecting Cognee or a dedicated graph backend.

## Consequences

Clarification following user confirmation: evaluate Cognee with LLM-based relationship
discovery from prose, initially verifying the existing OpenRouter provider route.
Known-link projection is a baseline, not the complete discovery feature. Derived
links may automatically assist retrieval without individual canonical approval;
promotion into campaign truth remains reviewed. Record embedding configuration
separately. Backend adoption, model selection and live rollout remain unproven.

Every consumer obtains context through the shared contract. Additional indexing does not block capture or approval. Projection consistency, path visibility, and conflict-policy correction are required work, not deferred operational details. No universal graph editor, campaign-wide manual SPO conversion, or new infrastructure is required for the first increment.

## Alternatives

- Separate graph/search behavior per page: duplicates policy and yields inconsistent answers.
- Immediate Cognee migration: backend choice precedes measured requirements and canonical lifecycle integration.
- Mandatory relationship extraction at ingestion: conflicts with ADR-0012 and prior workflow experience.

## Acceptance

Promote this ADR to accepted when the shared contract and cross-workflow tests are demonstrated. Details and ordered work are in [Shared Campaign Knowledge](../architecture/shared-campaign-knowledge.md).
