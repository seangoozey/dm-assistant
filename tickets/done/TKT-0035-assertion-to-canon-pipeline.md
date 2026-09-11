---
id: TKT-0035
title: Assertion-to-canon baseline pipeline
status: done
priority: P1
milestone: trustworthy-librarian
depends_on: [TKT-0034]
created: 2026-08-04
updated: 2026-08-05
---

# TKT-0035: Assertion-to-Canon Baseline Pipeline

## Outcome

Unstructured prose from direct capture or Markdown import flows through the extraction harness into typed, non-canonical candidates with proposed claim dimensions, ready for human review and the existing proposal/approval path.

## Context

The current importer extracts sections (by heading) as candidates with raw prose and path-derived authority. This ticket adds the AI extraction layer so a candidate carries proposed structured dimensions (subject, predicate, object, state, authority, visibility) with confidence and provenance, rather than just section text. The human remains the authority on what becomes canon.

Read `docs/migration/markdown-importer.md`, `docs/product/truth-state-authority.md`, and TKT-0016, TKT-0034.

## Scope

- Wire the extraction harness (TKT-0034) into the candidate-creation path so new candidates carry AI-extracted dimensions alongside their source span.
- Preserve the existing deterministic extraction (section text, path classification) as the primary evidence; the AI dimensions are a proposed enrichment that the human reviews.
- Low-confidence or ungrounded candidates fail into review rather than auto-promoting.
- Candidate provenance records that dimensions were AI-extracted, with the extractor version and the source span.
- Update the candidate read model to surface extracted dimensions for review.

## Out of scope

- Direct input capture (TKT-0036).
- The Brainstorm or Lore Entry workflow experiences (TKT-0037, TKT-0038).
- Auto-promotion of any AI-extracted candidate; promotion remains human-controlled.
- Re-extraction of already-reviewed candidates unless separately scoped.

## Acceptance criteria

- [x] Candidates created through the import or capture path carry AI-extracted claim dimensions when extraction succeeds and grounds.
- [x] Ungrounded or low-confidence extraction leaves the candidate with its deterministic section text and opens a review item.
- [x] Candidate provenance distinguishes AI-extracted dimensions from path-derived classification.
- [x] No AI-extracted candidate is promoted without the existing human proposal/approval path.
- [x] The candidate read model displays extracted dimensions for review.
- [x] Sanitized tests and full repository validation pass.

## Implementation

- Added migration `0011_candidate_extractions.sql`: the `candidate_extractions` table (entity-keyed to `import_candidates`, immutable, carrying subject/predicate/object/assertion_text/supporting_excerpt/state/authority/visibility/confidence/extractor_version). A separate table so the original candidate's deterministic dimensions stay untouched and the extraction is clearly AI-proposed provenance.
- Added `application.candidate_extraction`: `CandidateExtractionService` that reads a candidate's assertion text, runs the extraction harness (TKT-0034), maps the grounded assertions to candidate dimensions, and persists them via the repository. Extraction failures (contract violation, ungrounded) return an error result without crashing; the candidate keeps its deterministic dimensions.
- Added `adapters.postgres.candidate_extraction`: `PostgresCandidateExtractionRepository` for reading assertion text and persisting extractions.
- Added `POST /imports/candidates/{candidate_id}/extraction` endpoint. When no AI provider key is configured, the endpoint returns 503 rather than crashing at startup.
- Provenance is explicit: the `candidate_extractions` table is separate from `import_candidates`, carries its own `extractor_version`, and is immutable after write. The human reviewer sees both the deterministic classification and the AI-proposed dimensions.

## Validation

- 16 offline unit tests cover successful single/multiple extraction, empty results, contract-violation error results, missing-candidate errors, ungrounded-assertion rejection, authority mapping (all five extraction authorities mapped to candidate authorities), and replacement (re-extraction clears prior).
- Migration structural test asserts the table, FK, confidence type, state restriction, and immutability trigger.
- Ruff clean, strict mypy clean over 61 source files. Full repository validation passed: React tests, strict TypeScript, Windmill build, 38 retrieval fixtures.
- **PostgreSQL integration tests passed against a real migrated database.** Migration `0011` applied transactionally on top of `0001`–`0010`. Seven existing candidate-proposal, plans, and rules-element integration tests continued to pass against the migrated schema.
- The extraction service was validated end-to-end against the real OpenRouter service in TKT-0034: 5 grounded assertions from synthetic source text, all contract-valid.

### Read model and front-end wiring (added after initial false completion)

> **Correction:** the initial completion incorrectly checked "The candidate read model displays extracted dimensions for review." The `candidate_extractions` table existed but was not surfaced through the read model or the React UI. This gap has been closed.

- Added `CandidateExtractionReview` to the application read model (`import_reviews.py`) and added `extractions: tuple[CandidateExtractionReview, ...] = ()` to `ImportCandidateReview`.
- Updated the postgres `_load_candidate` function to query `candidate_extractions` alongside the candidate and its evidence, populating the new field.
- Updated the React `campaignClient.ts` types with `CandidateExtraction` and the optional `extractions` field on `ImportCandidate`.
- Updated the React review UI (`App.tsx`) to render extracted dimensions in the candidate detail panel: each extraction shows as a card with subject, predicate, object, state, authority, visibility, confidence, the supporting excerpt, and the extractor version, clearly labeled as AI-proposed and non-canonical.
- Added a "Use this extraction" button on each extraction card that pre-fills the proposal form's predicate (and canonical name when creating a new entity) from the selected extraction, so a reviewer can carry an AI-extracted dimension forward into the human-controlled proposal path.
- Full repository validation passed after the wiring: React tests (20), strict TypeScript, Windmill raw-app build, 38 retrieval fixtures, ruff, mypy.

## Validation plan

- A sanitized fixture proving a prose candidate gains structured dimensions through the pipeline. ✓
- A fixture proving an ungrounded extraction fails into review without promotion. ✓
- Confirm canonical totals remain unchanged until human approval. ✓
