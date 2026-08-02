---
id: TKT-0022
title: Implement candidate proposal and approval workflow
status: done
priority: P1
milestone: trustworthy-librarian
depends_on: [TKT-0015, TKT-0021]
created: 2026-08-01
updated: 2026-08-01
---

# TKT-0022: Implement Candidate Proposal and Approval Workflow

## Outcome

Turn explicitly selected import candidates into exact, versioned proposals and scoped approvals that can use the existing atomic change-set application boundary.

## Context

Campaign Core can atomically apply a pre-existing approved change set, but it has no human-facing command API for creating proposal versions, selecting candidate evidence, approving exact items, rejecting/defering candidates, or constructing the allowed mutation payload.

Read `docs/product/invariants.md`, `docs/product/truth-state-authority.md`, `docs/architecture/campaign-core-schema.md`, `docs/architecture/workflows.md`, TKT-0015, and TKT-0021.

## Scope

- Create a proposal from exact candidate IDs and explicit target/entity decisions.
- Render an immutable proposal version with content hash, evidence, intended mutations, and candidate dispositions.
- Add typed commands for reject, defer, revise, and exact item-scoped approval.
- Construct only allowlisted `create_entity` and evidence-backed `create_claim` mutations initially.
- Apply through the existing idempotent change-set operation and update candidate review status transactionally.

## Out of scope

- Automatic approval or bulk promotion.
- Inferring entity identity from name similarity.
- Promoting templates, navigation indexes, quarantine items, or planning material as established truth.
- Language-model-authored proposal content.

## Acceptance criteria

- [x] Proposal creation binds exact candidate IDs, evidence revisions, target decisions, and an immutable version hash.
- [x] A later edit invalidates approval of the earlier unapplied version.
- [x] Approval names explicit proposal items; inspecting or approving one never approves siblings.
- [x] Reject and defer commands change review disposition without mutating canonical truth.
- [x] Apply remains one atomic, auditable, idempotent Campaign Core transaction.
- [x] Candidate evidence is linked to every resulting canonical claim.
- [x] Planning, PC-agency, future-date, conflict, and suspected-retcon rules fail closed.

## Implementation

- Added DM-only typed create, read, revise, approve, reject, and defer operations for imported candidates. Requests name exact candidate and evidence revision IDs plus explicit immutable targets; no entity matching or proposal prose is inferred.
- Proposal construction creates an immutable source span, copies the selected candidate assertion into evidence-backed claim payloads, and hashes the complete ordered version. Only allowlisted `create_entity` and `create_claim` mutations are constructed.
- Added migration `0004_candidate_proposals.sql` with separate candidate review status, immutable proposal-candidate evidence bindings, immutable disposition history, the `import_review` workflow kind, and transaction-bound applied-status reconciliation.
- Revisions create new immutable rows and revoke older unapplied approvals. Approval requires explicit item IDs from the current displayed version and creates the existing version-bound change set; canonical application still has no route around `apply_change_set`.
- Deterministic construction rejects removed or evidence-only candidates, excluded classifications, missing or duplicate identities, disallowed authority/state transitions, invalid observation and future times, PC-agency violations, and existing subject/predicate conflicts or possible retcons. Planning and brainstorm evidence cannot be promoted as established truth in this ticket.
- Candidate reads expose source lifecycle status separately from review status, including a review-status filter for the React slice.

## Validation evidence

- The full repository gate against disposable PostgreSQL 16.14 passed with 123 tests and one environment-dependent skip. The same run passed Ruff, strict mypy over 41 source files, 10 React tests, strict TypeScript, all 38 retrieval cases, Compose/test-stack/Windmill policies, and the raw-app build.
- Four PostgreSQL proposal integration tests use the sanitized 17-file import corpus. They prove exact evidence/span linkage, partial scope isolation, cumulative scoped completion, claim provenance, stale approval invalidation, reject/defer isolation, and fail-closed planning, future-time, PC-agency, and possible-retcon behavior.
- The ordinary repository gate passed with 107 tests and 17 intentional PostgreSQL-environment skips, plus every non-database gate.
- The preserved development stack rebuilt successfully, applied the additive migration, and remained healthy. Aggregate smoke checks found all 405 live-shape candidates still pending, zero applied candidates, five proposal/disposition paths, and printed no private assertions.
- `git diff --check` passed. The disposable PostgreSQL container and its exact anonymous volume were removed after validation.

## Migration and rollback

Migration `0004` is forward-only and additive. The prior application can ignore the new workflow enum value, candidate review column, bindings, disposition table, and trigger; application rollback deploys the prior image without deleting them. Schema recovery, if ever required, restores a tested logical backup into a new database rather than deleting proposal evidence or disposition history. No live candidate or canonical row was promoted during deployment.

## Follow-up

TKT-0023 can now build the single-item React review path over these typed commands. It must keep target resolution and item selection explicit, display the immutable version/hash before approval, and never add bulk or implicit confirmation.
