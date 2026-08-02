---
id: TKT-0011
title: Author grounded retrieval acceptance corpus
status: done
priority: P1
milestone: trustworthy-librarian
depends_on: []
created: 2026-08-01
updated: 2026-08-01
---

# TKT-0011: Author Grounded Retrieval Acceptance Corpus

## Outcome

Create the documented 30–50-question sanitized corpus that specifies how campaign retrieval must cite authoritative evidence, respect visibility and truth state, expose conflicts, and decline unsupported answers.

## Context

`docs/testing/acceptance-strategy.md` requires a representative retrieval suite, but the repository currently contains nine workflow interaction fixtures rather than a focused retrieval corpus. Corpus authoring is independent of the not-yet-built Campaign Core and fixture harness; executable integration is tracked separately. Read the product invariants, truth-state authority specification, importer specification, and acceptance strategy.

## Scope

- Create 30–50 sanitized questions covering direct facts, aliases, relationships, chronology, contradictions, canon-versus-planning leakage, unknown answers, recent updates, and character-specific visibility.
- Record the minimum authoritative inputs, expected answer facts, required citations, forbidden claims, and expected unknown/conflict behavior for every question.
- Include cases where preparation, brainstorm material, stale links, and derived artifacts must not override campaign truth.
- Include temporal cases distinguishing expected and observed dates.
- Document sanitization and provenance without copying unnecessary private campaign content.

## Out of scope

- Optimizing embeddings or adding Cognee.
- Selecting a production model based solely on this corpus.
- Importing live campaign data into a canonical production database.
- Executing the corpus through Campaign Core or a retrieval API.
- Broad model-quality evaluation unrelated to grounded retrieval.

## Acceptance criteria

- [x] The suite contains between 30 and 50 structurally valid retrieval cases.
- [x] Every case specifies authoritative inputs, expected facts, required citations, forbidden claims, visibility, and expected answer mode.
- [x] The suite covers every category named in the acceptance strategy.
- [x] At least five cases require an explicit unknown or insufficient-evidence answer.
- [x] At least five cases test non-canon leakage from preparation, brainstorm, quarantine, or derived artifacts.
- [x] At least three cases test conflicts or possible retcons without automatic overwrite.
- [x] At least three cases test expected-versus-observed chronology.
- [x] A standalone structural validation reports category totals and threshold coverage.
- [x] No live Starfall access is required and no unnecessary private source text is committed.

## Validation

`python tests/validate_retrieval_cases.py` passed with 38 cases: 3 aliases, 4 character-visibility, 5 chronology, 4 contradiction, 5 direct-fact, 6 non-canon-leakage, 2 recent-update, 4 relationship, and 5 unknown cases. Answer modes comprise 17 answers, 2 conflicts, 15 insufficient-evidence responses, 2 possible-retcon responses, and 2 restricted responses.

`python -m py_compile tests/validate_retrieval_cases.py` and `git diff --check` passed. A path scan confirmed the corpus contains no live-source or snapshot path. Manual sanitization review confirmed that Starfall-derived facts are limited to facts already present in `tests/fixtures/interaction_cases.yaml`; all other examples are labeled synthetic.

## Implementation notes

The corpus may reuse the minimum facts already present in sanitized interaction fixtures. Synthetic records must be clearly labeled and must never be represented as campaign canon.

The standalone validator uses PyYAML because the repository's existing behavioral fixtures are YAML. TKT-0010 must pin and integrate that test dependency when it establishes the standard harness.

## Follow-ups

- TKT-0012 executes the corpus through the typed harness and initial retrieval boundary.
- Establish a separate retrieval-quality benchmark if deterministic acceptance coverage proves insufficient.
