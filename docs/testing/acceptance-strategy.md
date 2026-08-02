# Acceptance Strategy

The most important tests are scenario fixtures derived from Sean's real interactions.

## Each case records

- user input and active workflow;
- relevant existing records;
- expected entities and claims;
- allowed automatic changes;
- required questions or warnings;
- forbidden inferences;
- expected sources and citations;
- expected proposal, receipt, or comparison;
- idempotency behavior.

## Initial interaction cases

- Inspecting Jace during a pending promotion must not promote unrelated claims.
- Invented Sorin and Roccid material must be rejected under the default records-clerk role.
- Explicit request for a Sorin read-aloud may embellish presentation but not lore.
- Direct Sorin lore update inside a brainstorm updates only Sorin and returns to the brainstorm.
- “Promote all and close” applies the exact reviewed version.
- PC “ultimate tasks” become campaign-shaping directions, not guaranteed player actions.
- A missing noble name produces an unknown answer rather than invention.
- Real-play notes supersede prepared outcomes and issue a receipt.
- A later statement in audio withdraws an earlier candidate claim.
- An unresolved self-question remains unresolved.

## Retrieval suite

Maintain at least 30–50 questions covering direct facts, aliases, relationships, chronology, contradictions, non-canon leakage, unknown answers, recent updates, and character-specific knowledge.

The sanitized corpus is maintained in `tests/fixtures/retrieval_cases.yaml`. The repository test command validates its structure and executes every case through the typed Campaign Core retrieval boundary. The isolated-store harness, assertion rules, and extension procedure are documented in [retrieval-harness.md](retrieval-harness.md).

## Test levels

- Pure domain unit tests for state transitions and authority.
- Database transaction tests for all-or-nothing promotion and idempotency.
- Importer fixture tests.
- API contract tests.
- Windmill job integration tests.
- Full vertical-slice acceptance tests through the React interface where valuable.

Model evaluations supplement deterministic tests; they never replace them.

## Standard deterministic validation

After installing `campaign-core/requirements-dev.txt` from the `campaign-core` directory and activating that environment, run this from the repository root:

```bash
python tests/validate_repository.py
```

This is the shared local and continuous-validation entry point. Interaction fixture ownership, schema rules, and extension steps are documented in [fixture-harness.md](fixture-harness.md).

The synthetic Markdown import corpus, path-safety assertions, and reconciliation sequence are documented in [importer-fixtures.md](importer-fixtures.md).

The grounded retrieval corpus, deterministic policy boundary, and non-brittle evidence assertions are documented in [retrieval-harness.md](retrieval-harness.md).
