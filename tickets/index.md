# Ticket Index

Update this file whenever a ticket moves or changes scope.

## In progress

- [TKT-0136: Promotion Pipeline — reusable Proposal → Candidate → Claim review and commit](in-progress/TKT-0136-promotion-pipeline.md) — ALL FOUR SLICES DELIVERED 2026-09-21 (Description + Lore + Brainstorm + repair lane w/ standing audit; mandatory review everywhere; live audit found 1 shell + 5 captures + 1 brainstorm); awaiting Sean's close review — stable promotion REAL, 0140 unblocked
- [TKT-0099: Lore creation queue with evidence gathering and optional synopsis](in-progress/TKT-0099-lore-creation-queue.md) — V1 + re-attribution + AI direction delivered; re-attribution canonical write moved to migration 0066 (2026-09-21); remaining = mention queueing in composers, refresh persistence for drafts, 0040 conflict path

## Ready

- [TKT-0132: Vocabulary overhaul — Migration, Library, and Records surfaces rename to ADR-0017](ready/TKT-0132-vocabulary-rename-migration-and-library.md) — Assertion→Claim, Documents→Sources, unify Records hoods
- [TKT-0133: Vocabulary overhaul — Brainstorm reframed to Truth State; canon-status hero removed](ready/TKT-0133-vocabulary-brainstorm-and-truth-state.md) — "non-canonical" retired; Possible→Considered; DM-only standardized
- [TKT-0134: Vocabulary overhaul — Glossary and Help rewritten to ADR-0017](ready/TKT-0134-vocabulary-glossary-help-rewrite.md) — add Source/Attribute/Kind/Truth State/Identity; redefine Document/Claim/Entity; depends on 0132+0133
- [TKT-0135: Vocabulary overhaul — Kind separated from Attributes; Source provenance for Direct Input; Entry retirement](ready/TKT-0135-vocabulary-kind-attributes-separation.md) — Kind as classification; Direct Input origin recorded; "Entry" retires from domain copy
- [TKT-0130: Retrieval orders by campaign chronology and answers when/how-long questions](ready/TKT-0130-retrieval-chronology-ordering.md) — split from 0041; retrieval day-ordinal sort + /ask date questions
- [TKT-0131: Terminology and architecture review](ready/TKT-0131-terminology-and-architecture-review.md) — ADR-0017 recorded; implementation = 0132–0135; this ticket tracks the overall effort

## Backlog

Active when picked up:

- [TKT-0142: Unified claim surface — one claim card behind every claim operation](backlog/TKT-0142-unified-claim-surface.md) — the russian-doll fix; Promotion Review row is the seed; phased convergence (replacement editor → Migration steps 3–6 → session review); new surfaces born on it
- [TKT-0141: Presumed Retcon surface — unopposed established-fact changes auto-accept, editable reason](backlog/TKT-0141-presumed-retcon-surface.md) — refines the retcon invariant (presume when no observed conflict); depends on 0142; attributes inherit it per the 0139 ruling
- [TKT-0140: Migrate the whole library to Qualified Entities](backlog/TKT-0140-library-qualified-entity-migration.md) — BLOCKED by stable promotion (0136) + the standard (0139); summaries migrate into Descriptions VIA the pipeline; standing unqualified-entities queue
- [TKT-0139: Define the Qualified Entity standard](backlog/TKT-0139-qualified-entity-standard.md) — DELIVERED 2026-09-21: spec ACCEPTED (all rulings), ADR-0017 amendment, glossary entry, audit endpoint live (120 entities: 53 qualified / 67 unqualified — the Migration→Seeded distance is a number); awaiting close review. Minting = TKT-0143
- [TKT-0147: Phase 2 Stage 3 — Document/Entity alignment](backlog/TKT-0147-document-entity-alignment.md) — sheets demote to evidence (22 live); identity mints onto records ANCHORED to sheet spans; only authored Descriptions render pages; one editor/save path; Q5 flips computed; Roccid's dropdowns arrive by convergence
- [TKT-0146: Description claim breakpoints — the :: authoring notation and the candidate builder](backlog/TKT-0146-description-claim-breakpoints.md) — marker-only derivation (no markers = no breaks), four regroup ops in review, Dossier-like ordered claim collection on the document; FRE prose test = 9 claims vs 14 sentence rows; reverts the mis-built claim-composition UI; autosave per ADR-0019
- [TKT-0145: Re-home the session-note reviewer off the shelved phase-1 workspace](backlog/TKT-0145-session-review-rehome.md) — the daily reviewer rents space on the shelved wizard; rebuild on the 0142 claim card, reroute capture/audit/document entries, retire the flag dependency
- [TKT-0144: Brainstorm general review — unfinished works, library display, Entity promotion](backlog/TKT-0144-brainstorm-general-review.md) — from the Wrath of Romulus WIP testing: brainstorms lack cohesion across surfaces (5x Library rows per session; audit double-count fixed same day); rulings + slices; the open session is the fixture
- [TKT-0143: Claim-backed attribute minting](backlog/TKT-0143-claim-backed-attribute-minting.md) — dropdown mints dated claims behind the fast path (life_status pattern generalized); presumed-retcon supersession; gates 0139's Q5 + 0137's attribute promotion
- [TKT-0138: Orphaned claims review — standing queue to assign owners to subject-less claims](backlog/TKT-0138-orphaned-claims-review.md) — exposed by Lore's group-by-owner; PRIMARY PATH = checked claims migrate into the Lore creation queue as seeded evidence (Lore creates/links the owner); direct assign + receipted "no owner needed" for ambient history/lore
- [TKT-0137: AI Promotion Assistant — wand-marked suggestions inside the Promotion Pipeline, tested on Lore first](backlog/TKT-0137-ai-promotion-assistant.md) — PROPOSAL awaiting Sean's rulings (purpose slot, async vs sync, placement); depends on 0136 Lore slice
- [TKT-0099 remaining: Unmatched @mention queueing in composers](in-progress/TKT-0099-lore-creation-queue.md) — Queue for Lore alongside Keep as text in session notes/brainstorm
- [TKT-0119: Responsive layout strategy](backlog/TKT-0119-responsive-strategy.md) — named breakpoints, container queries for panels, tested crush path
- [TKT-0099: Lore creation queue](in-progress/TKT-0099-lore-creation-queue.md) — deferral expired 2026-09-19; V1 shipped
- [TKT-0100: Shared spellcheck, campaign dictionary, and automatic mention suggestions](backlog/TKT-0100-campaign-spellcheck-and-mentions.md) — deferral expired 2026-09-19
- [TKT-0101: Mention and navigate to any library entry](backlog/TKT-0101-mentions-for-all-library-entries.md) — deferral expired 2026-09-19; reference-only semantics
- [TKT-0107: In-app graph view of identities and evidence associations](backlog/TKT-0107-in-app-graph-view.md) — deferred by request ("not yet"); renders from Campaign Core canonical data
- [TKT-0115: Brainstorm truth state — findable prior brainstorm thinking without granting canon](backlog/TKT-0115-brainstorm-truth-state.md) — deferral expired 2026-09-19; design questions enumerated
- [TKT-0040: Lore Entry with conflict-gated direct application](backlog/TKT-0040-lore-entry-conflict-gated-application.md) — ties into TKT-0099 track
- [TKT-0042: Timeline view](backlog/TKT-0042-timeline-view.md)
- [TKT-0043: Failed-plan review queue](backlog/TKT-0043-failed-plan-review-queue.md) — low priority per Sean
- [TKT-0094: Implement ranked passage and connected evidence retrieval](backlog/TKT-0094-shared-connected-retrieval.md) — milestone umbrella; delivery slices live in 0103/0104
- [TKT-0095: Connect every campaign workflow to shared knowledge](backlog/TKT-0095-shared-knowledge-workflow-integration.md) — milestone umbrella

Parked with the graph ruling (2026-09-14: promising, not fully ready for a real test; revisit after the DB-completeness front settles):

- [TKT-0096: Evaluate Cognee and graph retrieval backends against shared contract](backlog/TKT-0096-knowledge-backend-evaluation.md) — PARKED; corpus runs complete, adoption deferred
- [TKT-0103: Build clean evidence-linked relationship indexing](backlog/TKT-0103-clean-weighted-relationship-index.md) — PARKED; carries TKT-0092's absorbed projection remainder
- [TKT-0104: Evaluate native Cognee relationship retrieval against the current walker](backlog/TKT-0104-native-cognee-ranked-retrieval.md) — PARKED; comparison diagnostic complete
- [TKT-0105: Decide Cognee retention or Neo4j migration from measured results](backlog/TKT-0105-graph-backend-decision.md) — PARKED behind 0104
