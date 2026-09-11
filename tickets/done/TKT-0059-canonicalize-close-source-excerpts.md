---
id: TKT-0059
title: Canonicalize close AI source excerpts
status: done
priority: P1
milestone: planning-workspace
depends_on: [TKT-0058]
created: 2026-08-10
updated: 2026-08-10
---

# TKT-0059: Canonicalize Close AI Source Excerpts

## Outcome

Minor AI paraphrases of supporting evidence are replaced with exact deterministic source text when similarity is safely high; invented or weakly matching evidence remains rejected.

## Acceptance criteria

- [x] Existing exact excerpts remain unchanged.
- [x] Close matches search bounded windows of at most three consecutive source segments.
- [x] Alignment requires both strong token overlap and sequence similarity.
- [x] Accepted matches store exact source text before grounding and citation reconciliation.
- [x] Weak matches remain grounding failures.
- [x] Extractor version is `extraction/5`; tests and validation pass.

## Validation evidence

- Focused grounding and extraction tests: 41 passed, including close paraphrase canonicalization and unrelated/short evidence rejection.
- Repository validation: 254 Python tests passed, 26 skipped; 27 React tests passed; lint, types, policies, build, and retrieval corpus passed.
- Local Campaign Core image rebuilt and both service health checks passed.
