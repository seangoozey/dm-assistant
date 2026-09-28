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

### Draft proposal written (2026-09-21)

`docs/product/qualified-entity.md` — the standard as a draft for review: Q1–Q10 checkable criteria (asserts something; real claims; clean ownership; correct kind; claim-minted dated attributes; vocabulary-backed; anchoring as nudge not gate; explicit page state; presentation discipline; visible Truth States), the four work items it requires (attribute minting, deliberate-unpaged marker, the audit endpoint, summary retirement), and five open decisions for Sean (zero-claim floor, non-entity scope, binary vs tiered, grading granularity, mechanism ticketing). Rulings land → ADR-0017 amendment + glossary entry + spec status.

### Q8 revision (Sean's review, 2026-09-21)

"Page" is undeclared vocabulary (the declaration used it once to gloss Document); worse, requiring a Description conflates the record with the reading layer — a Description is curation for reading, not identity. RULED: **Descriptions are advisory polish, not qualification** — an entity with claims + attributes and no Description is Qualified; absence nudges (no-page flag), never gates; the deliberate-unpaged marker work item is DELETED. A Seeded app's entities qualify from birth; empty shells are pre-pipeline residue caught by Q1 (mandatory review makes "Description without claims" unconstructible going forward). Standard is now Q1–Q9 with the Description ruling recorded as a section.

### DELIVERED 2026-09-21 — spec accepted, audit live

All five rulings recorded and the standard finalized (`docs/product/qualified-entity.md`, ACCEPTED):
1. **Q1 floor + no empty Entities**: with claim-backed Attributes, an Entity with a Name is ≥1 Claim; an Entity with literally no associated data should not exist and should not be allowed to exist (populate through a reviewed lane or remove via the audited path — never automatic).
2. **Derived types**: Plans/Encounters/Notes aren't Entities (an Entity is the structured representation of an Identity) but may be extended/derived versions — **the Qualified Entity bar is assumed the floor of these types**; extend upward where the type requires.
3. **Binary** — the point is Migration → Seeded, then never an unQualified Entity again; the Migration-phase surface doesn't care to what degree something is unQualified.
4. Per-criterion reasons = implementation detail (for routing).
5. Attribute minting = its own ticket → **TKT-0143** created (also gates 0137's attribute promotion).

Shipped with the spec:
- **ADR-0017 amendment**: Qualified Entity joins the declared vocabulary (binary, live-computed; Descriptions advisory; derived types floor).
- **Glossary entry** "Qualified Entity" (registry rule; glossary tests 4/4).
- **Audit endpoint** `GET /campaign/qualified-entities` (application/qualified_entities.py + Postgres reads): Q1/Q4/Q6 computed; Q3 pending 0138 and Q5 pending 0143 — reported as pending, never silently passed; Q2/Q8/Q9 structural. Harness 6/6 (new test: zero-claims fails Q1, faction parent_location fails Q4, retired vocabulary value fails Q6, pending statuses asserted, clean entity passes).
- **Live first run**: 120 entities — 53 qualified, 67 unqualified (65× Q1 zero-claims, 6× Q6 retired vocabulary values; sample: Raven King, Far Realm Entity, Ruh... and Catlantis on vocabulary). The Migration→Seeded distance is now a number.

Remaining in 0139: none — definition, vocabulary, and machine-checkable proof all delivered. Mark ready for close review.
