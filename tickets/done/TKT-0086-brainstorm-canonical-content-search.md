---
id: TKT-0086
title: Search canonical content within Brainstorm
status: done
priority: P0
milestone: planning-workspace
depends_on: [TKT-0085]
created: 2026-09-05
updated: 2026-09-05
---

# TKT-0086: Search Canonical Content Within Brainstorm

## Outcome

A DM can answer a continuity question from canonical claim content, open the owning record, and pin it without leaving an active Brainstorm.

## Scope

- Run grounded campaign retrieval from the Brainstorm search field after a short debounce.
- Keep canonical-name and alias matches while adding ranked claim-content matches with assertion and citation text.
- Show dossier and pin controls on every content result that resolves to a canonical entity.
- Make pin affordances visible and consistent on name, content, and suggested-canon cards.
- Preserve the active thought draft and current Brainstorm when searching, opening, closing, pinning, or unpinning.

## Acceptance criteria

- [x] The Ishi'go'dan / Ragga'na'ken query surfaces the claim that he was sent to Mythis Minor to destroy Tsunadis.
- [x] Content results show useful assertion text and provenance rather than only a bare record name.
- [x] A resolvable content result has visible open-dossier and pin controls.
- [x] Search failures are visible without disrupting thought capture.
- [x] React, retrieval, and repository validation pass.

## Migration and rollback

No schema migration is required. Rolling back the UI restores name-only search; no campaign data is changed by searching.

## Completion evidence

- Repository validation passed: 314 backend tests, 68 React tests, strict TypeScript, Windmill raw-app build, and 38 retrieval corpus cases.
- Live Brainstorm search for the Ishi'go'dan / Ragga'na'ken question returned the Romulus assertion naming Mythis Minor and the castle at Tsunadis with its canonical citation.
- The live result exposed both `Open Romulus` and `Pin Romulus`; verification did not alter the active thought or pinned context.
