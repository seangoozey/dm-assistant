---
id: TKT-0024
title: Perform the first scoped live canonical promotion
status: done
priority: P1
milestone: trustworthy-librarian
depends_on: [TKT-0020, TKT-0023]
created: 2026-08-01
updated: 2026-08-01
---

# TKT-0024: Perform the First Scoped Live Canonical Promotion

## Outcome

Use the completed review workflow to promote a deliberately small, representative set of live Starfall evidence and prove that Ask returns grounded, cited answers without leaking non-canon material.

## Context

This is an operational acceptance exercise, not a bulk migration. It demonstrates the complete source-to-receipt-to-retrieval path before expanding canonical coverage.

Read `docs/product/invariants.md`, `docs/product/truth-state-authority.md`, `docs/testing/retrieval-harness.md`, TKT-0012, TKT-0020, and TKT-0023.

## Scope

- Take a logical pre-promotion backup of the development Campaign database.
- Select a minimal representative entity/fact set with unambiguous durable or observed evidence.
- Review every selected source span and resulting proposal item in the UI.
- Approve and apply only that visible proposal version.
- Verify receipts, idempotent retry, grounded retrieval, exact citations, visibility, and non-canon exclusion.

## Out of scope

- Bulk approval of the import queue.
- Campaign-bible promotion.
- Resolving ambiguous identities, possible moves, retcons, or conflicts as part of the happy-path proof.

## Acceptance criteria

- [x] The selected scope and exclusion rationale are recorded without committing private prose.
- [x] A pre-promotion backup and non-destructive recovery path are verified.
- [x] Every mutation has reviewed evidence and one exact item-scoped approval.
- [x] One receipt records the atomic canonical change and an exact retry creates no duplicates.
- [x] Ask returns the promoted facts with exact citations and appropriate visibility.
- [x] Nearby brainstorm, preparation, unresolved, and unrelated candidates do not appear as established support.
- [x] Any discovered ambiguity becomes a follow-up review item rather than silently expanding scope.

## Operational record

Campaign Core retained the new entity's type, and TKT-0026's complete comparison fix is implemented, tested, and deployed. The user had already explicitly approved and applied the exact two-item proposal in the UI before the fix deployed; this record treats those direct UI actions as authoritative and does not infer approval from conversational shorthand.

### Backup and recovery

- Before proposal creation, a PostgreSQL custom-format archive was created from the development Campaign database and copied outside Git to `C:\Users\Sean\Documents\DM Assistant Backups\2026-08-01-tkt24\campaign-prepromotion.dump`.
- `pg_restore --list` parsed the archive successfully. The archive was then restored with `--no-owner` into a newly created isolated database rather than over the live database.
- The restored baseline contained zero entities, zero claims, zero relationships, and 405 import candidates, matching the expected pre-promotion state. A scalar connection check also succeeded.
- The exact temporary restore-check database was removed after verification. Recovery remains non-destructive: restore this archive into a new database, validate it, and repoint Campaign Core only after review; never overwrite or drop the current database as a rollback shortcut.
- The archive size and SHA-256 were verified after copying, but the hash and dump bytes are intentionally not committed.

### Selected scope and exclusions

- Scope is exactly one pending `explicit_lore` / `established` / `dm_only` candidate from a durable-evidence location document's canon-summary section.
- The exact evidence span was reviewed in the deployed UI and matched the candidate. The proposal contains exactly one new location entity and one `is_continent_of` claim bound to that evidence revision.
- A source-level unresolved-link review remains open for the document. It does not overlap or alter the selected span and is neither resolved nor promoted by this exercise.
- All sibling candidates, preparation, brainstorm/planning material, quarantine, unrelated explicit lore, and unresolved-link content are excluded. No private excerpt, proposal UUID, receipt ID, or source hash is committed here.
- Before proposal creation, the scoped Ask query returned `insufficient_evidence`: all 15 visible matches were context-only and none could support an established answer.

### Applied proposal and retrieval proof

- Campaign Core created immutable proposal version 1 with exactly two selected items: one location entity and one established explicit-lore claim. The user explicitly approved both selected items and then explicitly applied the approved change in the deployed UI.
- Campaign Core issued one applied receipt covering two items. Canonical totals became one entity, one claim, and zero relationships; exactly one candidate became applied.
- Replaying the exact approved application returned the same receipt with `idempotent_replay: true`. Totals remained one entity, one claim, zero relationships, one receipt, and two change-set items.
- The same scoped Ask question changed from the recorded context-only baseline to `answer`. Its sole support evidence is the established explicit-lore claim with the exact durable-source canon-summary citation.
- A party requester receives `restricted` with no evidence or citations because the promoted claim is `dm_only`.
- The scoped answer contains no preparation, brainstorm/planning, unresolved-link, quarantine, sibling, or unrelated support. The pre-existing source-level unresolved-link review remains open rather than being silently resolved or expanded into this promotion.
- TKT-0026 adds the missing entity-type and consequential claim-field comparison. Its source is deployed with zero workspace drift and the reopened app is stable. Closing the stale Codex browser tab discarded Windmill's session-only historical proposal view, so the already-applied proposal was not recreated merely to obtain another screenshot.

### Final validation

- The reopened deployed app reports 404 remaining queue results, one fewer than the 405 pre-promotion candidates, consistent with exactly one applied candidate being excluded from the default pending queue.
- Full repository validation passes: 107 Python tests passed, 17 environment-dependent tests skipped, 18 React tests passed, strict TypeScript and raw-app builds passed, and all 38 retrieval fixtures validated.
- No migration was introduced. Recovery remains the verified non-destructive restore procedure above; the pre-promotion archive remains outside Git.
