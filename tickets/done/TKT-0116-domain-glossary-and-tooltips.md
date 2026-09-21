---
id: TKT-0116
title: Domain glossary with in-app help and definition tooltips
status: done
priority: P2
milestone: shared-campaign-knowledge
depends_on: []
created: 2026-09-13
updated: 2026-09-14
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

## Delivery (2026-09-14, deployed)

- **`glossary.tsx`**: 29 entries across six categories (Records and truth, Identity, Documents and evidence, Organizations and roles, Workflow and audit, Retrieval and the graph) — each with a tooltip `short` and a full `definition` in DM language, including the ladder (observed/established/intended/prepared/possible), authority, visibility, supersession, canon-by-receipt, entity/alias/misspelling, document/direct-input/description/provenance, faction/roster/role/leadership/title (the title-vs-role ruling encoded), candidate/proposal/change-set/receipt, derived-vs-audited, evidence-vs-suggestion, graph-trace.
- **`Term` component**: dotted-underline inline term; hover/focus shows name + short definition; click deep-links to Help, scrolls the entry into view and flashes it. Unknown keys render visibly broken instead of crashing.
- **Help page** in the nav (after Conventions): all entries grouped by category.
- **Wired surfaces** (pattern established, coverage grows with the rule): editor "Kind (audited)", "Members (audited roster)", Leadership checkboxes, Roles-page explainer (role/faction/leadership), entry-hero Aliases/Roles/Canon status.
- **Maintenance rule enforced by test**: `glossary.test.tsx` reads App.tsx as raw source, extracts every `<Term term="…">` key, and fails on any key without a registry entry; also validates category completeness and entry shape.

Validation: 105 React tests pass (4 new glossary tests + Help deep-link flow), `tsc` clean. Live-verified: Help renders 29 entries in 6 groups; tooltip hidden until hover with correct content; term click navigates to Help and flashes the Leadership entry. Term coverage beyond the initial surfaces grows incrementally via the `<Term>` rule.
