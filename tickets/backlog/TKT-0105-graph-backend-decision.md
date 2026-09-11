---
id: TKT-0105
title: Decide Cognee retention or Neo4j retrieval migration from measured results
status: backlog
priority: P1
milestone: shared-campaign-knowledge
depends_on: [TKT-0104]
created: 2026-09-10
updated: 2026-09-10
---

# TKT-0105: Decide Cognee retention or Neo4j retrieval migration from measured results

## Outcome

Close the bounded backend evaluation in TKT-0096 with a supported keep/change decision, not a graph-size success claim.

## Scope

- If configured Cognee meets relevance, provenance, correction and latency criteria through maintainable supported APIs, retain it and document remaining production work under TKT-0092/0094/0095.
- If it fails, evaluate a narrow Neo4j explicit-schema/hybrid-traversal alternative against the same inputs and benchmarks. Distinguish changing the graph store while retaining Cognee from replacing its extraction/retrieval framework.
- Compare operational cost, dependency stability, schema control, debug visibility, source invalidation, rebuild/restore and development burden. No presumption that Neo4j calculates ingestion strength automatically.
- Borrow Microsoft GraphRAG's extraction/aggregation lessons without automatically adopting its complete community-summary pipeline or source-target-only aggregation.
- Keep PostgreSQL/Campaign Core authoritative. Any backend remains a disposable derived projection, with no canonical write credentials.

## Acceptance

- [ ] Written decision cites measured results and failure cases, not preference or edge counts.
- [ ] Selected architecture and tradeoffs documented in an ADR after review.
- [ ] Follow-up deployment/migration plan includes backup, rollback, freshness, monitoring and cross-workflow integration.
- [ ] No production migration performed under this decision ticket; infrastructure additions require explicit scope/approval.

## Research references

- Microsoft extraction/aggregation: https://github.com/microsoft/graphrag/blob/main/packages/graphrag/graphrag/index/operations/extract_graph/extract_graph.py
- Microsoft default flow: https://microsoft.github.io/graphrag/index/default_dataflow/
- Neo4j builder: https://neo4j.com/docs/neo4j-graphrag-python/current/user_guide_kg_builder.html
- Neo4j retrieval: https://neo4j.com/docs/neo4j-graphrag-python/current/user_guide_rag.html
- Cognee indexing: https://docs.cognee.ai/core-concepts/main-operations/legacy-operations/cognify

Verify versions when work starts; the prior inspection used installed Cognee 1.5.3 and upstream documentation on 2026-09-09.
