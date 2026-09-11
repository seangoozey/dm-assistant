---
id: TKT-0082
title: Capture chronological table notes from encounter context
status: done
priority: P0
milestone: trustworthy-librarian
depends_on: [TKT-0038, TKT-0080]
created: 2026-08-26
updated: 2026-08-26
---

# TKT-0082: Capture Chronological Table Notes from Encounter Context

## Outcome

During play, the DM can record what actually happened from any useful place in a prepared encounter without losing their reading position. Notes retain encounter and section context, but the session timeline and assembled session note are ordered by capture time because encounters are not played linearly.

## Scope

- Put a compact note action in the upper-right of every encounter section, including named sub-encounters such as **The Common Fire**.
- Provide an encounter-level note action for events that do not belong to a prepared section.
- Open a lightweight composer without navigating away or changing scroll position.
- Timestamp and autosave drafts immediately to a durable open session run, retaining browser-local fallback storage so refresh or a temporary connection failure does not lose table notes.
- Keep encounter, source document, and stable section identity as hidden context rather than adding it to the claim text.
- Show one session timeline sorted by capture time, independent of encounter document order.
- Allow notes to be corrected or removed before assembly.
- Assemble the timeline into the existing session-note capture workflow in chronological order.
- Append to a new or existing direct-input session note and close the durable run with links to the captured source document and capture receipt.

## Acceptance criteria

- [x] Every rendered encounter section has a small accessible note icon in its upper-right corner.
- [x] The encounter header offers a general note action.
- [x] Adding a note does not navigate or reset encounter/dossier scroll position.
- [x] Captured notes survive refresh and appear oldest-to-newest even when their encounter sections were visited out of order.
- [x] Each note retains encounter and section context without inserting that context into its eventual claim sentence.
- [x] The timeline can seed a new session note using chronological note text.
- [x] Notes remain editable and removable before they become immutable session evidence.
- [x] Focused UI tests and strict typecheck pass.

## Out of scope

- Making scratch notes canonical without the existing session-note review.
- Ordering notes by encounter headings or authored progression.
- AI extraction during live table play.

## Progress

- Deployed the first table-ready vertical slice. Every rendered encounter heading and the encounter itself now expose an unobtrusive note action.
- Notes open in a session-timeline panel without navigation, carry encounter/section context, and persist in browser-local run storage across refreshes.
- Timeline display and session-note assembly sort by capture timestamp, never authored encounter order.
- Notes can be edited or removed before capture. The assembled text can start a new direct-input session note or append to an existing direct-input session note, then follows the established claim-review workflow.
- Added deterministic section keys, focused helper coverage, and a full UI path test.
- Added PostgreSQL-backed open session runs and chronologically ordered notes with encounter, source-document, and stable section provenance.
- Existing browser-local notes migrate into the open run; saves and edits sync optimistically, failed sync remains visible, and deletes roll back locally when the server rejects them.
- Session wrap-up can seed a new note or append to an existing direct-input note. Successful capture closes the run and retains links to the immutable source document and capture receipt.
- The deployed stack accepted migration `0031`; the live open-session endpoint returned HTTP 200. Strict TypeScript, 50 focused UI/Windmill tests, and 5 focused Campaign Core tests pass.
