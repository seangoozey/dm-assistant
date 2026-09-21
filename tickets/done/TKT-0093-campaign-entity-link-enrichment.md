---
id: TKT-0093
title: Link existing prose to canonical elements without mandatory SPO
status: done
priority: P0
milestone: shared-campaign-knowledge
depends_on: [TKT-0092]
created: 2026-09-06
---

# Outcome

Build optional evidence associations for entity-free or partially linked claims and encounter/source passages.

This is the deterministic linking baseline, not the complete relationship-discovery
feature. TKT-0096 must also evaluate LLM discovery through Cognee. Derived suggestions
may aid retrieval without approval of every edge; canonical enrichment remains reviewed.

## Required reading

- [Shared Campaign Knowledge](../../docs/architecture/shared-campaign-knowledge.md)
- [ADR-0014](../../docs/decisions/ADR-0014-shared-campaign-knowledge.md)
- [ADR-0012](../../docs/decisions/ADR-0012-provenance-first-claims.md)

## Scope

Reuse known IDs and explicit mentions first. Unique canonical names/aliases can yield derived mention links with exact offsets and method version; ambiguous names remain unresolved suggestions. Never manufacture subjects, identities or semantic predicates. Provide correction/suppression and bounded retryable backfill.

## Acceptance and validation

Claims remain capturable without links; long biography retains full text; ambiguous aliases never auto-merge; corrected aliases can rebuild associations; human overrides survive rebuild. Sample existing imported records with a read-only audit before applying derived index changes.

## Migration and rollback

Backfill only derived association storage. Canonical relationship enrichment remains reviewed. Disable/rebuild links without removing claims or evidence.

## Closure

Superseded by TKT-0106 (identity review queue, complete 2026-09-13): entity and alias enrichment now flows through the standing in-app queue, reconcile_links, and role vocabulary — the recurring-process ruling this ticket anticipated. Closed as superseded 2026-09-14 at ticket audit.
