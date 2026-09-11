---
id: TKT-0066
title: Use assertion-first retrieval and conflict detection
status: completed
priority: P1
milestone: planning-workspace
depends_on: [TKT-0063, TKT-0064, TKT-0065]
created: 2026-08-11
updated: 2026-08-11
---

# TKT-0066: Use Assertion-First Retrieval and Conflict Detection

## Outcome

Full-text and semantic retrieval use the complete assertion; subject queries use resolved identity; optional predicate/object indexes improve traversal without controlling claim meaning.

## Acceptance criteria

- [x] Complete assertion text is indexed for grounded retrieval.
- [x] Subject queries use stable resolved entity identity.
- [x] Predicate/object filtering tolerates missing indexes.
- [x] Contradiction checks compare assertion meaning and subject rather than triple equality alone.
- [x] Alias changes and entity merges preserve claim discovery.
- [x] Ruhrogue-derived fixtures cover full-text, subject, relationship, and conflict retrieval.
