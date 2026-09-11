---
id: TKT-0087
title: Make Brainstorm evidence cards pinnable and searchable at a glance
status: done
priority: P0
milestone: planning-workspace
depends_on: [TKT-0085, TKT-0086]
created: 2026-09-05
updated: 2026-09-05
---

# TKT-0087: Make Brainstorm Evidence Cards Pinnable and Searchable at a Glance

## Outcome

A DM can locate a matching passage inside a long canonical assertion, expand it only when needed, and pin any suggested evidence card during an active Brainstorm.

## Scope

- Render canonical search results as bounded excerpts centered on the first matching query term.
- Highlight every matching query term in the excerpt and expose the complete assertion on explicit expansion.
- Keep citations and dossier controls available without making the whole result permanently tall.
- Support durable, session-scoped pins for exact canonical evidence as well as entity dossiers.
- Show a consistent pin control on every card in `Suggested for latest thought`.

## Acceptance criteria

- [x] Searching `Tsunadis` shows a short excerpt containing highlighted `Tsunadis` near the top of the result.
- [x] Long results have a bounded collapsed height and expand/collapse by clicking their main content.
- [x] Expanded text does not lose the query highlights or citation.
- [x] Every suggested evidence card has a pin control, including claims without an owning entity ID.
- [x] Exact evidence pins survive refresh and contribute their assertion text to later continuity retrieval.
- [x] Relevant service, PostgreSQL, React, and repository validation pass.

## Migration and rollback

Use an additive exact-evidence pin table keyed by Brainstorm session and canonical retrieval record. Rolling back the application leaves those non-canonical context rows unused; no campaign claims or sources are modified.

## Validation evidence

Repository gate passed: 316 backend tests, 69 React tests, strict types, raw-app build, and 38 retrieval cases. Seven isolated PostgreSQL integration tests passed, including entity-free evidence pin persistence, idempotency, and removal. Deployed successfully with test-stack.ps1 up. Browser visual confirmation remains a user-facing follow-up.
