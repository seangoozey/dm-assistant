---
id: TKT-0113
title: Global toast notifications with one app-wide event bus
status: done
priority: P2
milestone: shared-campaign-knowledge
depends_on: []
created: 2026-09-13
updated: 2026-09-13
---

# TKT-0113: Global toast notifications with one app-wide event bus

## Context

Outcome and error messages today render in per-page message areas (often page-bottom, per the hidden "no current membership to remove" incident of 2026-09-13). The app needs a **global toast**: transient, always-visible notifications for every operation outcome, so nothing important happens only where the DM isn't looking.

## Scope when taken up

- **Event bus first**: one `notify(kind, message, detail?)` surface (success / error / info) that any component can call. This bus is the foundation the Log page (TKT-0112) will consume — one vocabulary, transient + durable consumers.
- **Toast stack**: fixed-position overlay (top-right), token-styled (parchment panel, hairline border; error variant with the warm error accent), auto-dismiss with pause-on-hover, click-to-dismiss, capped stack length. Conventions rules apply (no transform on interactive states).
- **Scrape the entire app for anything that would use it** (required inventory at pickup). Initial sweep from the 2026-09-13 codebase — every `set*Message` / `set*Error` / `.error` state pair is a candidate:
  - `identityMessage`/`identityMessageIsError` (Identity page decisions, refusals)
  - `entityProfileMessage` (profile saves, kind corrections, membership/role decisions, refusals)
  - `pcMessage` (PC profile saves), `claimEditMessage` (claim corrections), `sessionCaptureError` (captures)
  - `reviewError` (migration review), `encounterDossierError`, `brainstorm` session messages
  - **Backend job failures** (`reviewCampaign` class errors bubbling through the review-job client) — currently page-bottom only; these must toast regardless of which page is open
  - Background refresh failures that today fail silently (`.catch(() => {})`)
- Keep in-page message areas where they add context (receipts beside the editor); toasts mirror, not replace.
- Behavior becomes configurable via TKT-0114 (enable/disable, duration).

## Progress (2026-09-13, deployed)

Built: `toasts.tsx` — module-level event bus (`toast.push(kind, message)`) with dedupe (identical message refreshes instead of stacking), 6.5s auto-dismiss, click-to-dismiss, 4-visible cap; `ToastStack` rendered in the app shell (top-right, token-styled; error toasts are `role="alert"`); `resetForTest()` for suite isolation. Wired 19 outcome surfaces: identity decisions (success + refusal), entity profile saves, kind corrections, membership add/remove (success + refusal), role assign/clear (success + refusal incl. leadership refusals), Roles page define/seat/vacate/link, PC profile saves, claim corrections, session-capture failures. Receipts stay in the in-page messages; toasts carry notification phrasing. Remaining scrape inventory (background `.catch(() => {})` refreshes, brainstorm/migration/dossier messages) intentionally left for the next pass.

Validation: 4 bus tests (dismiss, alert role + auto-dismiss, dedupe, cap) + App integration (refusal mirrored into `.toast`); React 97 passed, `tsc` clean; verified live — re-adding an existing member to Carpet Rollers refused by Core and the refusal appeared as a top-right error toast (the previously buried review-job error class). Test assertions updated where in-page message and toast mirror the same phrase.

## Out of scope

- Durable storage of events (that is TKT-0112).

## Completion (2026-09-14)

Surface scrape finished: **27 outcome surfaces** wired to the bus — identity decisions, entity-profile saves, kind corrections, membership add/remove, role define/assign/clear/link, Roles-page operations, PC saves, claim corrections, session-capture failures, migration review errors (import review, candidate load, extraction status/refresh), background job failures and queue/cancel notices, and the NPC dossier error. Background `.catch(() => {})` refresh failures stay silent deliberately — they are non-critical UI refreshes whose failure mode is staleness, and toasting them would be noise; revisit with TKT-0110's audit if they ever mask real loss. React 100 passed, `tsc` clean, deployed. Closed at ticket audit.
