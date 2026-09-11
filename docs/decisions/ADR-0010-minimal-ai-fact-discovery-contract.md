# ADR-0010: Minimal AI Fact-Discovery Contract

- Status: accepted
- Date: 2026-08-10

## Context

The extraction provider was asked to understand prose while also copying exact excerpts, assigning truth dimensions, and maintaining reciprocal coverage indexes. Representative models understood the facts but frequently failed this bookkeeping contract. Those failures obscured the distinction between semantic extraction and deterministic audit mechanics.

## Decision

The `extraction/8` provider contract contains only atomic assertion text, cited source-segment IDs, and proposed subject-predicate-object structure. Campaign Core owns exact evidence reconstruction, state, authority, visibility, confidence, coverage dispositions, and reciprocal claim indexes.

The provider cannot override source-owned truth dimensions. Exact evidence is sliced from immutable source text using deterministic segment offsets. Uncited segments remain visibly `context_only`; they are not silently represented as extracted facts.

## Consequences

- The model focuses on semantic fact discovery instead of audit bookkeeping.
- Exact evidence and coverage cannot fail because of model punctuation or index mistakes.
- Human review still corrects or excludes proposed semantic structure before promotion.
- A future independent normalization stage may replace the provider's proposed subject-predicate-object values without changing fact discovery or provenance.
