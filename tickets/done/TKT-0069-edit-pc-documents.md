---
id: TKT-0069
title: Edit curated PC pages from Documents
status: done
priority: P1
milestone: campaign-content-manager
depends_on: [TKT-0068]
created: 2026-08-12
updated: 2026-08-12
---

# TKT-0069: Edit Curated PC Pages from Documents

## Outcome

The DM can edit a PC's curated profile and player-authored background directly from its Documents page without editing derived real-play summaries or weakening source provenance.

## Scope

- Editable PC profile fields: canonical name, player, race, sex, status, and aliases/former names.
- Editable intact background/biography with its existing source identity and revision history preserved.
- Read-only real-play facts sourced from session notes.
- Separate links or actions for player plans and conditional DM plans; they are not rewritten as biography text.
- A clear dirty state, validation errors, cancel action, and exact before/after review before saving.
- Audited, idempotent writes through Campaign Core rather than direct browser, Windmill, database, or live-share mutation.

## Acceptance criteria

- [x] PC Documents pages expose an explicit Edit action; ordinary viewing remains read-only.
- [x] Player, race, sex, status, aliases, and background can be edited independently.
- [x] Required fields are validated before review.
- [x] Missing race or sex can remain explicitly unrecorded and is never inferred.
- [x] Saving presents the complete, versioned before/after change and requires one exact confirmation.
- [x] Campaign Core rejects stale source/profile versions and returns an actionable conflict.
- [x] The profile mutation is transactional, idempotent, and produces an auditable receipt.
- [x] Original source text, path, hashes, revisions, and prior values remain recoverable.
- [x] Current Status and other derived summaries cannot be edited as canonical PC facts.
- [x] Real-play facts remain linked to their authoritative session evidence.
- [x] Player plans and DM plans remain separate record workflows with their knowledge boundaries intact.
- [x] The UI reports success, validation failures, stale edits, and service failures persistently.
- [x] Tests cover the versioned storage and exact profile/biography edit flow.

## Architecture notes

Implemented as a Campaign Core-owned, versioned curated overlay on the read-only imported source. It never writes back to the live Starfall share. Every save is tied to the exact source revision from which the editable profile originated.

## Out of scope

- Generic Markdown editing for every document type.
- Editing session notes from the PC page.
- Automatically generating or rewriting biographies.
- Inferring race, sex, relationships, facts, or plans from prose.
- Building a general schema designer.

## Validation evidence

- Repository validator: 286 passed, 26 skipped.
- React: 31 tests passed, strict typecheck passed, Windmill raw-app build passed.
- Ruff, mypy, compose policy, lifecycle policy, Windmill source policy, and retrieval corpus passed.
