---
id: TKT-0099
title: Lore creation queue with evidence gathering and optional synopsis
status: backlog
priority: P2
milestone: trustworthy-librarian
depends_on: [TKT-0040, TKT-0094]
created: 2026-09-09
updated: 2026-09-09
---

# TKT-0099: Lore creation queue with evidence gathering and optional synopsis

## Outcome

Capture missing campaign entries without interrupting writing. Later, load a queued item in Lore creation, gather relevant library evidence, and review a draft before creating or linking an entry. Deferred at the user's request; this ticket does not authorize implementation or canonical changes.

## Context

An unmatched mention such as Tsunadis can refer to a place already discussed in evidence but lacking its own Location entry. A missing identity is not missing knowledge, and typing a mention must not create canon automatically.

Coordinate with TKT-0040 (Lore creation), TKT-0093 (optional identity links), TKT-0094 (shared retrieval), and TKT-0095 (workflow integration). Reuse shared retrieval rather than building a separate scraper or graph.

## Scope

- Add **Queue for Lore** to the Library **+** menu, allowing a name and optional context to be saved without creating an entity.
- Provide a discoverable **Lore queue** entry point outside the + menu, with a compact pending count, and a queue picker on the Lore creation page. Prefer a Library navigation item or small queue button; settle its exact placement during UI work.
- Offer **Queue for Lore** for unmatched @mentions while retaining **Keep as text**. Preserve the current draft and caret; no forced navigation.
- Persist queued name, originating workspace/document reference, exact surrounding context, timestamps, and optional user notes. Repeated requests must not accidentally duplicate items. Suggest combining matching names, but do not merge ambiguous identities solely by spelling.
- Lifecycle: Queued, Drafting, Resolved; allow Dismiss. Retain context and resolution history. Resume drafts after refresh.
- Load a queued item into Lore creation with its context intact.
- Provide **Gather library evidence** using content search, aliases, and graph relationships. Return bounded, expandable source passages with citations. Keep plans, observed events, and unresolved conflicts distinguishable; graph associations are discovery aids, not proof.
- Allow selection of evidence and an optional, explicit **Draft synopsis** action. AI drafts only from selected evidence, cites its support, preserves uncertainty, and surfaces unanswered questions. Never turn plans into outcomes or assumptions into facts.
- Review/edit the proposed name, type, prose, and evidence before creating through Campaign Core. Alternatively resolve by linking to an existing entry. Mark resolved only after successful creation/linking; failures remain resumable.
- Offer explicit linking of pending mentions after resolution without rewriting original evidence or silently replacing prose.

## Out of scope

- Automatic canonical creation from mentions, queue actions, retrieval, or AI synopsis.
- Broad automatic entity extraction or mandatory subject-predicate-object enrichment.
- External web scraping; this gathers existing campaign-library evidence.
- Creating Tsunadis as part of ticket drafting.

## Acceptance criteria

- [ ] Library + can queue an item; the queue is also accessible without opening that menu.
- [ ] An unmatched mention can be queued without losing the active draft; keeping it as text remains possible.
- [ ] Queue items and drafts survive refresh, with origin/context retained and duplicate submissions handled safely.
- [ ] Lore creation can load, dismiss, resume, and resolve a queued item.
- [ ] Evidence gathering finds relevant passages even when no corresponding entity exists; passages are bounded and expandable.
- [ ] Synopsis generation is opt-in, editable, cited, and non-canonical. Unsupported details and contradictory evidence are not silently reconciled.
- [ ] Creating or linking requires an explicit action through existing Core boundaries; failure cannot falsely resolve the queue item.
- [ ] Suggested mention links require explicit acceptance and preserve original text/provenance.
- [ ] Tests cover lifecycle, duplicate requests, missing identities, conflicting evidence, provider failure, and successful resolution; UI is visually checked at normal and narrow widths.

## Validation plan

Use a sanitized Tsunadis-like example: several source passages mention a place and castle without a location identity. Verify that the workflow gathers those passages, asks about ambiguous identity rather than guessing, and creates nothing until reviewed. Include an existing-identity resolution and refresh/retry tests.

## Implementation sequence

1. Durable queue, Library entry points, and Lore-page loading.
2. Shared evidence gathering and explicit create/link resolution.
3. Optional cited AI synopsis, with visible progress, failure recovery, and existing model settings.

## Documentation

Document the distinction between queued names, non-canonical drafts, and resolved canonical entries, plus unmatched-mention behavior and evidence-selection rules.
