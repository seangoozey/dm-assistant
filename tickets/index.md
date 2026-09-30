# Ticket Index

Update this file whenever a ticket moves or changes scope.

## In progress

- [TKT-0137: AI Promotion Assistant — wand-marked suggestions inside the Promotion Pipeline, tested on Lore first](in-progress/TKT-0137-ai-promotion-assistant.md) — LORE + DESCRIPTION DEDUP DELIVERED 2026-09-27: promotion purpose + deepseek-chat candidate (receipted activation, no default); restatement-first suggestions (positional refs, harness-validated) on Lore; Description claim review gained "Check for duplicates" — the deterministic mirror rides the same job as system_restatements, joined with the AI's calls into green/blue/orange row notes with one-click Exclude (nothing auto-excluded); async Windmill job; statement ideas + Link pre-sort wand-marked, never auto-included; Stage 3 untouched; next: Sean activates the profile + fresh go for a real-data run
- [TKT-0099: Lore creation queue with evidence gathering and optional synopsis](in-progress/TKT-0099-lore-creation-queue.md) — V1 + re-attribution + AI direction + the independent working page delivered; remaining = mention queueing in composers, conflict surfacing in creation review (rode with 0040, now retired — the concern lands with 0142)

## Ready

- [TKT-0138: Orphaned claims review — a standing queue to assign owners to subject-less claims](ready/TKT-0138-orphaned-claims-review.md) — THE FRONT (Sean 2026-09-28: unassigned invisible data outranks Q1 prose completion, which is baseline no-end): 186 live orphans, no surface lists them today; write path landed (0067/0068); Lore bridge primary + direct assign + "no owner needed"; flips audit Q3 to computed and folds the Q5 flip
- [TKT-0135: Vocabulary overhaul — Kind separated from Attributes; Source provenance for Direct Input; Entry retirement](ready/TKT-0135-vocabulary-kind-attributes-separation.md) — the last 0131 implementation tail: Kind as classification; Direct Input origin recorded; "Entry" retires from domain copy
- [TKT-0130: Retrieval orders by campaign chronology and answers when/how-long questions](ready/TKT-0130-retrieval-chronology-ordering.md) — split from 0041; retrieval day-ordinal sort + /ask date questions

## Backlog

Active when picked up:

- [TKT-0142: Unified claim surface — one claim card behind every claim operation](backlog/TKT-0142-unified-claim-surface.md) — the russian-doll fix; Promotion Review row is the seed; phased convergence (replacement editor → Migration steps 3–6 → session review); new surfaces born on it; absorbs the conflict-display concern from the retired 0040
- [TKT-0141: Presumed Retcon surface — unopposed established-fact changes auto-accept, editable reason](backlog/TKT-0141-presumed-retcon-surface.md) — refines the retcon invariant (presume when no observed conflict); depends on 0142; attributes inherit it per the 0139 ruling
- [TKT-0145: Re-home the session-note reviewer off the shelved phase-1 workspace](backlog/TKT-0145-session-review-rehome.md) — the daily reviewer rents space on the shelved wizard; rebuild on the 0142 claim card, reroute capture/audit/document entries, retire the flag dependency
- [TKT-0144: Brainstorm general review — unfinished works, library display, Entity promotion](backlog/TKT-0144-brainstorm-general-review.md) — from the Wrath of Romulus WIP testing: brainstorms lack cohesion across surfaces (5x Library rows per session; audit double-count fixed same day); rulings + slices; the open session is the fixture
- [TKT-0119: Responsive layout strategy](backlog/TKT-0119-responsive-strategy.md) — named breakpoints, container queries for panels, tested crush path
- [TKT-0100: Shared spellcheck, campaign dictionary, and automatic mention suggestions](backlog/TKT-0100-campaign-spellcheck-and-mentions.md) — carries the dictionary forcing-function ruling (mentions have real consumers)
- [TKT-0101: Mention and navigate to any library entry](backlog/TKT-0101-mentions-for-all-library-entries.md) — reference-only semantics; carries the retrieval-driver ruling (query consults claim_related_entities)
- [TKT-0042: Timeline view](backlog/TKT-0042-timeline-view.md) — dependency 0041 long done
- [TKT-0043: Failed-plan review queue](backlog/TKT-0043-failed-plan-review-queue.md) — live AGENTS.md invariant, unenforced today (lifecycle supports failed; no detection/queue); refreshed 2026-09-28; natural home = the 0142 conflict machinery
- [TKT-0107: In-app graph view of identities and evidence associations](backlog/TKT-0107-in-app-graph-view.md) — "not yet" timing deferral (not the Cognee park — renders from canonical data; dep 0106 long satisfied); refiled 2026-09-28
The graph track — parked (2026-09-14: revisit after the DB-completeness front settles = 0138 landing; 71/120 today), reframed by Sean's 2026-09-28 ruling: **the graph service is FOUNDATIONAL to project completion; only the concrete implementation is unresolved.** The decision track (0096→0103→0104→0105) produces the infrastructure ruling that unblocks the engine (0094) and its consumers (0095):

- [TKT-0094: Implement ranked passage and connected evidence retrieval — the graph service](backlog/TKT-0094-shared-connected-retrieval.md) — BLOCKED (P0, foundational): unblocks with the final graph infrastructure decision
- [TKT-0095: Connect every campaign workflow to shared knowledge](backlog/TKT-0095-shared-knowledge-workflow-integration.md) — BLOCKED behind 0094; consumer integration follows the engine
- [TKT-0096: Evaluate Cognee and graph retrieval backends against shared contract](backlog/TKT-0096-knowledge-backend-evaluation.md) — corpus runs COMPLETE (evidence in hand for 0105)
- [TKT-0103: Build clean evidence-linked relationship indexing](backlog/TKT-0103-clean-weighted-relationship-index.md) — the concrete REMAINING BUILD on the decision track (the Postgres-native candidate 0105 weighs)
- [TKT-0104: Native Cognee retrieval comparison](backlog/TKT-0104-native-cognee-ranked-retrieval.md) — diagnostic COMPLETE (native 4/6 vs deployed 2/6); evidence in hand
- [TKT-0105: The graph backend DECISION](backlog/TKT-0105-graph-backend-decision.md) — Cognee vs Neo4j vs Postgres-native; the ruling that unblocks the foundational service; open input = 0103

Unblock sequence when the park lifts: 0103 → 0105 → 0094 → 0095.
