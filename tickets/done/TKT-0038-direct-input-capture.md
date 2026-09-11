---
id: TKT-0038
title: Direct input capture and evidence-backed candidates
status: done
priority: P1
milestone: trustworthy-librarian
depends_on: [TKT-0035]
created: 2026-08-04
updated: 2026-08-27
---

# TKT-0038: Direct Input Capture and Evidence-Backed Candidates

## Outcome

A DM can submit free-text thoughts or observations directly through Campaign Core (no Markdown file), producing an immutable synthetic source revision and candidates that flow through the same extraction and review pipeline as imported evidence.

## Context

The importer is source-file-only. The primary experiences (Brainstorm, Lore Entry, Real Play) all need to capture text that a human types in the moment. This ticket builds the direct-input source and candidate path on top of the assertion pipeline (TKT-0035).

Read `docs/migration/markdown-importer.md`, `docs/architecture/campaign-core-schema.md`, and TKT-0035.

## Scope

- A direct-input source document and revision type: the submitted text is the immutable evidence, with provenance marking it as direct capture (not file import).
- A `/capture` endpoint accepting text, classification, and visibility, producing the source revision and candidate(s) through the assertion pipeline.
- The candidate read model surfaces direct-input candidates alongside imported ones.
- No canonical mutation; promotion remains the existing proposal path.

### First vertical slice: session notes

- Add a Library input surface for a dated, titled session note with manicured free text.
- Capture the separate in-game date and persist the last submitted value as the default for the next note; never confuse it with the real-world session/audit date.
- Preserve the submission verbatim as a `direct_input` source revision with a stable session-note identity.
- Default the capture to `real_play_evidence`, `observed`, `real_play`, and `dm_only`.
- Create one evidence-backed candidate per non-empty note line, preserving each line's exact source span, and open the first directly in the existing review workflow.
- Resolve `@` mentions for PCs, NPCs, and locations through entity search; store the selected stable entity IDs and exact mention spans in immutable revision metadata without forcing a claim subject or other semantic role.
- Split non-empty note text deterministically at sentence boundaries so ordinary multi-sentence notes become individually reviewable statements without AI.
- Give direct session notes a compact batch reviewer that hides migration/extraction diagnostics, inherits the full campaign date, verifies and applies an exact claim in one action, and advances to the next statement.
- Persist mentioned entity IDs as `mentioned` claim associations so claims surface on related records without inventing subject/predicate/object roles.
- Show captured notes alongside imported session notes; provenance must clearly distinguish direct capture from Markdown import.
- Editing or adding to an already captured session creates a new immutable revision rather than rewriting evidence.

## Out of scope

- The Brainstorm, Lore Entry, or Real Play workflow experiences (TKT-0039, TKT-0040, or a future ticket).
- Audio capture or transcription.
- Batch or bulk capture.
- AI extraction and automatic canonical application in the first session-note slice. These can follow once exact capture, review handoff, and revision behavior are reliable.

## Acceptance criteria

- [x] A direct-input submission creates an immutable source revision preserving the exact submitted text.
- [x] The submission produces candidates through the assertion pipeline (TKT-0035).
- [x] Direct-input provenance distinguishes captured text from file-imported evidence.
- [x] No direct-input path creates canonical entities, claims, or relationships before explicit review.
- [x] The candidate read model includes direct-input candidates.
- [x] Sanitized tests and full repository validation pass.
- [x] A DM can enter a session date, title, and note in the Library and immediately continue to its candidate review.
- [x] Each deterministic statement becomes a separate reviewable candidate in source order with exact offsets into the immutable note.
- [x] Selecting an `@` autocomplete result binds the mention to a stable PC, NPC, or location ID while retaining readable note text.
- [x] Related records are de-duplicated and attached only to split claims that name them, independently of grammatical roles.
- [x] Direct-note review shows the full inherited campaign date and keeps evidence internals behind a disclosure.
- [x] AI extraction and the six-step migration workflow are absent from the default direct-note review path.
- [x] Reopening a captured session shows its stored title and latest revision while retaining prior submitted revisions.

## Progress

- Captured session notes now render as session records rather than generic source documents. The list and entry header use the stored title instead of a filename-derived `SOURCE / Untitled entry` fallback.
- Session-note corrections retain the stable capture identity and create a new immutable source revision.
- Commit, skip, stale-proposal recovery, claim-specific mention association, and final-review navigation have regression coverage.
- Session-run scratch writes are explicitly separated from canonical campaign mutations, and canonical claim replacement remains migration-owned.
- Repository validation passes: 304 Campaign Core tests, 60 React tests, strict type checks, Windmill raw-app build, and 38 retrieval cases.

## Validation plan

- Capture a synthetic thought and verify the source revision, candidate, and provenance.
- Confirm zero canonical mutation from capture alone.
