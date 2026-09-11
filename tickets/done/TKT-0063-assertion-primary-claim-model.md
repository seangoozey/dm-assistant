---
id: TKT-0063
title: Make the complete assertion primary claim content
status: completed
priority: P1
milestone: planning-workspace
depends_on: [TKT-0062]
created: 2026-08-11
updated: 2026-08-11
---

# TKT-0063: Make the Complete Assertion Primary Claim Content

## Outcome

Claims preserve a complete atomic assertion as their authoritative semantic content. A resolved principal subject is required, while predicate and object become optional retrieval indexes that do not redefine or truncate the claim.

## Acceptance criteria

- [x] The domain and persistence models identify assertion text as primary claim meaning.
- [x] Every claim requires one stable principal subject identity.
- [x] Predicate and object are optional retrieval indexes.
- [x] Existing claims migrate forward without loss of assertion text, evidence, provenance, or receipts.
- [x] Canonical mutations remain transactional, idempotent, and auditable.
- [x] API contracts, documentation, and tests reflect the new semantics.
- [x] Full validation and local deployment pass.
