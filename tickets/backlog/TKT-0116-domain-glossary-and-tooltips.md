---
id: TKT-0116
title: Domain glossary with in-app help and definition tooltips
status: backlog
priority: P2
milestone: shared-campaign-knowledge
depends_on: []
created: 2026-09-13
updated: 2026-09-13
---

# TKT-0116: Domain glossary with in-app help and definition tooltips

## Context

Sean (2026-09-13): "keeping truth state, role, identity, document, entity all in my head is becoming increasingly difficult." The app's vocabulary is now large and load-bearing (it encodes the trust model), and nothing in the product teaches it. The system needs a maintained help/glossary document defining each term — what it is, its purpose, and how the app uses it — surfaced through a Help destination and wired into on-page tooltips at the places the terms appear.

## Scope when taken up

- **The glossary document**: one maintained source defining the domain vocabulary, including at least: entity vs. identity vs. alias vs. misspelling; document (source vs. direct-input vs. entity document) vs. record/claim; truth state ladder (observed, established, intended, prepared, possible — and `considered` if TKT-0115 lands); authority (real_play, explicit_lore, npc_intention, preparation, brainstorm); visibility (dm_only, party, character); role vs. title; faction, roster, membership, leadership seat; candidate, proposal, change set, receipt; provenance/source span; supersession/retcon; derived vs. audited (co-mention vs. roster); canon-by-receipt (why there is no canon-status field).
- **Where it lives**: a Help page in the app nav (sibling of Conventions) rendered from a maintained Markdown/TS module — not a separate doc site — so it ships with the app and stays versioned beside the code that enforces the definitions. `docs/product/invariants.md` and the Conventions page are ancestors, not replacements: this is definitions in DM language, not engineering rules.
- **Tooltips**: a shared `<Term term="truth-state">` component (or equivalent) used wherever vocabulary appears — queue cards, editors, hero fields, roles, migration review — rendering the short definition on hover/focus with a link to the full glossary entry. Same mechanism the Conventions page uses for CSS classes, applied to vocabulary.
- **Maintenance**: definitions change with the domain (new states, new kinds). The ticket's definition of done includes the glossary covering every term surfaced by a `<Term>` tooltip, plus a lightweight rule: new vocabulary lands with its glossary entry in the same change (enforced socially or by a test that fails on unknown term keys).

## Out of scope

- Tooltip tours / onboarding flows; this is reference, not a wizard.
