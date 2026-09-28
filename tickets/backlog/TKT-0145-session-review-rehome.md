---
id: TKT-0145
title: Re-home the session-note reviewer off the shelved phase-1 Migration workspace
status: backlog
priority: P2
milestone: trustworthy-librarian
depends_on: [TKT-0142]
created: 2026-09-22
updated: 2026-09-22
---

# TKT-0145: Re-home the session-note reviewer off the shelved phase-1 Migration workspace

## Context

The phase-1 Migration wizard was shelved behind a Settings flag (2026-09-21, default off) — but the **session-note reviewer still lives on that page**: capture-and-review, the audit's "Open capture — review statements" (routed there 2026-09-22 with the first statement auto-selected), and the legacy proposal review all navigate programmatically to `migration-legacy`. The flows work, but a daily-use surface renting space on a shelved page is debt: the flag can never be removed, and the reviewer can't join the unified claim surface (TKT-0142) while it's welded to the wizard's render tree.

## Scope when taken up

- Build the reviewer as its own surface on the **unified claim card** (0142's component): statement-by-statement review of a session note's pending candidates — the compact session-review idiom (inherited dimensions, observed date, commit-and-continue, skip-with-reason, split) rendered from the claim card's slots, not the wizard's resolution form.
- Routing: capture-and-review, the unpromoted audit's open-capture, and session-note documents with pending candidates all land on the new surface (documents-page context, the note's provenance alongside).
- The phase-1 page then serves ONLY the archived wizard: the Settings flag note retires, and the flag itself becomes "archived tooling" rather than "required for session review."
- Tests: capture flow, audit routing, statement commit/skip/split carried over.

## Out of scope

- The wizard itself (stays shelved as-is).
- Brainstorm WIP lifecycle (TKT-0144).

## Validation evidence

(to record when built)
