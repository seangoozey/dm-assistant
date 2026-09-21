---
id: TKT-0111
title: Entity descriptions as documents, with gathered evidence and AI prose support
status: done
priority: P2
milestone: shared-campaign-knowledge
depends_on: [TKT-0106, TKT-0099]
created: 2026-09-13
updated: 2026-09-16
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

## Description nature ruling (corrected 2026-09-15 after Sean's challenge — supersedes the first draft)

Two document classes must not be conflated:
- **The synthesized placeholder is the derived artifact** — browser-built from claims, render-only, correctly non-evidentiary. Unchanged.
- **A written description is a DM-authored direct-input document, evidence-class** — same standing as session notes and brainstorm thoughts (connector `direct-input:entity-description`). Sean's case: NPCs carry prose in their sheets that never became claims, and a DM writing from memory adds real information; calling that "derived" would put trusted DM knowledge in constitutional limbo. Promoting it must not require re-typing it elsewhere.

Structure — **one document, two zones**:
- **Gathered zone**: the composer surfaces the entity's claims as REFERENCES — claim-IDs recorded in the description's metadata, never copied text. Traceable, stale-flaggable when a referenced claim supersedes, and duplication-free.
- **Authored zone**: the DM's new prose. Evidence, extractable through the normal review path like any DM document. Provenance chains, never loops: promoted claim ← description ← referenced claim ← original evidence.

Protections that do the real work (no special-casing needed): promotion still goes through review (one door); descriptions are explicit-lore-class at best — real play outranks, always; a description restating a claim is one source saying it, never two (no independent-confirmation illusion). Eventual refinement: when review promotes a statement whose description-reference chain reaches original evidence, offer the original as the preferred citation.

The AI prose writer lives in TKT-0120; 0111 builds gather/compose/file with manual writing and consumes the writer when it exists.

## Out of scope

- Editing imported (non-direct-input) documents in-app — their lineage stays read-only.
- Converting existing summaries into documents automatically.

## Validation evidence

(to record when built)

## Presentation note (2026-09-15 — TKT-0121 supersedes the display side)

Sean's presentation ruling completes this ticket's model: ALL display elements are derived from canon; the description document is authored canon-input whose *rendering* is a template block. 0111 builds the authoring machinery (composer, gather-references, filing, flag-clearing); the templated page layer that displays descriptions — and takes claims/sources under the hood across every entry kind — is TKT-0121. Build order: 0111 (canon input) then 0121 (presentation), or together if picked up in one effort.

## V1 delivered (2026-09-15, deployed) — authoring machinery live

- **Core**: `EntityDescriptionService` files DM prose through the real import pipeline as `entities/{slug}.md` — connector `direct-input:entity-description`, frontmatter carrying entity_id + referenced_claim_ids + written_at; evidence-class per the corrected ruling (DURABLE_EVIDENCE classification). `POST /entities/{id}/description` (DM-gated); `entities/` admitted in the import path policy. Idempotent on key replay.
- **UI — the composer**: page-less entries (dashed-page flag) get a "Write description" action in the standard entry-page-actions slot; the composer shows the ADR-0015 explainer, a prose textarea, and the gathered-claims panel with per-claim checkboxes (all referenced by default, grouped by truth state) — selection becomes the description's recorded references. Save files the document, toasts the receipt, reloads the entry and the library; the matcher's exact-name rule adopts the new document as the entry's page and the flag clears.
- **0121 layer 1 shipped alongside**: claims are under the hood everywhere — StructuredEntryView and CharacterDocumentView now render a collapsed **Records** hood ("Records — claims, provenance, history" / "Records — known facts, real-play, plans") containing the canonical claim sections, provenance, and sources; no claim card list renders in any default page body. The character view's hidden-records toggle moved inside the hood.
- Validation: docker `test_entity_description_filed_as_evidence_document` (files with connector/frontmatter/references, path slug, idempotent replay) — 7/7 in test_direct_capture; local 462; React 110 (claims-inside-hood assertion, composer flow with references + toast). Live: Inquisitors entry renders hood closed in body, Write-description action present, composer opens with 34 gathered claims pre-referenced.

## V1.1 delivered (2026-09-16, deployed) — revisions + stale-flag

- **Revisions file as new source_revisions of the same page document**: the service always targets canonical `entities/{slug}.md`; the importer keys documents by (connector, path) and appends a new source_revision when content differs, so superseded prose stays in revision history. A revision naming a `document_id` whose current path is no longer the entity's page path is rejected **before** ingest ("no longer this entity's page path — file a new description rather than a revision") — a rename must not fork the page silently (`MarkdownImportRepository.current_document_path`).
- **Stale-flag (banner)**: `SourceDocumentContent` now serves `referenced_claims` (from frontmatter). The entry page shows a status line for authored description pages — `Authored page · N referenced records`, escalating to an alert (`N of M referenced records changed since this page was written — consider revising`) when any referenced claim has a claim-history row (claim_history rows are exactly the superseded claims). Both carry a **Revise description** action.
- **Revise flow**: opens the composer seeded with the current page prose ("Revising …'s page"), passes the page `document_id` through `writeEntityDescription`'s new fifth parameter; success toasts "Description revised".
- Validation: docker `test_entity_description_revision_same_document` (2 revisions, same document_id/path, fork-guard rejection leaves revision count at 2) — 9/9 in test_direct_capture; local Core 459 passed/70 skipped; React 121 (new stale-banner→revise→5-arg write test + `supersededReferenceCount` unit test). Live API verified serving `referenced_claims` post-deploy; app bundle redeployed.

## Remaining

- AI prose writer consumption (TKT-0120).
- Sean's first real description remains the acceptance test; after it exists, a real supersession will exercise the stale banner live.

## V1.2 (2026-09-18) — the authored page must WIN the page match and display (Sean's first filed description)

Sean filed Fleurite's description (first real authored page!) and it vanished: the page matcher only considered claim-linked sources, so the imported `locations/illisan/fleurite/fleurite.md` kept the page while `entities/fleurite.md` existed nowhere in the UI. Fixes (all React-side, verified 130/130):
- **Candidate injection**: loadCanonicalEntry adds the authored `entities/{slug}.md` (from the documents list) to the matcher's candidates even when no claim links it yet; post-save reloads pass the freshly-refreshed list explicitly (the closure's state is stale until re-render).
- **Matcher priority**: `entities/` pages are the top tier in both exact-name and named-match scoring — an authored page outranks an imported doc that shares the name.
- **Render normalization**: an authored page renders as the ENTRY — kind label + canonical name as the hero, prose as the summary — instead of "Untitled entry / Source"; the authored-page banner (references count + Revise) shows, and the unpaged flag clears via the same matcher.
- Regression test: claimed draft → fresh file → authored page becomes the entry's page (prose + banner + Revise + no write-description button).

## Closing (2026-09-18)

Accepted: the full lifecycle is live and tested — composer (manual + AI drafting with two-layer gather via TKT-0120), evidence-class filing at entities/{slug}.md, revisions with the rename fork-guard, the authored page winning the page match and rendering as the entry, the referenced-records banner with Revise, and Sean's first real description (Fleurite) filed and displaying. The one unexercised-live behavior — the stale banner firing on a real claim supersession — is observational; if it misbehaves when it happens, that's a new small ticket. AI prose writer consumption shipped as TKT-0120 (closed) with follow-ups 0126 (done) and 0127 (done).
