---
id: TKT-0048
title: Focal-entity grounded extraction
status: done
priority: P1
milestone: planning-workspace
depends_on: [TKT-0045, TKT-0047]
created: 2026-08-09
updated: 2026-08-09
---

# TKT-0048: Focal-Entity Grounded Extraction

## Outcome

Entity-centered source documents produce concise, retrieval-useful claims about their canonical focal entity. AI wording cannot silently replace the candidate's reviewed truth dimensions, and reviewers can see each claim's summary and exact evidence.

## Context

Extraction of `pcs/ruhrogue.md` alternated between Ruhrogue and grammatical sentence subjects such as Ruh and Ruhrogue's parents. It also produced compound predicates and inconsistent object values. The source candidate already owns state, authority, and visibility, but provider output attempted to reclassify those dimensions.

## Scope

- Identify the focal entity and record type from entity-centered document context.
- Strengthen prompt guidance around focal subjects, concise predicates, stable entity objects, and useful granularity.
- Normalize provider output to the focal entity for PC, NPC, and location documents.
- Normalize state, authority, and visibility to the reviewed candidate dimensions before persistence.
- Show assertion summaries, supporting excerpts, and confidence during extraction review.
- Explain that truth dimensions are inherited from reviewed source classification.
- Add sanitized regression coverage.

## Acceptance criteria

- [x] PC, NPC, and location extractions retain the document focal entity as claim subject.
- [x] Candidate truth dimensions override conflicting provider classifications.
- [x] Prompt discourages grammatical-subject drift, compound predicates, and non-entity objects.
- [x] Extraction review exposes assertion text, exact supporting evidence, and confidence.
- [x] Sanitized tests and full repository validation pass.

## Implementation

- Added explicit focal subject, record type, and reviewed truth dimensions to extraction context.
- Derived PC, NPC, and location context from normalized source paths and document headings.
- Strengthened the extraction prompt with focal-subject, participant/object, granularity, and concise-predicate guidance.
- Added deterministic post-provider normalization so model drift cannot change the focal subject or reviewed truth dimensions.
- Added per-claim assertion summaries, exact supporting excerpts, and confidence to extraction review.
- Added a sanitized regression proving conflicting provider subject/state/authority/visibility are normalized.

## Validation

- Ruff and strict mypy pass over 63 source files.
- 237 Python tests pass with 26 integration skips.
- 23 React tests and strict TypeScript pass.
- Windmill raw-app build and 38-case retrieval corpus pass.
