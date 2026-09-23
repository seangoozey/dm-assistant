---
id: TKT-0101
title: Mention and navigate to any library entry
status: backlog
priority: P2
milestone: trustworthy-librarian
depends_on: []
created: 2026-09-09
updated: 2026-09-21
---

# TKT-0101: Mention and navigate to any library entry

## Outcome

Allow explicit @mentions of any accessible library entry, including encounters, as a consistent reference and navigation tool. Encounter mentions do not imply that the encounter was played or its prepared events occurred.

## Context

The user wanted to reference an encounter while writing. Existing character/location-oriented lookup is too restrictive. Coordinate with TKT-0100 (shared editor and automatic mention suggestions), TKT-0099 (unmatched-name queue), and TKT-0093 (optional identity links); explicit mentions should not require those follow-ups to be implemented first.

## Scope

- Expand shared mention lookup across accessible library entry types, including encounters, sessions, lore, plans, characters, locations, and other supported entry kinds. Use stable entry references rather than assuming every result is a character entity.
- Search display titles, canonical names, and supported aliases. Show the entry type clearly and sufficient parent/group context to distinguish overlapping titles.
- Insert the selected entry's display title while persisting its stable identity separately. Preserve existing caret, trailing-space, keyboard-selection, and undo behavior.
- Keep selection explicit when multiple entries match; do not silently bind a name to the wrong entry.
- Make linked entries open in the existing contextual side panel, with appropriate content for their type. Preserve the current draft, encounter reading position, and surrounding workflow when opening or closing it.
- Apply consistently to existing mention-enabled editors and the shared editor integration as it expands.
- Treat a mention as a reference only. It may provide retrieval/navigation context but cannot establish attendance, occurrence, completion, chronology, or any other factual relationship by itself.
- **Mentions are a search driver (user ruling 2026-09-21)**: retrieval currently ignores `claim_related_entities` entirely — /query never consults the mention table. Wire it in so a record's evidence pool includes claims it is mentioned in, not only claims it owns. Mentions are an obvious ranking/input signal; the audit that motivated this found five load-bearing consumers of the mention table and retrieval is conspicuously not one of them.
- **Commit-path dependency (agreed recommendation 2026-09-21)**: mention pickers on new prose surfaces (Description, Lore) land with their Promotion Pipeline slices (TKT-0136), where mentions in committed prose ride along as `related_entity_ids` on the promoted statements — same name-in-text provenance rule as session capture. A picker without a commit path writes to nothing.

## Open at ticket time

- **Multiple mentions per claim (user question 2026-09-21)**: does `@Romulus @Romulus` in one claim carry any more value than `@Romulus` once plus a plain-text "Romulus" in the same claim? Working assumption is NO — presence, not multiplicity, is the signal, and a mention plus a plain-text occurrence of the same name are equivalent for linking. Decide whether mention density is ever a retrieval weight, or whether the table stays a set (it does today: primary key per claim+entity+kind, duplicates collapse).
- Enforce existing visibility rules in suggestions and previews. Handle renamed or unavailable targets without losing original prose or silently retargeting links.

## Out of scope

- Automatically creating missing entries or promoting their content to canon.
- Marking encounters played/completed from mentions.
- Inferring that a session enacted a prepared encounter or every event in it.
- Replacing optional prose claims with mandatory structured relationships.

## Acceptance criteria

- [ ] An encounter can be found and selected by @mention alongside other library types.
- [ ] Suggestions display type and disambiguating context; identical titles do not cause silent selection.
- [ ] Selected mentions retain stable entry references and readable titles, with existing keyboard/caret behavior preserved.
- [ ] Encounter and other entry previews open without leaving the active editor or losing reading position/draft text.
- [ ] Mentioning prepared material creates no observed claims and changes no encounter lifecycle or canonical state.
- [ ] Visibility restrictions apply to lookup and previews; missing/renamed targets remain safe and understandable.
- [ ] Tests cover encounter references from brainstorms and session notes, ambiguous titles, unavailable targets, and regressions for PC/NPC/location mentions.

## Validation plan

Use a prepared encounter referenced in both a brainstorm and a session note. Confirm the reference is stored and navigable but no preparation becomes an observed outcome. Test two same-named entries of different types, keyboard selection, side-panel close/reopen, and retained editor state.

## Documentation

Document mentions as references rather than assertions, supported library types, disambiguation, and contextual navigation. Deferred: this ticket records scope only.
