---
id: TKT-0117
title: Campaign calendar management — current in-world date as a first-class DM control
status: done
priority: P1
milestone: shared-campaign-knowledge
depends_on: [TKT-0041]
created: 2026-09-14
updated: 2026-09-14
---

# TKT-0117: Campaign calendar management — current in-world date as a first-class DM control

## Context (Sean, 2026-09-14)

Discussing TKT-0097 prerequisites: "there currently is no way to add in-world timestamps to anything, nor is there a way to manage the current in-world date so that new entries can be stamped with ease." The calendar machinery exists (TKT-0041 delivered the CampaignDate domain and a Postgres campaign clock; session capture collects an in-game date per note and uses the clock as its default), but the clock is not a managed, visible thing — the DM cannot see or set "today in the campaign," so stamping anything requires remembering the date by hand.

## Scope

- **Current in-world date, visible and editable**: surface the campaign clock in the app (a header chip or a Tools panel block — placement at pickup, follow UI conventions), showing the current campaign date; DM can set or advance it. Advancing is the common act (session end → move the clock); keep it one click plus optional reason. The clock change is recorded (campaign clock history already exists in Core — expose recent changes read-only).
- **Stamp-on-create defaults everywhere**: every point that creates dated content prefills from the clock — session capture (already does for its default; verify), claim correction/replacement (new claim's effective date defaults to current), entity-profile state changes, encounter resume metadata. The rule: a new record should never ask the DM for a date the clock already knows.
- **Core surface**: an API for read/write of the current date if the campaign clock adapter lacks one (it exists in Postgres — verify exposure through Campaign Core's API surface).
- Follows TKT-0044/0118's precision vocabulary when approximate dates land (clock itself stays exact).

## Acceptance

- Current campaign date visible at all times; set/advance works and is reflected in the next capture's default without reload gymnastics.
- New claim creation surfaces (capture, correction) prefill the in-game date from the clock and keep it reviewable.
- Tests: clock read/write through Core; UI prefill behavior; no canonical writes beyond the clock's own audited store.

## Out of scope

- Retroactive stamping of existing claims (TKT-0118); calendar systems other than the existing one; approximate dates (TKT-0118 absorbs TKT-0044).

## Delivery (2026-09-14, deployed)

- **Core**: `PUT /campaign/current-date` (DM-gated, optional reason) + `GET /campaign/current-date/history`; migration 0057 `campaign_clock_changes` — every clock change (DM set, session-capture advance) is appended with reason and timestamp. The write route carries the `campaign-clock` tag, not `campaign`: the boundary test enforcing "campaign-tagged mutations only through change-set apply" caught this — the clock is runtime state, and the tag now says so.
- **UI**: a **Today** chip in the topbar (between nav and DM badge) showing the current in-world date on load (505-11-27 CE live, from the one dated capture); clicking opens the management panel — y/m/d fields, **+1 day / +7 days** quick advance, optional reason, recent changes list, toast on save. Session capture's default already flows from this clock; captures continue to advance it automatically.
- **Bug found and fixed during verification**: an inserted switch-case fell through, making `get_current_campaign_date` issue a bodyless PUT (Core 422, `Error: [object Object]`) — this had silently broken the clock read through the app's job path. Fixed, plus a route-mapping test asserting the three clock operations' exact methods/paths so clock reads can never fall through to the mutating PUT again.
- Validation: docker `test_campaign_clock_set_and_history_through_api` (set/get/history/party-403) — 4/4 in `test_direct_capture.py`; local 461 passed (the boundary test green after the retag); React 107 passed (clock-chip test: open panel, set with reason, chip reflects date, history renders, toast fires). Live-verified: chip renders the date on load; panel edits round-trip through Core with receipts.

Follow-ups owned elsewhere: retroactive session-note dating and claim stamping (TKT-0118); the campaign-clock tag convention is available for future runtime-state routes.
