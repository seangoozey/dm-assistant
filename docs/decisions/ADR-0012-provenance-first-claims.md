# ADR-0012: Provenance-First Claims with Optional Structure

- Status: accepted
- Date: 2026-08-11
- Supersedes: ADR-0011 requirement for a resolved principal subject

## Context

The migration workflow made subject resolution a prerequisite for promoting an otherwise complete, source-backed assertion. Narrative clauses routinely use pronouns, possessives, unnamed participants, and a viewpoint that does not map cleanly to a new entity. Enforcing a subject-predicate-object representation delayed review and encouraged artificial entities, while the assertion text and provenance already carried the canonical meaning.

## Decision

The complete atomic assertion, its exact source evidence, and its reviewed truth dimensions are sufficient for a canonical claim. Subject, predicate, and object are optional retrieval enrichment. They may be absent at promotion time and added or corrected later through normal reviewed mutations without changing the assertion's provenance.

Subject-aware agency rules still apply whenever a subject is resolved. The system must never infer that missing structure weakens source provenance or authorizes a truth-state change.

## Consequences

- Human review can promote trustworthy assertions without waiting on AI extraction or identity resolution.
- Canonical claims remain searchable through assertion text and evidence when no entity enrichment exists.
- Graph traversal is incomplete until optional enrichment is added.
- Exact duplicate detection remains available for subjectless assertions; semantic conflict analysis can be improved independently.
- The primary migration workflow becomes smaller, while extraction and entity linking can return later as optional tooling.

## Alternatives

- Requiring a principal subject was rejected because it made secondary indexing block canonical capture.
- Treating arbitrary noun phrases as entities was rejected because it polluted identity data.
