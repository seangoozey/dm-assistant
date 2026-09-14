---
id: TKT-0108
title: Faction roles with unique leadership seats
status: in-progress
priority: P1
milestone: shared-campaign-knowledge
depends_on: [TKT-0106]
created: 2026-09-13
updated: 2026-09-13
---

# TKT-0108: Faction roles with unique leadership seats

## Context

Membership records (migration 0054) carry an unused `role_title` column. Sean ruled that factions need explicit role assignment: select an existing role or create a new one, per member. The Inquisitors expose the core distinction: all members hold Role: Inquisitor (many holders), but exactly one holds Grand Inquisitor. Sean's proposal, accepted as the design: **leadership roles are unique within the faction and marked with a legend star (★)** in the UI. Roles also serve identity assignment downstream (a faction role title is a strong resolution hint for honorific surfaces, and gives graph member edges semantics), but those payoffs are follow-ups — this ticket is the catalog, the audited assignment, and the UI.

## Design (agreed with Sean 2026-09-13)

- **Faction-scoped role catalog** (`faction_roles`): faction, name (case-insensitively unique per faction), `is_leadership` flag, created-by-decision. One flag carries both meanings: leadership = unique holder + ★. A role can exist with **no current holder** (a vacant seat survives member removal).
- **Define-on-assign**: roles come into existence through assignment. `is_leadership` is honored only at creation; an existing role's definition is never silently flipped by a later assignment.
- **Assignment** supersedes the member's current membership row and inserts a new one carrying the role (role history rides the existing supersession chain — "who held Grand Inquisitor when" is answerable from the audit trail). Clearing a role supersedes to a role-less row; the member stays on the roster.
- **Uniqueness refusal, never silent transfer**: assigning a leadership seat held by another member is refused with a named error ("held by X — change or clear their role first"). Succession is two explicit audited decisions. All rules live in the migration-owned DB function; idempotent on key replay.
- **UI**: Members block rows become "Name — Role" (★ on leadership) with a per-row role control: select existing role (leadership ones starred, vacant seats selectable), "New role…" (name + Leadership checkbox), or "No role". Refusals surface as red notices. Legend under the block header: "★ unique leadership seat".

## Implementation scope

1. Migration 0055: `faction_roles` + `apply_role_decision` (decision-first insert so role and membership rows reference their receipt; any failure rolls back atomically). Decision kind stays `membership` with `details.action` `assign_role`/`clear_role` — roster ops stay one audit family.
2. Core: `RoleDecision` model + `PostgresIdentityQueueRepository.role()` + `POST /identity/decisions/role`.
3. Library projection: `members` becomes structured `{member_id, name, role_title, is_leadership}`; detail entries gain the faction's role catalog (`roles` with holder names, vacant included).
4. UI: role chips + ★, per-row assign/clear control with select-or-create, legend, red error notices; backend op + client methods.
5. Tests: docker integration (define-on-assign, unique refusal with named holder, succession, vacancy, history via supersession, replay, non-member refusal, case-insensitive dedupe) + React (assign existing, create leadership, refusal notice, clear, structured members).

## Out of scope

- Atomic "transfer" succession action (add later if succession is frequent).
- Role flag changes after creation (leadership flips) — explicit re-create if ever needed.
- Identity-queue role hints and graph bundle role-labeled edges (follow-ups noted in TKT-0106/0107 track).
- Auto-suggested roles from claim text (auto-association remains future work per Sean's standing ruling).

## Validation evidence (2026-09-13, deployed)

- **Docker integration** (`tests/test_identity_queue_postgres.py::test_faction_role_decisions`): define-on-assign (leadership + shared), case-insensitive reuse keeping catalog casing, structured Library members with role_title/is_leadership, roles catalog with holder lists, leadership refusal naming the current holder, restate refusal, clear-without-role refusal, explicit succession (clear → successor seated), prior seats retained on the supersession chain, idempotent replay, non-member refusal, and vacancy after holder removal. Full docker suite **527 passed** (includes updated members-shape assertions in `test_membership_roster_decisions` and `test_entity_profiles_postgres.py`).
- **React** (85 passed, `tsc --noEmit` clean): `seats a member in an existing faction role and surfaces leadership refusals` (star chip, legend, red alert with Core's named refusal, successful seating after refresh) and `creates a new leadership role from the roster control` (New role… → name + Leadership ★ → Assign → chip after refresh); roster-refresh test updated for structured members.
- **Live verification**: migration `0055_faction_roles` applied to the live DB (`campaign_schema_migrations`); app healthy (200); Carpet Rollers editor renders the "★ unique leadership seat" legend, per-member role selects (No role / New role… while the catalog is empty), and the new-role form (name input, Leadership ★ checkbox, Assign disabled until named, Cancel). No role decisions were made against live data — role seating is the DM's call. Roster count differences observed live (8→5 current members) are Sean's own audited removals through the UI, with proper supersession rows.
- Pending: Sean's visual acceptance and real role seating (e.g., Inquisitors: Inquisitor shared role + Grand Inquisitor seat).
