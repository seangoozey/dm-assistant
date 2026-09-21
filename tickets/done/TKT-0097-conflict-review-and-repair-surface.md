---
id: TKT-0097
title: Review and repair evidence-linked factual conflicts
status: done
priority: P1
milestone: shared-campaign-knowledge
depends_on: [TKT-0091, TKT-0094]
created: 2026-09-06
---

# Outcome

Expose factual contradictions and suspected comparisons in a dedicated review surface
without filling normal campaign pages with provenance controls.

## Scope

- Consume the structured retrieval conflict contract; distinguish verified factual
  conflict, possible retcon, and unverified suspicion.
- Show both full assertions, source revision/span evidence, authority and campaign
  time. Explain the same-subject/property/scope comparison where available.
- Add a persistent, deduplicated review queue with auditable lifecycle; read-time
  issue hashes are not currently durable queue records.
- Offer correction, explicit supersession, or a documented not-conflicting resolution
  through existing exact reviewed mutation commands. No silent winning assertion.
- Revalidate current evidence/visibility before preview and application. Stale issues
  must refresh, not apply an old decision to a changed claim.
- Dismissal is a review disposition, not a canonical deletion or truth change.

## Acceptance

An actual contradiction can be opened with both sources and repaired through one
audited receipt; repeated detection does not duplicate an unresolved issue; stale and
hidden evidence cannot be acted upon or leaked. Compatible claims can be marked as
not conflicting without altering their assertions. Partial coverage and truncated
results must never appear as a clean campaign-wide consistency bill.

## References

- [Comparison contract](../../docs/testing/evidence-comparison.md)
- [Shared knowledge design](../../docs/architecture/shared-campaign-knowledge.md)

## Migration and rollback

Any persistent queue requires its own migration. Preserve claims, sources and prior
receipts. Disable the surface without deleting canonical records or review history.

## Absorbed scope (2026-09-14 ticket audit)

TKT-0091's remainder now lives here: PostgreSQL coordinate production for automatic live factual-conflict discovery, and replacement of the legacy unverified-alert mode heuristic (its false positives and mode privacy remain open).

## Sequencing (Sean, 2026-09-14)

Completes AFTER TKT-0117 (calendar management) and TKT-0118 (timestamp coverage): the queue must launch trustworthy — without temporal dissolution data it re-creates the always-firing legacy alert. The design conversation also settled the detection model: mechanical comparison over structured dimensions (status, possession, location, membership, leadership) where values are mutually exclusive; time and authority dissolve what they can; semantic contradictions ("ugly vs handsome") are never auto-judged — an AI pass may at most propose candidate pairs into the queue as unverified suggestions the DM confirms.

## V1 delivered (2026-09-15, deployed) — the queue launched trustworthy

- **Migration 0059**: `conflict_decisions` (dismiss + supersede, unique per pair) + `apply_conflict_decision` — supersession rides the full audited change-set machinery (workflow session, change set, item, receipt, `claim_supersessions` row); dismissal records "reviewed, kept both." Idempotent on pair replay; reason required.
- **Detection (deterministic, deliberately narrow)**: observed real-play deaths — the dead record's own name adjacent to a death word, dated, linked via subject OR related entities (the live Martin Faeroth death claim is subjectless; caught during live verification and fixed) — versus current claims about that entity dated strictly later. Time keeps undated journal mentions out automatically; authority is displayed on both sides.
- **API** (`conflicts` tag): `GET /campaign/conflicts`, `POST /campaign/conflicts/decisions` (DM-gated).
- **UI**: Conflict review panel at the top of Tools — pair cards with the observed death and the later claim side by side (authority + dates on both), the past-tense/operative guidance line, and two actions: **Keep both — historical** (dismiss) and **Retire later claim** (supersede, reason prefilled with the death date). Toasts + receipts.
- **Live queue: exactly one conflict — the flagship case.** Martin Faeroth, death observed 505-11-05 vs. the 505-11-11 smuggling claim. One real item, zero noise.
- Validation: docker `test_conflict_review_queue_and_decisions` (detection with dates/authority → dismissal + idempotent replay → audited supersession with change set and reason, queue drains) — 6/6 in test_direct_capture; local 461; React 109 (panel renders pair, retire through audited path, queue empties).

## Legacy alert replacement delivered (2026-09-15, deployed) — first real decision made

- **The legacy count heuristic is removed** (`legacy-count-review-v1` and `legacy_review_issue` deleted): retrieval no longer raises conflict modes from "two authoritative claims happen to share states," which fired on nearly every query (all live probes previously returned exactly one bogus suspected_conflict). Live now: Martin/Goodman/Grey House/Ishi'go'dan queries all `answer` cleanly.
- **Query-time conflicts are verified-only**: `verified-death-temporal-v1` applies the standing queue's rule (observed real-play death vs strictly-later same-entity claim) to the retrieved evidence, raising `possible_retcon` with `verification: verified_comparison`. Honest limitation recorded: retrieval records carry only subject-entity enrichment, so relation-linked cases (the live Martin pair) surface in the standing queue rather than at query time — the queue is the primary surface by design.
- **Corpus tranches documented**: the three behavioral fixtures expecting heuristic conflict modes now expect answer-with-both-records with the ruling noted in `retrieval_cases.yaml`'s header (same-fact disagreements await Postgres coordinate production — the true 0091 remainder); the connected-knowledge baseline regenerated with a 0097 tranche note (14 heuristic-driven conflict modes flipped; latency noise stripped from the file).
- **Sean made the first real conflict decision through the panel** (2026-09-15): Martin Faeroth's 505-11-11 smuggling claim kept as a historical mention alongside the observed 505-11-05 death — receipted dismissal; the pair will never re-fire. The queue is empty and earned it.

## Remaining in 0097

- Replace the legacy retrieval-side `legacy-count-review-v1` alert heuristic (TKT-0091's absorbed remainder) with verified coordinate-based comparison feeding this same queue.
- Additional mechanical dimensions as data warrants (leadership, possession, location) — each must launch with the same zero-noise bar.
- Semantic candidate pairs (AI-proposes, DM-verifies) — per the settled boundary, suggestion-only, never auto-judged.

## Closure (2026-09-16, ticket audit)

Delivered and in live use: the conflict queue (verified death-temporal detection, zero-noise launch — exactly the Martin Faeroth case), audited repair (dismiss + supersede through change sets), the legacy alert heuristic retired in favor of verified query-time conflicts, and — via TKT-0123's life-status enum — the dead-member/dead-leadership detector (dead seats read the enum; no prose matching anywhere). Sean made the first real decision through the panel (receipted dismissal). **Remaining re-homed rather than blocking:** Postgres comparison-coordinate production for the semantic contradiction class (the "ugly vs handsome" pairs — awaits real need; query-time verified rules cover current data) and AI-proposed candidate pairs (explicitly deferred, suggestion-only per the settled boundary — belongs with TKT-0120's writer work when that lands). Closed.
