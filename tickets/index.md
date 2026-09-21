# Ticket Index

Update this file whenever a ticket moves or changes scope.

## In progress

- [TKT-0099: Lore creation queue with evidence gathering and optional synopsis](in-progress/TKT-0099-lore-creation-queue.md) — V1 + re-attribution + AI direction delivered; remaining = mention queueing in composers, refresh persistence for drafts, 0040 conflict path

## Ready

- [TKT-0132: Vocabulary overhaul — Migration, Library, and Records surfaces rename to ADR-0017](ready/TKT-0132-vocabulary-rename-migration-and-library.md) — Assertion→Claim, Documents→Sources, unify Records hoods
- [TKT-0133: Vocabulary overhaul — Brainstorm reframed to Truth State; canon-status hero removed](ready/TKT-0133-vocabulary-brainstorm-and-truth-state.md) — "non-canonical" retired; Possible→Considered; DM-only standardized
- [TKT-0134: Vocabulary overhaul — Glossary and Help rewritten to ADR-0017](ready/TKT-0134-vocabulary-glossary-help-rewrite.md) — add Source/Attribute/Kind/Truth State/Identity; redefine Document/Claim/Entity; depends on 0132+0133
- [TKT-0135: Vocabulary overhaul — Kind separated from Attributes; Source provenance for Direct Input; Entry retirement](ready/TKT-0135-vocabulary-kind-attributes-separation.md) — Kind as classification; Direct Input origin recorded; "Entry" retires from domain copy
- [TKT-0130: Retrieval orders by campaign chronology and answers when/how-long questions](ready/TKT-0130-retrieval-chronology-ordering.md) — split from 0041; retrieval day-ordinal sort + /ask date questions
- [TKT-0131: Terminology and architecture review](ready/TKT-0131-terminology-and-architecture-review.md) — ADR-0017 recorded; implementation = 0132–0135; this ticket tracks the overall effort

## Backlog

Active when picked up:

- [TKT-0136: Promotion Pipeline — reusable Proposal → Candidate → Claim review and commit](backlog/TKT-0136-promotion-pipeline.md) — framework doc + ADR-0018 written; Brainstorm → Lore → Description adoption + repair lane
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
