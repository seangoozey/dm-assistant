---
id: TKT-0136
title: Promotion Pipeline — reusable Proposal → Candidate → Claim review and commit
status: backlog
priority: P2
milestone: trustworthy-librarian
depends_on: []
created: 2026-09-20
updated: 2026-09-20
---

# TKT-0136: Promotion Pipeline — reusable Proposal → Candidate → Claim review and commit

## Context

Sean's ruling (2026-09-20): build one reusable progression for turning working material into canon, serving Description filing, Lore creation, and Brainstorm promotion — plus a repair intake for in-app material that was written but never promoted correctly. Key constraint: **user ease** (the DM touches only what is wrong). The Migration wizard solved this class for imports with poor results (sequence-as-navigation, structure-as-gate, per-claim form grids, approval ceremony); the direct session reviewer proved the better pattern. Framework: `docs/architecture/promotion-pipeline.md`; decision record: ADR-0018 (proposed). Shaping rulings locked: compact scan-able candidate list, "Approve promotion" commit verb, name "Promotion Pipeline".

## Scope when taken up

- **Backend facade** (`campaign-core/src/dm_assistant_core/application/promotion.py`):
  - `derive(surface, proposal_refs, hints)` → candidate list: assertion text, subject target, defaulted Truth State, provenance, consequence (new / moves from / replaces / conflicts), deterministic-check results. A read.
  - `approve_promotion(payload, idempotency_key)` → single-action binding transaction: build immutable proposal version, bind approval to exactly that version + items, apply (entities, claims, re-attributions, supersessions, documents), receipt — reusing change_sets / candidate_proposals internals, no new canonical mutation route.
  - Server-side defaults per the framework's defaults table (authority, visibility, confidence, conditionality, recorded_at, dates). The 20-field `CreateClaimDecision` is assembled server-side.
- **Promotion Review list component**: compact scan-able rows — all approvable elements at a glance (text, subject chip w/ search, state chip, provenance cite, consequence/flag line), inline fixes, one expandable dimensions disclosure per candidate, one "Approve promotion · N claims [+ bundle]" button; receipts and failures into the toast/Log bus. UI tokens per ui-conventions; no wizard chrome.
- **Surface adoption** (proposed order, thinnest payload first):
  1. Brainstorm promotion (Considered claims on chosen subjects)
  2. Lore creation (adds re-attribution and new-entity bundle consequences)
  3. Description filing (adds citation mirrors and the description-document bundle)
- **Repair lane**: standing unpromoted-material audit (entities with zero claims but authored documents; unpromoted brainstorm thoughts; direct captures with pending statements) surfaced as a Tools-panel review that reopens stalled artifacts as proposals; *replaces claim #Z* consequences commit through supersession receipts.
- **Glossary**: "Promotion Pipeline" entry lands with the component (test-enforced registry rule).

## Out of scope

- Migration wizard rework (steps 3–6 collapse into this component under TKT-0131, separately).
- Durable pending-proposal queues for ephemeral surfaces (rejected in ADR-0018).
- Any AI seam beyond the four fixed ones; AI never gates or executes commit.
- TKT-0040's conflict-gated lore application specifics (the pipeline surfaces conflicts inline; 0040 remains its own track).

## Validation evidence

(to record when built)
