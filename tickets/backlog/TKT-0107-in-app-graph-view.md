---
id: TKT-0107
title: In-app graph view of identities and their evidence associations
status: backlog
priority: P2
milestone: shared-campaign-knowledge
depends_on: [TKT-0106]
created: 2026-09-13
updated: 2026-09-13
---

# TKT-0107: In-app graph view of identities and their evidence associations

## Context

Sean reviewed the offline graph viewer (`.local/cognee-evaluation/live-pilot-v3/graph.html`, a self-contained D3 force-directed page over the v3 pilot export: 375 nodes / 1,069 edges, entity and structural nodes, `#semantic` embedding tab) served via `python -m http.server 8767`, and wants that kind of view **available from the app in the future** — not yet; regeneration of a fresher snapshot was explicitly deferred ("not yet"). This ticket records the intent so it survives.

## Scope when taken up

- Render from **Campaign Core canonical data**: entities as nodes (kind-colored), `claim_related_entities` associations as edges (weight by support count), aliases/misspellings distinguishable; NOT from the disposable Cognee evaluation stores. The design doc's line "the graph is a model of these connections, not a required visual graph screen" was written before the identity work made the graph dense and interesting; this ticket adds the screen without changing that the graph is derived.
- Follow the UI conventions (docs/architecture/ui-conventions.md + the Conventions page); the offline viewer is the visual precedent, not the data source.
- Placement: a view mode or panel reachable from the Identity page or Library — Sean's call at design time.
- Hidden intermediate nodes must not leak endpoints through otherwise unavailable paths (standing visibility rule for any graph rendering).
- Keep it read-only: no node/edge editing from the view; decisions continue through the Identity Review queue.

## Out of scope

- Regenerating the Brainstorm pilot bundle (separate maintenance task; also refreshes Brainstorm graph traces, currently stale against the post-identity-work graph).
- LLM relationship extraction or Cognee re-indexing.

## Acceptance

- [ ] Graph view renders the current canonical identity graph from Campaign Core data with kind coloring and support-weighted edges.
- [ ] Reachable in-app behind DM-only visibility; no canonical writes from the view.
- [ ] Conventions-compliant styling; documented in ui-conventions.md.
- [ ] Sean's design sign-off on placement and density controls.
