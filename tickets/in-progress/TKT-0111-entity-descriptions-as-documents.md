---
id: TKT-0111
title: Entity descriptions as documents, with gathered evidence and AI prose support
status: in-progress
priority: P2
milestone: shared-campaign-knowledge
depends_on: [TKT-0106, TKT-0099]
created: 2026-09-13
updated: 2026-09-13
---

# TKT-0111: Entity descriptions as documents, with gathered evidence and AI prose support

## Context (agreed with Sean 2026-09-13)

Claim-rich but page-less identities (Ruh: 7 evidence docs, Inquisitors: 18, Far Realm: 12 — none of which is *their* page) currently render synthesized placeholders. When they need Descriptions, they should graduate into **documents of their own, written in the app**: the DM authors prose; the system files it as a source document (`markdown:direct-input:entity:<id>`, path family `entities/`), exactly like session notes and brainstorm thoughts. The entity's page stops being synthesized (exact-name match in the doc matcher), the description gains revisions and can later evidence claims via spans, and the trust line holds — DM-authored, connector-marked, explicit-lore standing beneath real-play claims. Lifecycle: claims-only identity → synthesized placeholder → entity document when a Description is written.

This ticket **extends TKT-0099** (Lore creation queue: gather library evidence, AI drafts only from selected evidence, cites support, preserves uncertainty). The description flow is that pattern applied to an existing entity, with the output being the entity's document rather than a new lore entry. TKT-0099's drafting rules apply verbatim: AI drafts only from selected evidence; never turn plans into outcomes or assumptions into facts.

## Scope

- **Write-description flow** on synthesized entry pages (and the profile editor): opens a description composer for the entity.
- **Scrape existing information during creation** (Sean's requirement): the composer pre-gathers the entity's canonical material — current claims grouped by projection, aliases, roles and holders, roster/associations, profile fields, and bounded evidence excerpts with citations — as selectable source material for the prose, using TKT-0099's gather mechanics (content search, aliases, graph associations as discovery aids, not proof).
- **Filing**: on save, Core creates the entity document (direct-input connector, `entities/` path family) with an immutable first revision; later edits create new revisions, never overwrites. The entity's view switches to its document; entity template fields (aliases, location, roles) still render from entity data over the doc.
- **AI prose writer support** (eventually, not necessarily first): an explicit, opt-in Draft action in the composer using the gathered selection, per TKT-0099's rules. No automatic drafting.
- Far Realm case needs nothing special: scattered evidence docs stay as evidence; the description document is the gathered prose in one place.

## Out of scope

- Editing imported (non-direct-input) documents in-app — their lineage stays read-only.
- Converting existing summaries into documents automatically.

## Validation evidence

(to record when built)
