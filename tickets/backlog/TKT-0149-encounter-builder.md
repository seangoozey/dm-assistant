---
id: TKT-0149
title: Encounter builder — a specialty surface for authoring and running table events
status: backlog
priority: P2
milestone: trustworthy-librarian
depends_on: []
created: 2026-09-30
updated: 2026-09-30
---

# TKT-0149: Encounter builder — a specialty surface for authoring and running table events

## Context

The minimal encounter creator landed 2026-09-29 (title + markdown body → authored document, session-independent, no statement extraction). Sean's follow-up ruling: that was a stub misremembered as existing — **a full encounter builder needs to be built at some point.** What exists today: the creator stub; EncounterEntryView (renders `##` sections as ordered stages); encounter lifecycle/progress (resume checkpoints); table notes with encounter context; ADR-0021's ruling that encounters are Entities (kind `encounter`) that own their claims, with auto-mentions carrying every cross-reference.

## The architecture decision (Sean's lean recorded 2026-09-30)

**Should the builder be a specialty branch of Brainstorm, or reuse most of Brainstorm's machinery?**

Sean leans **specialty branch** — encounter building is specialized enough (structured stages, running order, read-alouds, table-event record) that Brainstorm's thinking-interface idiom doesn't fit it, matching the ADR-0015 flow-surface ruling (each surface keeps its own idiom; shared machinery lives beneath). The alternative (build it inside Brainstorm's machinery and surface) was considered and is disfavored. DECIDE AT PICKUP with a concrete design; the lean stands unless the design work says otherwise.

What "beneath the idiom" should be shared regardless (the reusable machinery, per TKT-0150's assessment): the ADR-0019 working-file autosave, mention recognition/suggestions, the promotion pipeline for any claim promotion, and the claim card (TKT-0142) once it exists — the builder is born on shared components, per the standing rule (no new surfaces before/without the reusable surface).

## Scope when taken up

- **Structured authoring**: stages/sections in order (the `##` model the view already renders), with per-stage notes anchors; read-aloud text authoring (creative generation stays opt-in per the invariants — requested encounter read-alouds are the sanctioned AI surface).
- **The encounter Entity**: kind `encounter` per ADR-0021 — authored document mints the entity (authored-or-referenced criterion); the encounter owns its claims; auto-mentions tag every referenced record and every date (timeline pickup, viewing only).
- **Running integration**: the existing lifecycle/progress, table notes, and resume checkpoints attach to builder-authored encounters unchanged.
- **Claim promotion**: encounter statements promote through reviewed surfaces, owned by the encounter (never orphaned — the 0148 guardrail).

## Out of scope

- Rebuilding the view/run machinery (it exists).
- Brainstorm's WIP lifecycle questions (TKT-0144) — related but separate.

## Validation evidence

(to record when built)
