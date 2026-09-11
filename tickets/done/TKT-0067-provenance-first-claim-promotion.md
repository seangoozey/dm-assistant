---
id: TKT-0067
title: Make provenance-first assertions independently promotable
status: completed
priority: P1
milestone: planning-workspace
depends_on: [TKT-0063, TKT-0065, TKT-0066]
created: 2026-08-11
updated: 2026-08-11
---

# TKT-0067: Make Provenance-First Assertions Independently Promotable

## Outcome

A reviewer can promote a complete, source-backed assertion with its truth dimensions without first resolving a subject, predicate, or object. Structured claim fields remain optional enrichment that can be added later without changing the assertion or its provenance.

## Acceptance criteria

- [x] Canonical claims may omit subject, predicate, and object while retaining assertion text, source evidence, truth state, authority, visibility, and an auditable receipt.
- [x] The migration workflow offers a direct proposal path from a reviewed candidate and does not require AI extraction or entity creation.
- [x] Existing structured claims and subject-aware agency safeguards continue to work.
- [x] Retrieval includes subjectless canonical assertions and continues to use entity enrichment when present.
- [x] Conflict checks protect exact duplicate assertions without treating missing structure as an error.
- [x] API contracts, schema documentation, ADRs, and tests describe structured fields as optional enrichment.
- [x] Relevant backend and React validation pass, with evidence recorded here before completion.

## Validation evidence

- Repository deterministic validation: 284 passed, 26 integration tests skipped because the validator does not configure a disposable PostgreSQL URL.
- React validation: 29 tests passed, strict TypeScript typecheck passed, and the Windmill raw-app bundle built successfully.
- Retrieval acceptance corpus: 38 cases passed.
- Local test stack rebuilt successfully; Campaign Core and Windmill reported healthy.
- Windmill workspace `dm-assistant-dev` deployed successfully.
- PostgreSQL verified `0019_optional_claim_structure` applied and `claims.subject_entity_id` reports `is_nullable = YES`.

## Follow-up work

- Reintroduce subject/predicate/object enrichment only as a separately testable, optional workflow.
