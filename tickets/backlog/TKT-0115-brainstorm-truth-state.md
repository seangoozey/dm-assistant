---
id: TKT-0115
title: Brainstorm truth state — findable prior brainstorm thinking without granting canon
status: backlog
priority: P3
milestone: shared-campaign-knowledge
depends_on: [TKT-0104]
created: 2026-09-13
updated: 2026-09-13
---

# TKT-0115: Brainstorm truth state — findable prior brainstorm thinking without granting canon

## Context (Sean, 2026-09-13 — ticketed for consideration; not authorized for implementation)

The working brainstorm's thoughts are deliberately outside the graph: they are immutable evidence documents awaiting review, and nothing from them enters retrieval until promoted to claims. The exposed gap: after a session closes, its un-promoted thinking is reachable only through the Migration queue — a later brainstorm cannot ask "what did we already consider about the Long Night?" Sean's proposal to explore: **an additional truth state** for brainstorm content, below the existing ladder (observed > established > intended/prepared > possible), so prior session thinking is retained in retrieval as what it is — considered, not canon.

## Design questions to answer before any build

- **State vs. authority vs. separate record type.** Claims already carry `authority='brainstorm'` and `state='possible'` for *promoted* possibilities. The new state must be strictly sub-canonical: brainstorm-session content that is not even a tracked possibility yet. Decide whether it is a new `ClaimState` (e.g. `considered`), a separate non-claim record type surfaced by retrieval, or a projection over brainstorm evidence documents.
- **What the state must never do** (invariants that cannot bend):
  - Brainstorm content stays non-canon until an exact, reviewed proposal is promoted — this state adds findability, not authority.
  - Never renders in canonical views (Library claims, entity coverage counts, heroes); never evidences anything; promotion still goes through the provenance-first review path unchanged.
  - PC-related thoughts remain plot pressure/opportunity, never predictions (standing PC-agency rule).
- **Retrieval surfacing.** A distinct result role/section ("Suggestions from past brainstorms"), visually and structurally separate from evidence; graph participation only as a clearly-marked non-canon layer, if at all — weights rank, never grant authority. Bundle inclusion is a design decision at pickup (parallel layer vs. text search only).
- **Lifecycle.** What happens to a `considered` record when its session's proposal is later promoted (dedupe/supersede?) or explicitly rejected (retained as "considered and rejected"? — that may itself be valuable history).
- **Relationship to TKT-0099** (lore creation queue) — its drafts/synopses are the same class of non-canon prose; whatever mechanism lands should serve both, not two parallel ones.

## Out of scope until ruled on

- Any implementation. This ticket records the idea and the constraints; picking it up starts with Sean ruling on the design questions above.
