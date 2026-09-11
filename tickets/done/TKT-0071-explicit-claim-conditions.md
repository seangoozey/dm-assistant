---
id: TKT-0071
title: Replace ambiguous conditional flags with explicit claim conditions
status: done
priority: P0
milestone: trustworthy-migration
depends_on: [TKT-0031]
created: 2026-08-13
updated: 2026-08-13
---

# TKT-0071: Replace Ambiguous Conditional Flags with Explicit Claim Conditions

## Outcome

`conditional` means that a committed consequence is gated by a stated trigger. It does not describe a possibility, supposition, or uncertain plan that merely contains prerequisite language. Uncertain plans continue to be represented by truth state, authority, lifecycle, and agency boundaries.

## Scope

- Define a condition as an explicit trigger paired with the consequence that follows when it is satisfied and, when possible, a reference to another claim, event, plan, or entity.
- Replace or augment the bare `is_conditional` Boolean with nullable condition details.
- Preserve existing Boolean values for audit and migration compatibility.
- Document the distinction between uncertainty, planning state, agency, and prerequisite conditions.
- Normalize legacy records only through reviewed migrations; do not infer missing conditions.

## Acceptance criteria

- [x] `possible/brainstorm` claims cannot be conditional; a supposition layered on a possibility remains only a possibility.
- [x] Merely using words such as "if," "may," or "might" does not make a claim conditional.
- [x] A claim is conditional only when it records a committed consequence that follows upon a concrete trigger.
- [x] Conditional claims require nonempty trigger text or a valid trigger reference.
- [x] "Ruhrogue may lead the coalition if the nations accept his leadership" remains `possible/brainstorm`, not conditional.
- [x] "Ruhrogue will lead the coalition when he gains the signatures of the five lords" is conditional, with obtaining those signatures as its trigger.
- [x] PC agency is enforced independently from condition semantics.
- [x] Existing records remain readable and auditable.
- [x] API, schema, UI vocabulary, tests, and documentation use the same definition.

## Out of scope

- Automatically determining whether a condition has become true.
- Predicting player choices.
- Rewriting existing source documents.

## Validation evidence

- Added migration `0021_explicit_claim_conditions.sql`, including explicit trigger storage and apply-time enforcement.
- Proposal API and persistence now carry trigger text and optional typed references.
- Migration UI prevents possible claims from being conditional and requires a concrete trigger for committed conditional claims.
- Repository validation passed: 288 backend/acceptance tests passed (26 skipped), 33 React tests passed, Ruff, mypy, TypeScript typecheck, Windmill raw-app build, and 38 retrieval tests.
- Local test stack rebuilt and deployed; Windmill and Campaign Core are healthy, and PostgreSQL reports `claim_conditions` present.
