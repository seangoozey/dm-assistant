---
id: TKT-0148
title: Subject resolution at capture promotion — no claim enters canon ownerless
status: in-progress
priority: P1
milestone: trustworthy-librarian
depends_on: []
created: 2026-09-28
updated: 2026-09-28
---

# TKT-0148: Subject resolution at capture promotion — no claim enters canon ownerless

## Context

Sean's ruling (2026-09-28, with the ADR-0020 decision): **ongoing capture — Lore, Brainstorm, Sessions, Encounters — must deal with ownership ASAP, through the Candidate Promotion Pipeline** (subject resolution at promotion review, never a separate later surface). With backward compatibility abandoned, ownerless-claim creation stops being an accepted intermediate state: ADR-0020 makes audit Q3 the permanent ownership guard, and every new orphan would trip it.

Where each surface stands today:

- **Lore**: binds by construction — the created record owns every promoted claim; linked claims re-attribute in the same action. DONE.
- **Brainstorm (free surface)**: per-thought subject resolution is required before commit (existing record or new-record key). DONE.
- **Description**: binds to its entry. DONE.
- **Sessions / Encounters — THE GAP**: the session reviewer commits statements as claims with the subject optional and usually empty. Live evidence: the 2026-08-22 exile-camp session note contributed 11 ownerless claims through the CURRENT flow — every future session note and encounter-note capture mints more unless this lands.

## Ruling alignment (ADR-0021, 2026-09-28)

Sean's ruling makes this ticket the direct implementation of decision 2 for Sessions: "Sessions and Brainstorms are Lore-in-progress interfaces. Until committed, these interfaces generate claims that are unowned. During a commit, they break their proposals into candidates and assign ownership." The session reviewer's statement commit IS the commit where ownership is assigned. Encounter authoring is NOT in this ticket's scope: per ADR-0021 the encounter owns its claims outright with auto-mentions carrying cross-references (its ownership mechanism is ADR-0021's open WIP question).

## Scope

- **Subject resolution in the session-note statement reviewer**: committing a statement requires its subject — resolved through the same deterministic suggestion machinery as the orphan review (co-mentions first, then name-in-text, aliases; word-boundary, apostrophe-tolerant), with the lead suggestion preselected and editable/searchable, plus an explicit "no single record — ambient lore" choice (which files the receipted no-owner disposition rather than a NULL subject).
- **The promotion guardrail**: the pipeline's commit validation refuses a subjectless create_claim decision unless the explicit no-owner choice was made — nothing enters canon ownerless by omission. (This generalizes the 0138 lesson: the August import review accepted empty subjects silently, 218 times.)
- **Default-from-page rule**: when a statement's evidence sits on an entity's own page, the page's entity is the default subject (the failed-migration lesson: Zander's sheet claims promoted subjectless while the page association sat unused).
- Statement review keeps its compact idiom; this adds one decision per statement, preselected — the DM touches only what is wrong.

## Out of scope

- Fixing the existing 182 (TKT-0138's finite cleanup).
- The full session-reviewer re-home onto the unified claim card (TKT-0145, behind 0142) — this ticket lands on the CURRENT reviewer; 0145 carries the same behavior onto the card unchanged.
- Bulk backfill of any kind.

## Validation evidence

### Delivered 2026-09-30 (deployed) — the session reviewer assigns ownership at commit

Sean's go: "start work on 148." The gap this ticket existed for is CLOSED: session statements can no longer mint orphaned claims.

- **Backend — the shared suggestion read**: `application/owner_suggestions.py` (`suggest_owner_matches`: word-boundary, apostrophe-tolerant, longest-first, limit + exclude) — extracted from and now shared with the orphan review (0138's service composes it; one matcher, two consumers — a 0150 down payment). Endpoint `GET /campaign/owner-suggestions?text=&limit=` (DM-only). LIVE: "The Raven King unifies the farmsteads and establishes Ravenholdt." → Raven King (npc), Ravenholdt (location), +1.
- **Backend — the guardrail**: `CreateClaimDecision.owner_disposition` (the explicit no-owner choice); `_validate_claim` refuses a subjectless create_claim without it — "a claim needs its owning record — resolve the subject or choose 'no single record'". Migration **0073**: `claim_owner_dispositions` (immutable, receipt-linked) + `apply_change_set` re-defined so an ambient disposition files its receipt IN the claim's own transaction. Full backend suite green (no legitimate path breaks — replacement/correction flows don't use proposal items).
- **Frontend — the session reviewer** (`directSessionReview` — the statement-by-statement lane; `commitDirectInputClaim` was the literal orphan factory, `commonItem` carried no subject): every statement now shows the **Owning record** decision — lead suggestion PRESELECTED as a chip, other suggestions one click away, searchable (searchEntities typeahead), or **"No single record — ambient lore"** (receipted). Commit disabled until subject-or-ambient + observed date; payload carries `subject_entity_id` or `owner_disposition`. Mentions still ride as `related_entity_ids` (never subjects). Extracted as `SubjectChoiceField` (component-shaped for 0150).
- **Evidence**: backend 3/3 new (matcher ranking/limit/exclude, word boundaries, guardrail refuse + ambient-pass) + full suite; React 86/86 (new: capture → reviewer opens → suggestion preselected → commit gated → payload carries the subject). Deployed; 0073 in the ledger; endpoint + bundle verified live.

**Remaining tail (small, no live producer today)**: the default-from-page rule (evidence on an entity's own page ⇒ default subject) applies when a page-backed capture path exists — the session path's evidence is session notes, so suggestions carry the practical case. Fold into 0138's encounter slice (authored encounter docs are page-backed). Brainstorm/Lore/Description were already compliant by construction. With that fold, this ticket's scope is complete pending Sean's review.
