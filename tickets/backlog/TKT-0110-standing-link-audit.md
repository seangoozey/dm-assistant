---
id: TKT-0110
title: Standing in-app entity/document link audit
status: backlog
priority: P2
milestone: shared-campaign-knowledge
depends_on: [TKT-0109]
created: 2026-09-13
updated: 2026-09-13
---

# TKT-0110: Standing in-app entity/document link audit

## Context

Sean (2026-09-13): "I believe we're going to have to traverse all records and make sure they're linked correctly, there have been too many failures." The 2026-09-13 matcher repair dropped 16 wrong-page borrows found by a one-off read-only script (`.local/audit_links.py`) — but per the standing productize ruling, recurring data-quality gaps become standing in-app review features, never one-time manual fixes.

## Scope when taken up

- A Campaign Core read endpoint that audits entity↔document affinity across all entities with claim-evidenced sources: wrong-page borrows (foreign filename tokens), ambiguous partial matches, zero-affinity identities whose claims all live in other subjects' files, and documents that look like an entity's page but are borrowed by none.
- Surface as a review list (Tools or Identity family) with per-finding explanations and one-click navigation; findings are computed live, never stored as truth.
- Consider the same surface for claim-link sanity (derived `claim_related_entities` rows whose evidence no longer mentions the entity).

## Out of scope

- Auto-repair: every fix stays an explicit DM decision or a matcher rule change with tests.
