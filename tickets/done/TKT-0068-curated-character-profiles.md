---
id: TKT-0068
title: Curate PC and NPC profiles before ingestion
status: completed
priority: P1
created: 2026-08-12
updated: 2026-08-12
---

# TKT-0068: Curate PC and NPC Profiles Before Ingestion

## Outcome

PC and NPC documents expose profile identity, background, real-play facts, and plans as distinct content. The four PCs use their intact original biographies as background; derived summaries do not enter the candidate queue.

## Acceptance criteria

- [x] PC/NPC documents visibly distinguish race, sex, background, facts, and plans.
- [x] PC documents additionally display player attribution.
- [x] Original player biographies remain intact and are presented as background.
- [x] `Canon Summary`, `Background / History`, `Relationships`, and `Current Status` are excluded as derived PC/NPC candidates.
- [x] Real-play facts remain sourced from session notes.
- [x] Player plans and DM plans remain separate.
- [x] Missing race or sex is shown honestly rather than inferred.
- [x] Tests and documentation describe the curated boundary.

## Validation evidence

- Repository validator: 285 backend/acceptance tests and 30 React tests passed; strict typing, Windmill build, and 38 retrieval cases passed.
- Read-only live import `a1aaca28-59c4-4182-b315-55d7f27d5634` re-extracted exactly the four PC files under `markdown-parser/1.1`.
- Removed derived candidates remain append-only with `source_removed` status and are excluded from the active migration queue.
- Windmill workspace and Campaign Core were rebuilt and deployed successfully.
