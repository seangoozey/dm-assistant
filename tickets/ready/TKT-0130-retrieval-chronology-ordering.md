---
id: TKT-0130
title: Retrieval orders by campaign chronology and answers when/how-long questions
status: ready
priority: P3
milestone: trustworthy-librarian
depends_on: [TKT-0117]
created: 2026-09-19
updated: 2026-09-19
---

# TKT-0130: Retrieval orders by campaign chronology and answers when/how-long questions

## Context

Split from TKT-0041 (closed 2026-09-19). The campaign clock (TKT-0117) and `campaign_day_ordinal` (ADR-0007) are live, but retrieval does not use them: results are not ordered by in-game chronology, and "how many days since X" questions have no chronology-aware answer path.

## Scope when taken up

- **Retrieval chronology sort**: evidence ranked by `campaign_day_ordinal` within a single calendar (gregorian-ce); unrelated calendars are not silently ordered together (ADR-0007).
- **/ask chronology integration**: "when did X happen" and "how long since X" answers use stored campaign dates and the day-ordinal, not recorded_at wall-clock time.
- UI: answer cards that involve dates show the campaign date alongside the evidence.

## Out of scope

- Cross-calendar conversion; the timeline view (TKT-0042).

## Validation evidence

(to record when built)
