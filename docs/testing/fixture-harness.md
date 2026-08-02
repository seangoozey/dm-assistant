# Interaction Fixture Harness

`tests/fixtures/interaction_cases.yaml` is a sanitized, versioned acceptance corpus. Campaign Core tests parse every case through the strict Pydantic contract in `dm_assistant_core.acceptance.schema`; unknown fields and enum values are rejected rather than ignored.

## Execution ownership

Each case declares:

- `enforcement`: whether the rule belongs to Core, model/output evaluation, or both;
- `deterministic_assertions`: registered Core assertions executed by pytest;
- `deferred_evaluations`: model-quality or output-validation work that deterministic tests cannot prove;
- `implementation_dependency`: an existing ticket when a Core-owned behavior is intentionally not implemented yet.

A Core-owned case must name at least one executable assertion or a real ticket dependency. A non-Core case cannot claim a deterministic Core assertion. Mixed enforcement must explicitly list the corresponding deferred evaluation.

## Adding a case

1. Add only the minimum sanitized text needed to express the behavior. Never copy raw private chats, campaign backups, or production records.
2. Supply every required behavior field and choose a supported workflow and enforcement owner.
3. For implemented Core behavior, add a narrowly named `DeterministicAssertion` value and register its runner in `campaign-core/tests/support/interaction_harness.py`.
4. If the Core portion is not implemented, create or select a concrete ticket and record its ID as `implementation_dependency`.
5. Put model or prose judgment under `deferred_evaluations`; do not imitate it with keyword matching and call it a deterministic test.
6. Run the standard validation command from the repository root with the Campaign Core development environment active:

```bash
python tests/validate_repository.py
```

The command runs linting, strict type checking, all Campaign Core and fixture tests, Compose policy validation, and retrieval-corpus structural validation. It is the entry point for both local repeatable checks and future CI runners.

## Failure behavior

Schema errors include the failing case path and reason. Tests intentionally verify actionable failures for missing fields, duplicate IDs, empty behavior lists, and unknown workflow or enforcement values. Assertion execution is registry-based and order-independent.

