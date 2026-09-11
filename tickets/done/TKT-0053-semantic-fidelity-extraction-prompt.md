---
id: TKT-0053
title: Tighten extraction semantic fidelity and subject selection
status: done
priority: P1
milestone: planning-workspace
depends_on: [TKT-0052]
created: 2026-08-09
updated: 2026-08-09
---

# TKT-0053: Tighten Extraction Semantic Fidelity and Subject Selection

## Outcome

The extraction prompt preserves explicit meaning without upgrading implications, retains independent grammatical subjects, and keeps named qualifiers and predicate/object structure intact.

## Acceptance criteria

- [x] The prompt explicitly prohibits inferred death, orphanhood, witnessing, causation, intention, and certainty.
- [x] Independent named subjects remain subjects instead of being rewritten through the focal entity.
- [x] Ages, durations, destinations, route markers, titles, leaders, locations, motivations, and sequence qualifiers must be retained.
- [x] Predicates do not repeat an entity already supplied as the object.
- [x] Sanitized regression examples cover the Ruhrogue failure patterns.
- [x] Extractor version advances and validation passes.

## Implementation

- Added explicit negative examples for unsupported orphanhood and witnessing inferences.
- Required independent grammatical subjects to remain subjects when inverse rewriting changes meaning.
- Required retrieval-significant qualifiers and secondary participants to survive extraction.
- Clarified predicate/object separation and added a final semantic-fidelity comparison pass.
- Advanced the extraction contract to `extraction/3`.

## Validation

- 38 focused extraction tests pass.
- Full validation passes: 248 Python tests with 26 integration skips, 25 React tests, Ruff, strict mypy and TypeScript, Windmill build/source policy, Compose policy, and the retrieval corpus.
- Campaign Core was rebuilt and deployed successfully.
