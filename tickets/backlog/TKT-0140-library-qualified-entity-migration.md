---
id: TKT-0140
title: Migrate the whole library to Qualified Entities — everything reaches the bar through the Promotion Pipeline
status: backlog
priority: P2
milestone: trustworthy-librarian
depends_on: [TKT-0136, TKT-0139]
created: 2026-09-21
updated: 2026-09-21
---

# TKT-0140: Migrate the whole library to Qualified Entities — everything reaches the bar through the Promotion Pipeline

## Context

Sean's ruling (2026-09-21): migrate **everything in the library to a Qualified Entity**, including summaries. **Blocked by stable promotion** — the Promotion Pipeline (TKT-0136) must be complete across its surfaces and proven in real use before this runs, because the pipeline is the migration's engine. **Blocked by the standard** (TKT-0139) — the migration audits against the Qualified Entity definition. Per the standing productize rule, this lands as a standing in-app review (an "unqualified entities" queue in the Tools panel), never a one-time manual backfill.

## Scope when taken up

- **Core audit endpoint**: compute the Qualified Entity checklist per entity (TKT-0139's machine-checkable bar) and return the unqualified set with per-entity reasons — the queue's data source, re-runnable so newly-degraded entities reappear.
- **Summaries migrate via the Promotion Pipeline**: profile `summary` content becomes a Description through the pipeline, not a copy — the prose derives candidates, statements face the mandatory include-or-exclude review (ADR-0018 pt 8), and the description files with provenance. Live today: 1 substantive summary of 19 profiles; the field is then retired (editor + synthesized-page injection removed, per the ADR-0015/0017 violation assessment of 2026-09-21).
- **Route every unqualified entity through its lane**: orphaned assertions via the TKT-0138 bridge (queue-for-Lore / assign), unpaged entries via Write-description + promotion review, wrong-kind or thin-attribute records via the profile editors, synthesized-only content replaced by authored pages or deliberate unpaged state.
- **The queue drives to zero and stays there**: entity-level rows with reasons and shortcuts into the right lane; progress visible (like the identity review's 281-decisions run); completion recorded with evidence.
- Non-entity record classes (plans, encounters, sessions) follow the TKT-0139 scope ruling — presumed excluded unless a parallel standard is ruled in.

## Out of scope

- Auto-qualification: every fix is an explicit DM action in its reviewed lane; the audit only finds and routes.
- New qualification criteria beyond TKT-0139's definition.

## Validation evidence

(to record when built)
