---
id: TKT-0127
title: Asynchronous draft generation with a holding queue
status: done
priority: P1
milestone: shared-campaign-knowledge
depends_on: [TKT-0120]
created: 2026-09-17
updated: 2026-09-17
---

# TKT-0127: Asynchronous draft generation with a holding queue

## Context (Sean, 2026-09-17, closing TKT-0120)

"While waiting for the call to come back, the rest of the app is blocked. Pages can be loaded but they all give Working/Loading/Wait messages. And then when I go back to the section being generated its been lost. There's nothing about this generation that needs to block. It should be asynchronously queued and rendered and then put in to a holding queue that lets me get back to it and either commit or discard it. Maybe something like the floating table notes will hold the queued renders and have a click to follow back option."

Two stacked causes:

1. **UI-level**: the composer awaits the draft promise in place — navigating away discards the composer and the pending result.
2. **Worker-level**: the app's live path runs every Campaign Core operation through the single windmill worker (the review bridge); a 10–30s draft job queues ALL page loads behind it. This is the "every page says Working/Loading" symptom.

## Scope

- **Fire-and-forget drafting**: clicking Draft parks the request and returns the composer/UI immediately; the request runs to completion regardless of navigation.
- **Holding queue (the floating-notes pattern)**: a session-scoped pen of in-flight and ready drafts — each entry shows entity name, elapsed time, state (running → ready/failed), and a click-to-follow-back action that reopens that entry's composer seeded with the result (commit = file as usual; discard = drop the entry). Ready/failed transitions toast and log with timings (timings shipped in 0120 v2.2).
- **Worker contention fix** (investigate + implement one):
  - preferred: route prose drafting off the shared worker — either a dedicated windmill queue/worker for long AI jobs, or the direct same-origin `/campaign-core` proxy path for `/prose/draft` if the deployment supports it (page loads then never queue behind drafting);
  - the jobPlatform start/inspect pattern (as candidate extraction already uses) if a queue split is simpler.
- Failed drafts stay in the pen with the error until dismissed — nothing silently lost.

## Out of scope

- Server-side persistence of draft results (session-scoped pen first; durable draft history can follow if wanted).
- Extraction jobs' interactivity (already job-platform based).

## Validation evidence

(to record when built)

## Validation evidence

Delivered 2026-09-17, deployed, live-verified.

- **The job** (`f/dm_assistant/jobs/prose_draft.py`): one Campaign Core `/prose/draft` call as durable Windmill work, launched async by the app backend starter (`backend/start_prose_draft.ts`, windmill-client `runScriptByPathAsync`) — the same pattern as candidate extraction, per Sean's ruling to use Windmill's worker machinery.
- **Worker contention fixed**: compose gains `windmill-worker-2` (same group, own cache volume) — Windmill distributes queued jobs to idle workers, so page loads (the review bridge) never queue behind a long AI job. Both workers healthy post-deploy.
- **Fire-and-forget composer**: Draft from selected queues the job and releases the composer immediately ("Draft queued — keep working…"); the request no longer lives in the UI's await.
- **The drafts pen** (floating, bottom-right, table-notes pattern): entries show entity name, live elapsed ticker while running, and on completion the draft excerpt + support line (model · elapsed · tokens · cited records) with **Return to draft** (loads the entry, seeds the guarded composer with the marker-stripped prose — filing/canceling there is commit/discard) and **Discard**. Failed jobs stay in the pen with their error until dismissed. Ready/failed transitions toast and log with timings (persisted log).
- Tests: React 128/128 — queue→poll→ready→claim flow (material shape asserted through `startProseDraft`), failed-job path (pen retains error; toast + persisted session log recorded), jobPlatform interface coverage for `start_prose_draft`. Deployed app version + job verified in windmill storage.

## Post-delivery fixes (2026-09-17, same day)

- **Readable provider failures**: Sean's live run failed after 172.6s with "Internal Server Error" — both 90s provider attempts timed out and the raw timeout exception escaped the endpoint as a 500. ProseHarness now translates every provider fault into a ProseDraftError with its cause ("the prose provider failed: a request exceeded the configured timeout after all retries"), so the tray shows the real reason, not a mystery 500. Unit-tested with a failing client.
- **Citation mirroring restored on claim**: claiming a Drafts-tray result now seeds the composer's selections from the draft's actual citations (claims + relations) instead of all-claims-checked — filing records exactly the cited records. Test covers "1 of 2 referenced" after a one-citation draft.
- **Named**: the floating queue is the **Drafts tray** (glossary entry + all copy).
- **Floating trays manager**: Settings → Floating trays (session notes + Drafts tray: dock left / right / hidden). Launchers now live in stacking tray docks (no more overlap); panels open on their tray's side; hidden trays show no launcher while queue events still toast and log.

## Claim-flow fix (2026-09-18, from Sean's live fork-guard error)

Claiming a Drafts-tray result seeded the composer as revision mode with whatever document was *selected* — for an entry paged by an imported document that targeted the imported doc, and Core's rename fork-guard correctly refused ("no longer this entity's page path"). Fixed: the composer only targets a revision when the entry's current page is the authored description; claimed drafts on imported-paged (or unpaged) entries file as fresh pages. The rename case (authored page, renamed entity) now recovers gracefully: on the fork-guard rejection the composer retries once as a new page per Core's own guidance, with a message noting the old page document remains as history. React 130/130 incl. the imported-page regression test.
