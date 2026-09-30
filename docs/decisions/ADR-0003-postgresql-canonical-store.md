# ADR-0003: PostgreSQL Canonical Store

- Status: accepted (user ruling 2026-09-28: PostgreSQL is the stack; TrueNAS is the final production state once the system is seeded and built to the point of usable-with-occasional-upgrades — that move is deployment maturity, not a re-decision of the store)
- Date: 2026-07-31

## Context

Claims require structured authority, time, provenance, relationships, transactional change sets, full-text retrieval, and later vector search.

## Decision

Use PostgreSQL as the canonical campaign database from Version 1. Keep Windmill platform state in a separate database and credential boundary.

## Consequences

- Schema and migrations begin earlier than with a temporary SQLite design.
- PostgreSQL full-text search provides the lexical baseline.
- pgvector can be added without a separate vector service initially.
- Logical backups and restore tests are required.
