---
id: TKT-0052
title: Add lossless segment-accounted extraction review
status: done
priority: P1
milestone: planning-workspace
depends_on: [TKT-0051]
created: 2026-08-09
updated: 2026-08-09
---

# TKT-0052: Add Lossless Segment-Accounted Extraction Review

## Outcome

AI extraction targets lossless atomic claims, accounts for every deterministic source clause, rejects incomplete coverage contracts, and shows non-extracted dispositions to the reviewer.

## Acceptance criteria

- [x] Campaign Core deterministically segments candidate source text with stable IDs and offsets.
- [x] Every extracted claim cites one or more valid source segment IDs.
- [x] Every segment is exactly accounted for as extracted, context-only, duplicate, or non-assertive.
- [x] Missing, duplicate, unknown, or inconsistent coverage fails extraction without partial storage.
- [x] Independent facts may retain a non-focal subject while reviewed truth dimensions remain source-controlled.
- [x] Extraction runs persist immutable segments, coverage, and claim-to-segment links.
- [x] Step 3 shows coverage totals and every non-extracted segment disposition.
- [x] Prompt and extractor version document the lossless atomic-coverage contract.
- [x] Tests and full repository validation pass.

## Implementation

- Added deterministic sentence/clause segmentation with stable IDs and exact offsets.
- Versioned the extraction contract as `extraction/2` and prompted for lossless atomic claims plus reciprocal segment coverage.
- Added fail-closed validation for missing, duplicate, unknown, or inconsistent coverage references.
- Preserved independent non-focal subjects while continuing to enforce source-owned state, authority, and visibility.
- Persisted immutable segment, disposition, and claim-link data per extraction run.
- Added a Step 3 coverage panel with totals and every non-extracted source segment.

## Validation

- 49 focused extraction, persistence-contract, and migration tests pass.
- Full repository validation passes: 245 Python tests with 26 integration skips, 25 React tests, Ruff, strict mypy and TypeScript, Windmill build/source policy, Compose policy, and the 38-case retrieval corpus.
- Migration `0013_extraction_segment_coverage` is applied to the local development database.
- The updated Campaign Core image and Windmill raw app are deployed to `dm-assistant-dev`.
