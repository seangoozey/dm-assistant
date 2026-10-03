# ADR-0020: The Current Database Is the Only Working Database

- Status: accepted (user ruling 2026-09-28)
- Date: 2026-09-28

## Context

The original cutover plan kept the legacy Starfall collection as a live, independently-changing source: development imports were one-way and incremental, and a final delta import at cutover would both complete the migration and serve as the recovery path if the campaign database ever had to be rebuilt. In practice the migration never went smoothly — no sensible one-time operation was ever built, and the process has been piece meal and remains unfinished to this day (the orphaned-claims population is part of that unfinished state). The legacy collection itself stopped changing once migration began; the "live source" framing existed to mitigate a fail state, not because the source was still moving.

Sean's ruling (2026-09-28): **abandon backward compatibility with the original source. The current campaign database is the only working database.**

## Decision

1. No further imports from the legacy collection are planned or required. The final-delta-import cutover step is retired.
2. The campaign PostgreSQL database is the single source of truth for campaign data. Its recovery story is **database backups**, not re-import from source.
3. The legacy collections (`E:\studio\starfall`, `\\HOMESERVER\projects\projects\starfall`, the OpenClaw workspace) remain **read-only historical reference** — evidence of origin, usable for comparison and provenance questions — but are no longer a future input to the canonical store.
4. The unfinished migration state (orphaned claims, zero-claim entities, wrong-owner claims) is resolved **forward, inside the current database**, through the existing reviewed surfaces — never by re-running an import.

## Consequences

- The failed-migration-state class has no new producers. Cleanup of the existing population (TKT-0138) is FINITE, not a standing review; the Qualified audit's Q3 (ownership) flips to computed as the permanent guard, so any future ownerless claim is a regression signal, not a queue entry.
- Ongoing capture surfaces (Lore, Brainstorm, Sessions, Encounters) must resolve claim ownership at promotion time — ownerless-claim creation stops being an accepted intermediate state (tracked as its own ticket).
- The importer machinery stays (direct input capture and session notes use it), but its role is the port of entry for NEW material, never a re-migration tool.
- The `docs/plan.md` cutover principle is superseded: the legacy-write-freeze/delta-import/parity-check sequence no longer applies; the backup/rollback half remains as ordinary operational practice.

## Alternatives considered

- **Keep the re-import path as disaster recovery** — rejected: it never worked as a one-time operation, maintaining compatibility with a frozen source is ongoing cost, and database backups are the honest recovery mechanism for a database that is the product.
- **Finish a bulk re-migration with correct ownership** — rejected: reworking the import machinery to fix what reviewed in-database surfaces can fix forward adds no value.
