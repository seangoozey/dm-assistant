# Grounded Retrieval Harness

`tests/fixtures/retrieval_cases.yaml` is the executable contract for initial grounded retrieval. Its 38 sanitized cases cover direct facts, aliases, relationships, chronology, contradictions, non-canon leakage, unknown answers, recent updates, and character-specific visibility.

## Execution boundary

Each test case is parsed through strict Pydantic fixture models, converted to typed retrieval records, and loaded into a new in-memory repository. `RetrievalService` then invokes the same deterministic `RetrievalPolicy` used by the HTTP boundary. No case shares state with another, and reversing the fixture input order must produce an identical result.

The initial boundary is lexical and deliberately structured. It returns an answer mode, typed evidence roles, exact citations, and reason codes rather than model-generated prose. Authoritative accepted records may support an answer. Non-canonical candidates and context records can be returned only as context; they cannot support a fact. Visibility filtering happens before evaluation or citation selection.

Campaign Core also provides `POST /retrieval/query`. Its default PostgreSQL adapter reads accepted claims and relationships plus non-canonical import candidates. The operation is read-only and does not promote candidates or mutate campaign truth.

## Assertions

The suite checks exact answer modes and citation sets. Required facts are matched against the returned structured evidence and citations by normalized semantic tokens, avoiding exact prose comparisons. Forbidden assertions, hidden records, hidden citations, duplicate citations, and non-canonical support roles fail deterministically.

Conflict and possible-retcon modes require both sides of the visible comparison. Insufficient-evidence and restricted modes must remain explicit rather than filling gaps. Reversing repository order verifies deterministic evidence and citation ordering.

Malformed fixture tests intentionally reject missing questions, duplicate record identifiers, unknown categories, and empty expected facts.

## Running and extending

From the repository root with the Campaign Core development environment active:

```powershell
python tests\validate_repository.py
```

For a focused run:

```powershell
cd campaign-core
.\.venv\Scripts\python -m pytest tests\test_retrieval_acceptance.py -q
```

When adding a case, give every record a stable identifier, label source kind, authority, state, visibility, and exact citation, and state all required and forbidden outcomes. Keep the corpus sanitized and set `source_policy.live_source_accessed` to `false`; acceptance tests must not depend on the live Starfall collection.
