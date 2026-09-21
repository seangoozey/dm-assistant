---
id: TKT-0110
title: Standing in-app entity/document link audit
status: done
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

## Validation evidence

Delivered 2026-09-19, deployed, live-verified.

- **Core** (`application/link_audit.py` + `adapters/postgres/link_audit.py`): read-only traversal joining entities → claims → evidence → spans → revisions → documents → paths. Two finding kinds: **wrong_page_borrow** (filename carries tokens belonging to other entities — detected via a word-to-entity-name index, mirroring the UI matcher's rules) and **zero_affinity** (>3 claim-evidenced sources, none of which is the entity's page). `GET /campaign/link-audit` (DM-gated). Computed live, never stored.
- **UI**: Tools gains a **Link audit** panel — Run/Re-run, findings grouped by kind with the entity name, kind chip, detail, and a one-click "Open {entity}" that navigates (guard-wrapped) to the entry.
- **Live result**: 0 findings across 53 audited entities — correct, the 2026-09-13 repair already fixed the 16 wrong borrows this detects. The surface is now standing for future drift.
- Tests: Core 5 local (wrong-page borrow detection, exact-match pass, qualifier-suffix pass, zero-affinity detection, DM-only API); React 136/136 incl. run → findings display → navigate to entity.
