---
id: TKT-0062
title: Add corrective extraction retry and failure analysis storage
status: done
priority: P1
milestone: planning-workspace
depends_on: [TKT-0061, TKT-0056]
created: 2026-08-10
updated: 2026-08-10
---

# TKT-0062: Add Corrective Extraction Retry and Failure Analysis Storage

## Outcome

After an invalid extraction response, the bounded second attempt receives actionable validation feedback. Failed attempts are retained as derived diagnostic evidence with exact configuration provenance, without entering canonical campaign truth.

## Acceptance criteria

- [x] Attempt two identifies the prior validation failure and requests a complete corrected response.
- [x] Each failed attempt retains its attempt number, error, and raw provider response when available.
- [x] Exhausted candidate failures are durably stored with candidate, extractor, model profile, model slug, and prompt version.
- [x] Failure records are explicitly derived diagnostics and cannot be promoted as campaign truth.
- [x] Successful retry stores no canonical data from its failed first attempt.
- [x] Tests cover corrective retry content, failure capture, persistence, and provenance.
- [x] Full validation and local deployment pass.

## Validation evidence

- Repository validation passed: 265 Python tests, 26 skipped; 28 React tests; lint, mypy, policies, raw-app build, and retrieval corpus.
- Focused extraction tests passed with corrective retry message and two-attempt raw failure capture.
- Local stack rebuilt successfully; Campaign Core and Windmill health checks passed.
- Migration `0015_extraction_failure_analysis` and table `candidate_extraction_failures` were verified in the local Campaign database.

## Follow-up work

- Add a DM-only failure-analysis view when enough stored samples exist to support useful provider comparisons.
