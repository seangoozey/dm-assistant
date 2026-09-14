---
id: TKT-0112
title: App activity log page
status: in-progress
priority: P2
milestone: shared-campaign-knowledge
depends_on: [TKT-0113]
created: 2026-09-13
updated: 2026-09-13
---

# TKT-0112: App activity log page

## Context

The Inquisitors removal failure (2026-09-13) produced a Core refusal that surfaced only in a message area at the very bottom of the page — Sean found it by scrolling and poking. Transient messages are not enough; the app needs a durable, scannable log of what happened and what failed.

## Scope when taken up

- A **Log page** in the main nav: reverse-chronological activity with kind, time, actor context, and outcome — successes with receipts, refusals with Core's named reasons, and errors with the failing surface.
- **Scrape the entire app for anything that would use it** (required inventory at pickup). Initial sweep from the 2026-09-13 codebase:
  - Identity decisions (create/alias/misspelling/role/membership/define/assign — Core `identity_decisions` is already a durable audit source)
  - Change-set applications, profile saves (receipts), kind corrections
  - Session note captures and claim corrections/commits
  - Brainstorm captures, pins, proposal promotions
  - Import runs, extraction jobs, Windmill job failures (the `reviewCampaign` error class — backend job errors currently render only in page-bottom message areas)
  - Retrieval/lookup failures where surfaced
- Source design at pickup: combine Core audit tables (read-only projection) with a client-side event buffer fed by the toast/event bus introduced by TKT-0113 — one event vocabulary, two consumers (transient toast, durable log).

## Progress (2026-09-13, deployed)

Built the Log page (main nav, between Tools and Conventions): a merged, newest-first stream of **session events** (the TKT-0113 event bus now records every push — repeats included — into a 200-entry session log with timestamps) and **audited decisions** from Campaign Core via the new `GET /identity/decisions/recent` (repo `recent_decisions`, newest first with `details`; `IdentityDecisionEntry` model; backend op `list_recent_decisions`; client `listRecentDecisions`). Rows carry time, kind (Done / Error / Notice / Decision · kind), message with structured summary (action, role, member, faction), and source ("This session" vs "Campaign Core audit"); Errors-only filter; count line; Refresh. Session events are honestly labeled browser-session scoped; durable truth stays in Core.

Validation: docker `test_recent_decisions_listing_newest_first` (24 identity tests pass); React Log-page test (merged stream, structured summaries, errors filter) + bus log-recording test — 99 React passed, `tsc` clean, local 460 passed. Live verification: the page renders 100 real audited decisions, including today's Inquisitors roster creation (Eustice → Inquisitor, Romulus → Grand Inquisitor) and the Fleurite Exiles role links.

Remaining for full ticket scope: additional durable sources (change sets, import runs, job failures), error-message normalization (review-job errors currently carry stack suffixes into toasts/log), and the TKT-0114 configurability.

## Out of scope

- Log-based analytics; this is a DM-facing activity trail, not telemetry.
