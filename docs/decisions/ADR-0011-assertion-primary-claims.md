# ADR-0011: Assertion-Primary Claims

- Status: accepted
- Date: 2026-08-11

## Context

Subject-predicate-object triples improve traversal but cannot reliably preserve every qualifier in narrative campaign facts. Treating the triple as the fact encouraged awkward predicates, artificial entities, and lost context.

## Decision

The complete atomic assertion text is the authoritative semantic content of a claim. Every canonical claim requires one stable principal subject identity. Predicate and object are optional retrieval indexes; omitting or later correcting them does not alter the underlying assertion.

Existing assertions, evidence, provenance, lifecycle fields, and receipts remain unchanged. No secondary entity-reference enumeration is required during initial migration.

## Consequences

- Review can approve a complete claim without forcing a lossy triple.
- Retrieval always indexes assertion text and may additionally use predicate/object indexes.
- Subject resolution remains required and is addressed separately.
- Conflict detection cannot rely exclusively on subject-predicate equality.
