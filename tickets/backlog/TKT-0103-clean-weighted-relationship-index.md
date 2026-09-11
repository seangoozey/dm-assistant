---
id: TKT-0103
title: Build clean evidence-linked relationship indexing and aggregation
status: backlog
priority: P0
milestone: shared-campaign-knowledge
depends_on: [TKT-0102]
created: 2026-09-10
updated: 2026-09-10
---

# TKT-0103: Build clean evidence-linked relationship indexing and aggregation

## Outcome

A reproducible representative Cognee index suitable for relevance evaluation. Delivery slice of TKT-0092 and TKT-0096; not a full-library migration.

## Scope

- Pin installed library/model/prompt/schema/chunker versions and inspect supported extension points before coding; do not patch site-packages as a durable solution.
- Remove instruction boilerplate from indexed source text. Put extraction instructions in prompts and truth/provenance in metadata, preserving exact source spans and offsets.
- Use section-aware token-bounded chunks, preserving neighboring context when needed. Split oversized passages rather than excluding or truncating them; deduplicate overlapping support by original evidence identity.
- Include representative organizational, causal, geographic, planned and incidental relationships, including the previously missing Sorin/Eustice support and Monastery power-release chain. Audit coverage independently of ranking.
- Extract directed relationship descriptions with exact supporting references, modality, negation, attribution and temporal scope. Generated relationships remain derived; optional SPO enrichment is never required of the author.
- If ingestion strength is included, explicitly request and validate it and preserve it through storage/export. Keep it separate from evidence support, support counts and feedback_weight. Trace fields end-to-end; no assumed automatic weight calculation.
- Aggregate compatible relationships across stable identities while retaining individual evidence contributions. Do not merge opposing predicates or contradictory/modally distinct statements merely because endpoints match. Avoid multiplying strength for copied summaries or overlapping chunks; document the chosen aggregation rule rather than blindly summing.
- Audit suspicious boilerplate nodes, unsupported edges and alias collisions. Preserve failures for analysis; source correction invalidates affected derived relationships.

## Acceptance

- [ ] Versioned manifest maps every indexed passage and edge contribution back to original evidence.
- [ ] All representative fixture passages are covered, including oversized input; no instruction-generated campaign nodes.
- [ ] Weight/schema round-trip tests prove requested fields reach storage and retrieval; feedback remains separate.
- [ ] Duplicate-source, conflicting-state, alias and supersession tests pass.
- [ ] Rebuild is isolated and reversible; no canonical mutations or replacement of the active generation without acceptance.

## Validation

Use TKT-0102 corpus; record extraction quality, coverage, failures, tokens and cost. Check the existing authorized key budget before paid work; do not assume its remaining balance. No new service, purchase, or migration is authorized by this planning ticket.
