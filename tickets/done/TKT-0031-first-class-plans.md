---
id: TKT-0031
title: Add first-class plans with explicit agency and lifecycle boundaries
status: done
priority: P1
milestone: trustworthy-librarian
depends_on: [TKT-0029]
created: 2026-08-02
updated: 2026-08-02
---

# TKT-0031: Add First-Class Plans with Explicit Agency and Lifecycle Boundaries

## Outcome

Add stable, referenceable plan records for campaign-development direction, in-world actor plans, and player-communicated plans without treating any plan as an observed outcome or predicting a PC's actions.

## Model

- Use the common record identity and kind registry established by TKT-0029.
- The minimal `plan_kind` vocabulary is `campaign_direction`, `in_world_plan`, and `player_plan`.
- `campaign_direction` is DM-only guidance for campaign development.
- `in_world_plan` is authored by the DM and owned by an NPC or faction. The owner relationship distinguishes NPC and faction plans without duplicating kinds.
- `player_plan` records only what a player communicated, with source and time. It is nonbinding evidence, not knowable intent and not a forecast of PC action.
- The lifecycle vocabulary is `active`, `completed`, `failed`, `abandoned`, and `superseded`.
- A lifecycle transition cannot itself prove an outcome. Completion or failure requires separate observed evidence and appropriate claims.
- Plans may have typed owners, targets, objectives, dependencies, intended outcomes, related plans, visibility, provenance, and evidence.
- Truth states remain on claims and relationships, not on the plan record itself.

## Scope

- Add plan storage, constraints, proposal/apply behavior, and real foreign-key relationships to other records.
- Document plan-kind selection, ownership, visibility, lifecycle transitions, and the distinction between intention, projection, and observed fact.
- Support cross-document references to the same named plan and relationships between plans.
- Permit explicitly labeled projections only when grounded in a recorded DM-authored NPC or faction plan.
- Display player plans as attributed, time-bound, revocable context and never as a PC's true intention.
- Add review UI, retrieval filters, migrations, and sanitized vertical-slice tests.
- Include a sanitized example of a named villain plan related to a separate larger plan, with mechanism and promised outcome, to prove that such material is neither `worldbuilding` nor `campaign_direction` merely to fit the schema.

## Out of scope

- Automated planning or AI-generated plan creation.
- Predicting, prescribing, or filling in PC actions.
- Treating a plan or lifecycle transition as evidence that its intended outcome occurred.
- Calendar-neutral date representation, owned by TKT-0030.
- General-purpose workflow/project management.

## Acceptance criteria

- [x] Plans have stable record IDs and can be referenced by documents, evidence, claims, and other records with enforced referential integrity.
- [x] Only the three approved plan kinds are accepted; NPC-versus-faction ownership is represented by the owner relationship.
- [x] Only the five approved lifecycle states are accepted, with reviewed and receipted transitions.
- [x] `campaign_direction`, `in_world_plan`, and `player_plan` have clear inclusion rules, exclusions, examples, and counterexamples.
- [x] A player plan preserves attribution, source, and time but cannot authorize a PC prediction or establish future behavior.
- [x] NPC/faction projections cite an explicit in-world plan, remain labeled as projections, and cannot establish outcomes.
- [x] Completed or failed plans require separate observed evidence for claims about what occurred.
- [x] The sanitized named-plan example can be referenced from multiple documents and related to another plan without duplicating identity.
- [x] Proposal comparison shows plan kind, owner, knowledge boundary, lifecycle, visibility, relationships, and evidence before approval.
- [x] Migration, rollback, backend, retrieval, and React tests pass with validation evidence recorded.

## Follow-up work

- Ticket AI-assisted planning only after this human-controlled model has demonstrated reliable proposal, review, and lifecycle behavior.

## Implementation notes

- Added accepted ADR-0006 and the controlled plan-kind, lifecycle, and knowledge-boundary domain vocabulary.
- Migration 0008 adds typed plan storage, stable shared record IDs, real owner/evidence/related-plan/claim foreign keys, immutable lifecycle history, and kind-specific database constraints.
- Plan creation and lifecycle changes use immutable proposals, exact item approval, the sole canonical change-set apply boundary, idempotent receipts, and stale-state rejection.
- Player plans require a PC owner, player attribution, communication time, and source evidence. Campaign direction cannot acquire an owner, and in-world plans require an NPC or faction owner.
- Completed or failed transitions require separately stored `observed` claims. Projection context is emitted only for active evidence-backed in-world plans, is labeled `projection`, and explicitly cannot establish an outcome.
- The React/Windmill Plans workspace lists and filters plan records, creates exact plan and lifecycle proposals, displays complete before/after coordinates, and requires typed approval before application.
- Migration 0008 is expand-only. Rolling the application back to the prior version leaves its new tables and registry rows unused and does not invalidate earlier data or receipts; destructive rollback would use the documented logical-backup restore procedure.

Validation completed:

- Ruff passed.
- mypy passed for 49 source files; Windmill mypy passed.
- Campaign Core isolated repository validation: 116 passed, 25 skipped.
- Campaign Core full disposable PostgreSQL suite: 140 passed, 1 skipped.
- React/Vitest: 20 passed; strict TypeScript passed.
- Windmill raw-app validation and production bundle passed.
- Retrieval acceptance corpus: 38 cases validated.
- Full deterministic repository validation passed.
