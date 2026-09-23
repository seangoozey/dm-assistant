---
id: TKT-0139
title: Define the Qualified Entity standard — the bar every library entity must clear
status: backlog
priority: P2
milestone: trustworthy-librarian
depends_on: []
created: 2026-09-21
updated: 2026-09-21
---

# TKT-0139: Define the Qualified Entity standard — the bar every library entity must clear

## Context

Sean's ruling (2026-09-21): the library is to be migrated so that **everything is a qualified entity** — but no exact definition of a Qualified Entity exists (verified: no occurrence in docs/decisions/specs; ADR-0017 defines what an Entity *is* — Attributes + Claims defining an Identity — but not a completeness/qualification *bar*). This ticket produces that definition; TKT-0140 (the migration) is blocked on it. Definition work belongs with the domain vocabulary: expect an ADR-0017 amendment or a product spec section, plus a glossary entry.

## Scope when taken up

- Draft the **Qualified Entity standard**: the checkable bar an entity must clear, candidates including (to be ruled on, not assumed):
  - **Identity through the declared machinery**: every assertion it asserts is a Claim with Truth State, authority, and provenance (no canon-without-provenance blobs — the retired profile-summary lesson).
  - **Ownership resolved**: no orphaned claims that belong to it sitting unassigned (TKT-0138 feeds this); one owner per assertion.
  - **Attributes filled to kind**: the kind-appropriate attributes are present and vocabulary-backed where vocabularies exist (0129); Kind is structurally correct. **RULED by Sean (2026-09-21): attributes ARE claim-backed and part of the CTS** (originally posed as: Today attributes carry no claim/evidence/Truth State (life_status is the only anchored exception); "filled to kind" could mean bare values or claim-anchored values. The ruling decides whether the standard mandates the anchor (generalizing the life_status pattern) or treats full claims-derived profiles as the eventual shape — it gates TKT-0137's attribute promotion.) The ruling settles the strongest form: attribute values carry Truth States via backing claims; the write path mints claims behind the one-click dropdown (decision memo below).

  **Decision memo (2026-09-21, Sean's Romulus case):** the tension is dropdown friction (every change demanding claim ceremony kills the feature) vs. truth-state management (claim backing gives dated, evidenced, reasoned supersession — "High Elf observed 9/21" → "turned Orc observed 10/23" distinguishes transformation from retcon and keeps the prior period queryable). Resolution if claim-backed: **the editor stays a one-click fast path that MINTS claims behind the dropdown** (the life_status pattern generalized) — auto-claim on write (dated, Established by default), anchoring optional at write and attachable later, unanchored values marked (the 0123 backfill playbook); play-sourced changes supersede via the session-note claim automatically. Bare fields forfeit the Romulus case entirely and keep attributes permanently outside truth machinery. Recommended bar wording: qualified attributes are *dated* (claim-minted) — *anchored* is the nudge target, not the gate.
  - **Page state explicit**: an authored Description page, or the deliberate unpaged state — never a synthesized stand-in doing a page's job.
  - **No undocumented presentation**: nothing renders as canon that isn't a claim, attribute, or authored document (ADR-0015 layer discipline).
- The standard must be **machine-checkable** where possible (a Core audit endpoint can compute most of it) — TKT-0140's queue and any standing review depend on that.
- Rule explicitly on scope boundaries: are plans, encounters, and session documents held to a parallel standard, or is "qualified" an entity-only bar? (They are their own record classes per ADR-0006/0013; presumed out of scope unless ruled otherwise.)
- Deliverable: the definition recorded as an ADR amendment/spec + glossary entry + the checklist the audit endpoint will implement.

## Out of scope

- The migration itself (TKT-0140).
- Changing what an Entity is (ADR-0017 stands; this defines qualification, not structure).

## Validation evidence

(to record when built)
