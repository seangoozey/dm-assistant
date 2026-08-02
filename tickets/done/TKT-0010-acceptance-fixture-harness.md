---
id: TKT-0010
title: Build executable acceptance fixture harness
status: done
priority: P1
milestone: trustworthy-librarian
depends_on: [TKT-0005]
created: 2026-08-01
updated: 2026-08-01
---

# TKT-0010: Build Executable Acceptance Fixture Harness

## Outcome

Turn the structured interaction fixtures into an executable, documented test layer that validates fixture quality and exercises deterministic Campaign Core behavior.

## Context

`tests/fixtures/interaction_cases.yaml` expresses the initial authority, approval, creative-boundary, PC-agency, real-play, and audio-revision examples, but no test runner currently executes them. Read `docs/product/truth-state-authority.md`, `docs/architecture/campaign-core-schema.md`, `docs/testing/acceptance-strategy.md`, TKT-0002, and TKT-0005.

## Scope

- Define a typed schema for interaction fixtures.
- Validate required fields, supported workflow and enforcement values, unique IDs, and non-empty expected and forbidden behavior.
- Parameterize deterministic Core tests from applicable fixture cases.
- Clearly distinguish rules enforced by Core from model-quality or output-validation expectations.
- Integrate fixture validation with the repository's standard test command and continuous validation workflow.
- Document how future fixtures are added and executed.

## Out of scope

- Model-provider benchmarking.
- Treating prompt evaluations as substitutes for deterministic domain tests.
- Building the 30–50-question retrieval corpus; that is TKT-0011.
- Implementing every workflow end to end.

## Acceptance criteria

- [x] Every interaction fixture is parsed through a typed schema during tests.
- [x] Missing required fields, duplicate IDs, empty behavior lists, and unknown enum values fail with actionable messages.
- [x] Each fixture marked `core` runs at least one deterministic domain assertion, or explicitly records a tracked implementation dependency.
- [x] Mixed enforcement cases identify which assertions are deterministic and which require later model/output evaluation.
- [x] At least the approval-scope, proposal-version, PC-agency, and observed-versus-prepared cases execute through the domain layer.
- [x] The documented standard test command runs the fixture suite repeatedly without order-dependent results.
- [x] Tests contain no unsanitized private campaign material.

## Validation

`python tests/validate_repository.py` is the documented local and continuous-validation entry point. It passed with:

- Ruff checks over Campaign Core and repository validators.
- Strict mypy validation of 19 Campaign Core source files.
- 22 passing Campaign Core tests.
- Typed parsing of all 9 sanitized interaction cases.
- 6 registered deterministic cases/assertions, including approval scope, proposal version, PC agency, observed-versus-prepared authority, creative-artifact boundaries, and explicit candidate revision.
- 1 Core-owned case explicitly dependent on the existing TKT-0015 implementation ticket.
- 4 cases with explicit deferred model/output evaluation ownership.
- 5 intentional invalid-fixture tests covering a missing field, duplicate ID, empty behavior list, unknown workflow, and unknown enforcement owner; every case produced the expected actionable Pydantic error.
- Order-independent forward and reverse assertion execution.
- Passing Compose policy and 38-case retrieval-corpus structural validation.
- `git diff --check` passed.

The fixture remains the previously reviewed minimal sanitized corpus; no live Starfall data, raw chat dump, backup, or production record was added.

## Implementation

- Added strict Pydantic schema version 2 for fixture metadata, workflows, enforcement ownership, deterministic assertion IDs, deferred evaluations, and implementation dependencies.
- Added pure domain policies for exact approval scope, approval-version validity, observed-versus-prepared resolution, bounded creative artifacts, and explicit non-canon candidate correction; retained the existing PC-agency policy.
- Added a registry-based, order-independent fixture runner and tests that require every assertion enum to have an implementation.
- Added `tests/validate_repository.py` and documented fixture extension and execution in `docs/testing/fixture-harness.md`.

## Implementation notes

Use the test tooling established by TKT-0005 rather than introducing a parallel application environment.

## Follow-ups

- Add model and output-validation evaluations only under separately reviewed tickets.
- TKT-0012 executes the grounded retrieval corpus through Campaign Core.
- TKT-0015 replaces its fixture dependency with database/API assertions for atomic change-set application.
