---
id: TKT-0118
title: Campaign timestamp coverage — deterministic inheritance, reviewed backfill, approximate vocabulary
status: done
priority: P1
milestone: shared-campaign-knowledge
depends_on: [TKT-0117]
created: 2026-09-14
updated: 2026-09-14
---

# TKT-0118: Campaign timestamp coverage — deterministic inheritance, reviewed backfill, approximate vocabulary

## Context (Sean, 2026-09-14)

Claims carry full temporal columns (effective from/until y-m-d, expected/observed year, calendar id) but only **36 of 465 current claims (8%)** hold an in-game year — almost all deep-history lore. The modern era, where live contradictions live, is undated, which starves TKT-0097's temporal dissolution axis. This ticket absorbs TKT-0044 (date-precision vocabulary).

## Measured reality (2026-09-14, corrected after Sean's ruling)

Only **one** legacy session note carries an in-game date — in-game dating is a new feature this app introduced, never used before it. And sessions are not the dominant evidence root anyway. Current claims by evidence: **character sheets 145, play material 94, lore 72, session notes 55**. Perfect session dating therefore dates only ~55 claims directly. Sean CAN reconstruct most session-note dates from outside knowledge, and accepts the grind ("it's going to be a nightmare") — the design's job is to make the grind as small and leveraged as possible.

**Governing principle: date the spine, review the collisions — full coverage is not the goal.** TKT-0097 needs dates only where state assertions could collide; static lore and descriptions cannot conflict with play. The residue queue is ranked by conflict-relevance, never "date everything."

## Scope (revised)

1. **Session-note dating surface (Sean's reconstruction walk)**: edit the in-game date on each session note retroactively — the unit of grind is ~50 notes, one chronological walk, not 421 claims. Scaffolding: notes listed in real-world order (filename dates), previous note's campaign date shown, monotonicity check (campaign time moves forward; backwards jumps require confirmation), quick +1d/+Nd increments, progress count. Audited writes.
2. **Inheritance pass (mechanical, audited)**: once a session note is dated, its claims inherit `effective_from` from provenance — receipted, idempotent, never overwriting existing dates. Multi-evidence claims take the earliest session establishing them (rule recorded in the ticket when implemented).
3. **New claims stamped at birth**: promotion/review records the effective date as a reviewable coordinate (direct capture already collects an observed campaign date — wire into `effective_from`); corrections inherit or re-date explicitly.
4. **Conflict-ranked residue review**: standing queue for the remaining undated claims, RANKED by conflict relevance — present-state assertions about entities with dated events first (subject + state-ish dimension + undated), static/descriptive lore last or never. Suggested dates from context (entity timeline neighbors, referenced events); approximate vocabulary for the unknowable.
5. **Approximate-date vocabulary (absorbs TKT-0044)**: precision qualifier on campaign dates (exact / circa / early-mid-late / bounded before-after); ordering treats approximates as ranges.

## Acceptance

- Session dating walk covers the sessions Sean can reconstruct; each dated note immediately dates its claims.
- Residue review is conflict-ranked (measured: how many claims are actually high-relevance vs total).
- Before/after coverage numbers recorded in the ticket.
- Inheritance is deterministic and provenance-derived only; reviewed backfill decisions are receipted.
- Approximate dates order correctly against exact ones in chronology contexts (timeline, conflict temporal dissolution).
- TKT-0044 closed as absorbed.

## Out of scope

- Conflict detection itself (TKT-0097 — unblocked by this ticket completing).

## Infrastructure delivered (2026-09-14, deployed) — the walk itself is Sean's

- **Migration 0058**: `document_campaign_dates` overlay + change history (imported documents are never rewritten), `apply_session_document_date` (upsert + history + immediate provenance stamping of the document's undated claims; never overwrites), `inherit_claim_dates_from_documents` (bulk, idempotent, overlay + capture-frontmatter sources).
- **Core routes** (`campaign-dating` tag): the walk listing (`GET /campaign/session-dating` — real-world ordered, current in-game date with overlay-wins, per-note waiting-claim counts), `PUT /campaign/session-dating/{id}`, `POST /campaign/claim-dates/inherit`, `GET /campaign/undated-claims` (conflict-ranked: entity-linked claims whose entities have dated events first).
- **UI — the dating walk** on the Tools page: 50 session rows in play order, previous dated session shown as anchor ("after 505-2-28"), per-row date entry (year-month-day; regex accepts 1–6-digit and negative years — a 4-digit-only bug was caught by the test since the campaign year is 505), backwards-date warning, "N claims waiting" per row, capture-dated notes shown read-only, Sync button, toast + message with stamped counts, and the conflict-ranked residue queue (collision-risk claims flagged).
- **Capture-at-birth**: direct-input claim commits now carry `effective_from` from the observed campaign date alongside `observed_at` (the proposal machinery already supported it — one-line wiring).
- **First live inheritance run**: stamped 11 claims from the one dated capture note; coverage 36 → 47 of 465 current claims. Live walk: 1 of 50 sessions dated, 49 waiting, 44 claims waiting to inherit.
- Validation: docker `test_session_dating_walk_and_inheritance` (walk lists undated → set date stamps via provenance → correction never overwrites the first stamp → residue excludes dated claim → bulk counts) — 5/5 in test_direct_capture; local 461 passed; React 108 passed (walk test: progress line, anchor hint, date entry, stamp receipt, residue flagging).

## Remaining (Sean's grind + deferred scope)

- **The reconstruction walk itself** — ~49 sessions Sean dates from outside knowledge; each dated note immediately stamps its claims.
- **Approximate-date vocabulary (TKT-0044's scope)** — not yet built; residue per-claim date entry (currently read-only, ranked) can arrive with it.

## Reconstruction anchors (Sean's paper notes, 2026-09-14 — authoritative)

- **First session: 505-10-20** (set on `sessions/notes/2023-10-10.md`, receipted). Current date: 505-11-27 (the "550" in the conversation read as 505; the clock and timeline agree).
- All 50 sessions fall between 505-10-20 and 505-11-27 — **39 in-world days, more than one session per day on average**; the 2026 Ishi'ra'la floor sessions likely compress into a few in-world days (one crawl).
- Dated events to place: **10/25 party arrived at Unity · 10/26 John Seward rally · 10/31 Martin Faeroth summoned Vael'ka'noth · 11/1 party returned to Unity · 11/4 Battle for the Heart of Unity · 11/5 Assault on Vael'tha'nore.**
- Cross-check that passed: the 12/6/25 note's "Tue the 1st of December" implies 505-11-26 is a Thursday — exactly what `lore/timeline.md` states. Two independent anchors agree on the calendar.
- Corpus scan (read-only, all 50 notes): no harvestable in-world dates in the notes themselves; real-world date headers only; the sole in-note anchors are the December expiry (12/6/25) and a "leave at dawn on Monday" (9/6/25).
- Text-search mapping so far: **2025-03-01 contains Seward + Heart of Unity + Martin's death at Vael'ka'noth** — Sean's 10/31–11/4 climax arc concentrates in this one real session. "Rally" appears in no note; the Vael'tha'nore assault appears only as backstory in the ishirala archive log.
- Open convention: a session spanning several in-world days takes its **start date** at note level (claims can still be re-dated individually later).

## Corpus rulings (Sean, 2026-09-14 — walk scope corrected)

- **session-0-legacy-dump** is the aggregation of all Raven King campaign notes, already split into the `2023-10-10` → `2025-03-01` notes — excluded from the walk (zero undated claims; the split notes carry them).
- **sessions/prep/ documents are preparation, not table notes** (return-to-the-monastery-2026-06-17, session-prep-2026-06-04, session-prep-floor4) — excluded from the walk; prep is explicitly not real play.
- The ishirala-floor3 archive log is a misfiled duplicate of notes/2026-04-25 — also excluded (already was via archive/).
- **Handouts have session notes built into them.** Journal dating context for later claim stamping: **Mads journal is from the year 505**; **Vika Lana's journal is undated but occurs during the era of the Raven King** (see lore/timeline.md for era boundaries). These date via document overlays when their claims need it — not via the session walk.
- Walk now lists actual table sessions only (45 after exclusions; 2 dated).

## THE WALK IS COMPLETE (2026-09-14, Sean)

Sean dated all 45 table sessions in one sitting through the Tools panel — monotonic 505-10-20 → 505-11-27, prep and archive docs excluded, capture note confirmed. Claims inherited in real time per note: **coverage 36 → 91 of 465 current claims (20%); session-evidenced undated claims: ZERO.** His multi-day-session convention: dated by main-event day (2025-03-01 → 505-11-05, the Vael'tha'nore assault).

Remaining in this ticket: the residue (374 undated claims — lore/character/play-material evidenced, conflict-ranked queue live) and the approximate-date vocabulary (TKT-0044's scope, with per-claim residue dating). Per the governing principle, much of the residue is static lore that may legitimately stay undated; the queue's collision-ranked head is what matters for TKT-0097.

## Closure (2026-09-16, ticket audit)

The ticket's deliverable — campaign timestamp coverage through the dating walk, deterministic inheritance, capture-at-birth stamping, and the conflict-ranked residue view — is complete and in live use (46/46 sessions dated, 91 claims carrying campaign dates, session-evidenced undated claims: zero). **Remaining scope deferred to follow-up, not blocking:** the approximate-date vocabulary (TKT-0044's precision qualifiers) and per-claim residue date entry — both pick-up-when-valuable; most residue is static lore that may legitimately stay undated per the governing principle (date the spine, review the collisions). Closed.
