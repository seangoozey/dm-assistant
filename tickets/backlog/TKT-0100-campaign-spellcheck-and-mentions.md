---
id: TKT-0100
title: Shared spellcheck, campaign dictionary, and automatic mention suggestions
status: backlog
priority: P2
milestone: trustworthy-librarian
depends_on: []
created: 2026-09-09
updated: 2026-09-09
---

# TKT-0100: Shared spellcheck, campaign dictionary, and automatic mention suggestions

## Outcome

Provide consistent spelling assistance and campaign-name linking across natural-language text entry, without interrupting writing or silently changing text or canon.

## Context

Browser spelling support alone does not provide the app's shared campaign vocabulary or record linking. Users need ordinary spelling corrections alongside accurate fantasy names, aliases, and their own dictionary words. Reuse existing mention identity lookup and coordinate unmatched-name handling with TKT-0099 (Lore creation queue).

## Scope

- Inventory natural-language input surfaces and apply one reusable integration to session notes, brainstorms, Lore creation, encounter notes, editable claims, character backgrounds, and other prose/title fields.
- Maintain a persistent campaign-scoped dictionary seeded from canonical names and aliases, plus user-added words. Provide a manageable list for adding/removing custom words; identity-derived vocabulary remains tied to its record rather than becoming stale independent copies.
- Underline suspected spelling errors and offer ordinary spelling corrections and relevant campaign-name suggestions inline.
- Recognize multiword names, punctuation, apostrophes, and aliases, including names such as Ishi'go'dan. Do not fragment valid names into repeated false errors.
- Offer explicit actions: Correct spelling, Link entry, Ignore once, and Add to dictionary. Dictionary acceptance is not entity identity confirmation.
- Suggest mentions for recognized names without requiring @. Keep existing explicit @ completion available. Ambiguous matches require a choice; no silent entity creation, name replacement, or linking.
- Preserve caret/selection, undo/redo, composition input, multiline formatting, and draft text. Support keyboard navigation and accessible suggestion controls with strong contrast and viewport-contained positioning.
- Keep typing responsive for long notes; avoid full-document blocking work on each keystroke. Do not trigger paid AI calls or send text to external spelling services as part of ordinary typing.
- Evaluate browser-native versus application-managed spelling during implementation. Do not assume browser dictionaries can be controlled by the app. Avoid duplicate/conflicting native and custom overlays, and verify both Chrome and the in-app browser.

## Boundaries and exclusions

- No corrections to immutable source evidence; changes to committed claims use the existing audited editing workflow.
- No automatic canonical mutation from spelling acceptance, dictionary updates, or mention suggestions.
- Exclude IDs, URLs, dates, code, numeric fields, and other structured inputs from prose spellchecking.
- No grammar rewriting, stylistic rewriting, or generative text completion in this ticket.
- No new external provider or dependency without documenting privacy, licensing, size, and deployment implications.

## Acceptance criteria

- [ ] All inventoried natural-language entry surfaces use the shared spelling behavior; structured fields are excluded.
- [ ] Canonical names, aliases, and custom words are accepted consistently and dictionary changes persist across reloads.
- [ ] Misspellings offer usable ordinary and campaign-name corrections, including punctuation and multiword names.
- [ ] Correct, ignore-once, and dictionary actions do not unexpectedly submit forms, move the caret, or discard text; undo works.
- [ ] Names can be explicitly linked without @; ambiguous names require selection and unlinked text remains valid.
- [ ] Recognition never silently replaces text, creates an entity, or changes truth state.
- [ ] Existing @ mention selection and keyboard behavior continue to work.
- [ ] Long drafts and IME composition remain responsive; spelling does not generate paid/provider requests.
- [ ] Chrome and the in-app browser receive keyboard and visual verification, including narrow layouts and suggestion contrast.
- [ ] Committed-claim edits retain the normal audit trail and original source evidence stays unchanged.

## Implementation sequence

1. Inventory editors; choose and document a local spelling approach; add campaign dictionary and explicit spelling correction.
2. Add automatic name recognition and explicit mention-link suggestions on the same shared integration.

## Validation plan

Use fixtures for ordinary misspellings, Ruhrogue-like near matches, Ishi'go'dan, multiword locations, aliases, ambiguous names, custom words, and long notes. Exercise caret restoration, undo/redo, IME, refresh persistence, and dictionary removal. Verify network behavior and that no canonical mutation occurs without the existing explicit workflow.

## Documentation

Document dictionary scope and management, spelling versus identity linking, supported/excluded fields, privacy behavior, and browser differences. Implementation is deferred; this ticket records approved scope only.
