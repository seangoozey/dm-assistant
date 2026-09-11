---
id: TKT-0085
title: Add searchable pinned context and entity mentions to Brainstorm
status: done
priority: P0
milestone: planning-workspace
depends_on: [TKT-0039, TKT-0081]
created: 2026-09-05
updated: 2026-09-05
---

# TKT-0085: Add Searchable Pinned Context and Entity Mentions to Brainstorm

## Outcome

A DM can verify names, retrieve campaign records, and keep important context visible without leaving an active Brainstorm or losing the current thought.

## Scope

- Reuse the session-note caret-positioned `@` mention interaction in the Brainstorm composer.
- Preserve stable entity IDs and exact mention offsets separately from visible thought text.
- Add canonical-library search to the continuity panel with alias-aware name lookup.
- Open a selected result in an in-place, closable dossier without navigating away from Brainstorm.
- Pin and unpin entities in a durable, session-scoped context section above automatic suggestions.
- Include pinned entity names in subsequent grounded continuity retrieval without promoting or altering canon.

## Out of scope

- Mentioning uncommitted candidates or source documents.
- Creating entities from the autocomplete menu.
- AI-generated summaries or claims from pinned records.
- Global pins shared between brainstorm sessions.

## Acceptance criteria

- [x] `@` autocomplete appears at the caret, supports keyboard selection, inserts the canonical name plus a trailing space, and preserves focus.
- [x] Captured thoughts retain verbatim text plus validated stable mention metadata.
- [x] Search finds canonical names and aliases without leaving Brainstorm.
- [x] Search and continuity cards can open and close a dossier without losing the thought draft or page position.
- [x] Pin order is durable for the active Brainstorm and pinned records appear above automatic suggestions.
- [x] Pinning supplies explicit context to later continuity retrieval but never changes campaign truth.
- [x] Sanitized service, PostgreSQL, React, and repository validation pass.

## Migration and rollback

Add an append-only thought mention JSON column and mutable session-context pin rows. Rolling back application code may leave these additive structures unused; no canonical record or evidence deletion is required.

## Validation plan

- Service tests for mention validation, pinned-query context, and idempotency.
- PostgreSQL tests for durable ordered pins and thought mention round trips.
- React tests for caret completion, search, pinning, dossier preservation, and continuity refresh.

## Completion evidence

- Repository validation: 314 Python tests passed, 35 environment-specific tests skipped, 67 React tests passed, strict TypeScript and Windmill raw-app build passed.
- Isolated PostgreSQL validation: 6 candidate-proposal/Brainstorm integration tests passed, including pin and mention persistence after resume.
- Live Windmill verification: alias-capable search returned Romulus, the dossier opened immediately in the continuity panel, and closing it preserved the active Brainstorm without changing campaign data.
