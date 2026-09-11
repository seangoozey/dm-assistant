# Shared Campaign Knowledge

Design status: proposed implementation contract, 2026-09-06. See ADR-0014 and TKT-0089 through TKT-0096.

## Purpose

Campaign Core supplies one relationship-aware knowledge service to every workflow. Ask follows evidence across entries; encounters assemble participants, locations, history and plans; Lore finds affected records and comparison evidence; Brainstorm uses the same connections for context; the library offers navigable related content.

The graph is a model of these connections, not a required visual graph screen. Normal use stays centered on readable campaign content, references, and compact explanations.

## Existing foundation and gaps

- Stable record identities, aliases, claims, relationships and relationship evidence already exist. Plans have a separate family and lifecycle.
- Claim evidence links to immutable source spans and revisions. `claim_related_entities` contains explicit mentioned-entity associations; optional subjects are supported.
- Encounter content currently also exists as source documents. Its graph identity must reference the actual source-document UUID until a deliberate family migration occurs; do not fabricate an encounter entity.
- The PostgreSQL retrieval adapter loads claims, relationships and active candidates, filters lexical overlap, sorts by citation, then limits to 100. This can exclude useful results before the UI ranks them.
- Relationship retrieval currently exposes only its from-entity as an owner. It must expose both endpoints and direction for traversal.
- The existing conflict heuristic can label any two established claims as conflicting, or an observed/established pair as a retcon. Shared expansion must not multiply these false conclusions.
- UI excerpts and pins improve use but are not a shared retrieval policy.

## Knowledge contract

Node references are typed `(family, id)` pairs. Families cover existing entities, claims, relationships, plans, source documents/revisions/spans, and workflow sessions. A shared UUID is reused where present; source and workflow identities retain their own family. Passage nodes are derived references to an immutable assertion or revision with exact offsets, not additional claims.

Connections have three distinct meanings:

| Class | Examples | Authority and use |
| --- | --- | --- |
| Recorded semantic relationship | Located in; member of; owns; a recorded command | Supported by accepted relationship evidence or an explicitly reviewed claim-to-relationship mapping. Carries direction, truth dimensions and campaign time. |
| Evidence association | Claim concerns entity; source supports claim; encounter references NPC; plan has owner | Supports navigation and retrieval. Mentioning two entities does not establish an action between them. |
| Suggested association | Ambiguous name match; model-proposed relationship | Derived retrieval hint with method/version and evidence offsets. Never supplies an established relationship or automatically merges identities. |

Every edge records its class, typed endpoints, origin IDs, relevant evidence IDs, derivation version if applicable, and current/historical eligibility. Use existing authority and time coordinates, not an independent editable truth state on a graph copy. A semantic relationship may have several supporting claims; retain all provenance and expose disagreements.

Keep the initial semantic vocabulary small and driven by verified data: containment, membership, ownership, participation, and explicit plan prerequisites are candidates, not automatic classifications. Commands and complex plans may stay complete claims associated with their participants. No mandatory predicate extraction or new entity creation is introduced.

## Common retrieval operation

Introduce a typed service with query text and/or seed record IDs, requester visibility, optional campaign as-of date, requested purpose, inclusion of historical/planning context, and bounded result/depth limits. Existing `/retrieval/query` remains a compatibility adapter. All consumers call Campaign Core; clients do not assemble their own graphs.

Return ranked passages with parent assertion IDs, complete-text references, all relevant citations, match offsets, associated entities, evidence class, and the exact path explaining why each result was retrieved. Return separate comparison candidates and verified conflicts; absence of a known conflict is not proof that no conflict exists. Include index version, freshness and truncation metadata for diagnostics, hidden from normal campaign pages.

Processing sequence:

1. Resolve explicit IDs and unique aliases. Ambiguous names produce choices or labeled candidates; never silently merge.
2. Select eligible records and connections using visibility, supersession, state and time before ranking, counting or traversal. Hidden intermediate nodes must not expose visible endpoints through otherwise unavailable paths, citations or counts.
3. Retrieve passages using indexed full-text/name matching, with optional semantic retrieval behind the same adapter. Rank in Core before limiting.
4. Expand a small neighborhood from relevant entities and evidence, initially at most two hops. Apply per-node fan-out and total budgets, cycle detection and deterministic tie-breaking. High-degree names and common sources must not flood context.
5. Revalidate every path and returned record against current Campaign Core state. A graph path is an explanation of retrieval, not a newly proven transitive fact.
6. Return citations and passages. Answer synthesis, if added, must cite the evidence for each asserted step and abstain from unsupported conclusions.

Default current queries exclude superseded claims. Historical queries retain valid intervals and explicitly identify historical records. Prepared encounters and intended plans remain context of preparation or intention; a path never converts them into real-play outcomes. Player statements retain attribution and do not predict PC actions. Expected dates never establish occurrence.

## Writes, discovery and lifecycle

Accepted entities, claims, explicit links and semantic relationships remain in campaign PostgreSQL under Campaign Core mutations and receipts. Ingestion never waits for graph enrichment.

Build an idempotent projection from existing accepted links first. For unlinked prose, exact unique canonical-name/alias matches can create derived mention associations with offsets; ambiguity is retained, and inferred semantic relationships require review. Link correction can suppress a bad derived match without editing its source. Human-confirmed semantic changes follow existing reviewed mutation rules.

Review is required to promote an inferred relationship into canonical truth, not to
use every derived association for retrieval. LLM-discovered, evidence-linked
suggestions may automatically retrieve relevant passages. Their source assertions,
not the suggestions themselves, support answers. Model discovery must preserve
attribution, negation, time and planning dimensions and cannot verify a factual
conflict by itself. Unknown or ambiguous links remain non-authoritative.

Projection refresh consumes durable change notifications/outbox events for apply, replacement, merge, visibility changes, aliases and source associations. Store a processed watermark and support full rebuild plus atomic generation switch. On stale or unavailable indexes, canonical reads remain available and results are revalidated; stale nodes may never resurrect superseded or newly hidden material. Rollback disables the projection without removing truth or source evidence.

## Workflow integration

| Consumer | Required use |
| --- | --- |
| Ask | Cross-entry questions, ranked evidence paths and qualified answers. |
| Encounter runner | Participants, location hierarchy, relevant events, ongoing intentions and prerequisites; opening context preserves reading and table-note position. Prepared participation is not proof someone attended. |
| Lore Entry | Resolve affected records and fetch comparable claims before deciding whether a proposal needs conflict review. Unknown equivalence or missing structure cannot silently justify automatic application. |
| Brainstorm | Thought and pin IDs become seeds, while thoughts remain non-canon. Suggestions show compact passages and explanations when requested. |
| Library and session notes | Reuse the same name resolver, related-record navigation and evidence links; session observations retain their chronology. |

## Backend decision

Implement the first projection and service using the existing PostgreSQL boundary. Keep the index/retriever adapter replaceable. This is a baseline implementation, not a decision that a dedicated graph is unnecessary.

Evaluate Cognee, a dedicated graph backend, and optional vector passage search against the same corpus after that contract works. Evaluate recall, precision, path fidelity, update lag, rebuild/restore behavior, latency and operational cost. External extraction output remains derived. No backend may write canonical claims, relax visibility or require mandatory SPO.

The Cognee evaluation explicitly includes an LLM: discovering missing relationships
inside prose is part of the intended product capability. A storage-only comparison
does not test that purpose. Compare lexical retrieval, known-link traversal, and
LLM-enriched retrieval independently; never supply expected edges to the discovery
arm. OpenRouter is the first provider route to validate, with separate embedding
configuration and pinned versions/model settings. Model choice and compatibility
remain unverified until the experiment. Track extraction cost, grounding, variance,
failures and source-change invalidation alongside search metrics. First use synthetic
data, with no unapproved live-data transfer or unbounded provider spending.

## Acceptance corpus

Use a separate sanitized connected-knowledge corpus alongside the existing 38 cases. Include at least 24 cases, at least four each for Ask, encounters, Lore and Brainstorm; remaining cases target lifecycle/security. Each case names required evidence IDs, forbidden facts/paths, expected ambiguity, and allowed path classes.

Required scenarios include Ishi'go'dan sent to Tsunadis on Mythis Minor versus the summoning on Ragnok; encounter participant context spanning several sources; location containment; multiple compatible established claims; explicit contradiction versus merely related claims; alias ambiguity; entity-free claims; a hidden intermediate node; superseded evidence; planning versus observed outcomes; and attributed PC intentions. Measure passage recall@10 and precision@10 separately from answer correctness. No unsupported canonical relationship or hidden-path leakage is allowed. Freeze numeric relevance targets with the baseline results, rather than claiming improvement without measured comparison.
