---
id: TKT-0043
title: Failed-plan review queue
status: backlog
priority: P2
milestone: trustworthy-librarian
depends_on: []  # TKT-0031 closed long ago — satisfied
created: 2026-08-04
updated: 2026-09-28
---

# TKT-0043: Failed-Plan Review Queue

## Outcome

When real play disrupts an intended plan, the system records the observed disruption and queues a failed-plan review item without inventing the plan's reaction.

## Context

ADR-0006 (TKT-0031) and the truth-state table require that a disrupted intention records only the observed disruption and queues review of the failed plan. The plan-lifecycle disruption-to-review-item path is not yet implemented. This closes a defined invariant gap: the system does not invent NPC or faction reactions to failure.

Read `docs/decisions/ADR-0006-first-class-plans-and-agency.md`, `docs/product/truth-state-authority.md`, and TKT-0031.

## Scope

- When an observed claim contradicts an active in-world plan's intention, the plan lifecycle transitions to `failed` and a review item is queued.
- The system records only the observed disruption; it does not synthesize the plan's reaction or mark the outcome beyond the lifecycle transition.
- The review item surfaces the plan, the disrupting observation, and its evidence.

## Out of scope

- Inventing or generating the plan owner's reaction.
- Auto-resolving the failed plan without human review.
- Player-plan disruption (player plans are nonbinding and revocable; they do not fail).

## Acceptance criteria

- [ ] A disrupting observed claim transitions an active in-world plan to `failed`.
- [ ] A failed-plan review item is queued with the plan, observation, and evidence.
- [ ] The system does not synthesize a reaction or outcome for the disrupted plan.
- [ ] Player plans are unaffected (they are nonbinding and revocable, not failable).
- [ ] Sanitized tests and full repository validation pass.

## Refreshed 2026-09-28 (board hygiene)

Still open and still a live non-negotiable invariant (AGENTS.md: "Failed NPC or faction plans are marked for review; the system does not invent reactions"). Current state verified: the plan lifecycle SUPPORTS `failed` and requires a separate observed claim for the transition (application/plans.py), but nothing DETECTS a contradicting observation and queues the review — the invariant is unenforced by the system. Dependency TKT-0031 is long done; nothing blocks this beyond priority. Natural home when built: the detection slot on TKT-0142's unified claim card / the same conflict machinery as 0097 and TKT-0141.