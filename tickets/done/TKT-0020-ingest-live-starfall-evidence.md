---
id: TKT-0020
title: Ingest live Starfall evidence into development
status: done
priority: P1
milestone: trustworthy-librarian
depends_on: [TKT-0016, TKT-0018, TKT-0019]
created: 2026-08-01
updated: 2026-08-01
---

# TKT-0020: Ingest Live Starfall Evidence Into Development

## Outcome

Run the production Markdown connector against the owner-verified live Starfall collection and persist one audited, repeatable evidence import in the local development Campaign database without creating canonical campaign records.

## Context

The connector and its live path policy are implemented. A prior read-only dry run admitted 143 files and produced 405 non-canonical candidates in memory, but no live batch has been submitted to Campaign Core. The current UI therefore correctly returns `insufficient_evidence` from an empty development database.

Read `docs/migration/markdown-importer.md`, `docs/migration/current-system.md`, `docs/testing/importer-fixtures.md`, TKT-0014, TKT-0016, and TKT-0018.

## Scope

- Use `\\HOMESERVER\projects\projects\starfall` as a strictly read-only connector root from the host.
- Run and record an aggregate-only dry run before submission.
- Preserve a logical baseline backup of the development Campaign database outside Git.
- Submit the exact reviewed scan to the local Campaign Core endpoint.
- Repeat the scan to prove idempotency and record aggregate receipt evidence.
- Verify exclusions, template/index handling, quarantine counts, and zero canonical mutations.

## Out of scope

- Editing, reorganizing, or cleaning the live collection.
- Promoting any candidate to canonical truth.
- Committing private prose, raw hashes, database dumps, or production receipts to Git.
- Treating `gm/campaign-bible.md` as established evidence.

## Acceptance criteria

- [x] The live root is accessed read-only and no source timestamp, byte, path, or metadata changes.
- [x] The aggregate dry-run result is reviewed against the versioned path policy before submission.
- [x] Excluded top-level roots and derived `gm` paths are pruned before reads; templates and indexes create no live candidates.
- [x] Campaign Core records one immutable import receipt and the expected source revisions, candidates, reviews, and quarantine outcomes.
- [x] An exact retry returns the original receipt without duplicate revisions or candidates.
- [x] Canonical entity, claim, and relationship counts remain unchanged.
- [x] Baseline backup, validation evidence, and non-destructive recovery instructions are recorded without committing private data.

## Validation evidence

- The aggregate-only preflight exactly matched the earlier audited live dry run: 143 admitted files, 405 candidates, and 9 excluded paths encountered.
- Classifications were 57 durable evidence, 44 real-play evidence, 10 templates, 9 preparation, 8 quarantine, 5 non-canon evidence, 4 canonical artifacts, 3 planned preparation, 2 navigation indexes, and 1 planning-evidence file.
- Proposed outcomes were 118 new, 10 template-excluded, 8 quarantined, 5 review-required, and 2 navigation-excluded.
- Campaign Core persisted one immutable run with 143 source documents, 143 revisions, 143 observations, 405 candidates, and 125 open review items. Reviews comprise 112 warning reviews, 8 quarantine reviews, and 5 import reviews.
- Templates and navigation indexes produced zero candidates. The receipt contained zero canonical change-set IDs.
- The identical in-memory batch was submitted twice. The first call was new; the second reported an idempotent replay with the same import-run ID and no duplicate rows.
- Aggregate database counts after import were zero entities, zero claims, and zero relationships.
- A second read-only scan compared every admitted normalized path, SHA-256, and filesystem modification time with the submitted batch; the signatures were identical.
- No private prose, source hashes, dump bytes, or full receipt payloads were written to the repository.
- The full deterministic repository gate passes: 101 Python tests, 10 React tests, 38 retrieval cases, Ruff, mypy, strict TypeScript, infrastructure policy, and the Windmill raw-app build.

## Backup and recovery

Before submission, a PostgreSQL custom-format baseline archive was written outside Git. `pg_restore --list` successfully parsed 174 archive entries. The validated archive was then copied to `C:\Users\Sean\Documents\DM Assistant Backups\2026-08-01-tkt20\campaign-baseline.dump`; its hash matches the original temporary copy, but the hash itself is not committed.

Recovery is non-destructive: create a new Campaign database, restore the baseline archive into it with `pg_restore --no-owner`, run health and count checks against the restored database, and change Campaign Core's database URL only after review. Do not drop or overwrite the evidence-bearing database as a rollback shortcut.

## Follow-up

TKT-0021 exposes the now-populated import receipts, candidate evidence, quarantine, and review queues through typed Campaign Core reads. No candidate may be promoted before that review boundary and the later exact proposal workflow exist.
