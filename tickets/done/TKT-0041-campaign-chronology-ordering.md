---
id: TKT-0041
title: Calendar-aware chronology ordering and current-date config
status: done
priority: P2
milestone: trustworthy-librarian
depends_on: [TKT-0030]
created: 2026-08-04
updated: 2026-08-05
---

# TKT-0041: Calendar-Aware Chronology Ordering and Current-Date Config

## Outcome

The campaign's current in-game date (505CE) is configurable and queryable. Retrieval orders and filters canonical records by campaign chronology within the Gregorian calendar, and "how many days since X" is answerable using the `campaign_day_ordinal` function from ADR-0007.

## Context

ADR-0007 (TKT-0030) built the chronology storage model. This ticket makes it queryable: the current in-game year is campaign configuration, retrieval uses the day-ordinal for same-calendar ordering, and the UI can display the current date. The retrieval fixtures already use symbolic dates; this connects stored integer dates to retrieval ordering.

Read `docs/decisions/ADR-0007-campaign-chronology.md`, `docs/architecture/domain-model.md`, and TKT-0030.

## Scope

- Campaign configuration for the current in-game year (505CE), supplied through config rather than parser constants.
- Retrieval chronology sort and filter using `campaign_day_ordinal` within one calendar.
- `/ask` integration so chronology-aware questions (when, how long ago) use the stored dates.
- A queryable current-date value for the UI.

## Out of scope

- Cross-calendar conversion (ADR-0007 forbids silent cross-calendar ordering).
- The timeline view (TKT-0042).
- Date-precision vocabulary (TKT-0044).

## Acceptance criteria

- [ ] The current in-game year is set through campaign configuration.
- [ ] Retrieval orders canonical records by campaign day-ordinal within one calendar.
- [ ] Unrelated calendars are not silently ordered as if directly comparable.
- [ ] Chronology-aware `/ask` questions use stored campaign dates.
- [ ] Sanitized tests and full repository validation pass.

## Closing (2026-09-19) — delivered parts closed, remainder split

Delivered in full by other tickets:
- Current in-game date as campaign configuration → TKT-0117 (campaign clock: set/query/history via Core, topbar chip, receipted changes)
- Queryable current-date for the UI → TKT-0117
- The campaign_day_ordinal function → ADR-0007 / migration 0009

Remaining (split to follow-up): retrieval chronology ordering and /ask integration — see TKT-0130.
