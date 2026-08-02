---
id: TKT-0006A
title: Confirm Markdown importer specification against live Starfall data
status: done
priority: P1
milestone: trustworthy-librarian
depends_on: [TKT-0006]
created: 2026-07-31
updated: 2026-08-01
---

# TKT-0006A: Confirm Markdown Importer Specification Against Live Starfall Data

## Outcome

Confirm that the incremental Markdown importer specification remains correct against the current live Starfall collection after this repository is moved to the environment where that collection is held.

## Context

TKT-0006 was specified and reviewed using the local `E:\studio\starfall` snapshot. That snapshot is not current campaign data. The live collection at `\\HOMESERVER\projects\projects\starfall` is authoritative for importer confirmation, but remains strictly read-only throughout this work. Its path must be supplied through external configuration rather than domain logic.

## Scope

- Configure the live Starfall path outside domain logic.
- Perform read-only inventory and representative sampling of live files.
- Compare live folder/type/frontmatter patterns against `docs/migration/markdown-importer.md`.
- Confirm template exclusion, mixed-status parsing, PC-agency treatment, promoted brainstorm receipts, unclassified-content quarantine, stale-link warnings, and missing-source review behavior.
- Record any specification discrepancy as a targeted amendment or follow-up ticket.

## Out of scope

- Writing to, cleaning up, or reorganizing the live Starfall collection.
- Importing live data into a canonical campaign database.
- Changing importer implementation before the confirmation findings are reviewed.

## Acceptance criteria

- [x] Live source path and access mode are documented; access is read-only.
- [x] Live inventory is compared with the snapshot assumptions used by TKT-0006.
- [x] Required representative categories are sampled from live records.
- [x] Every difference affecting importer behavior has a documented resolution, specification amendment, or follow-up ticket.
- [x] Validation evidence identifies the live snapshot/revision without copying private source content into this repository.

## Validation

All checks used direct read operations against `\\HOMESERVER\projects\projects\starfall`. No source file, directory, timestamp, attribute, or ACL was changed. The root was supplied to the audit process at runtime and was not embedded in domain logic.

### Snapshot identity and growth

The final two consecutive scans completed on 2026-08-01 and produced the same content manifest:

```text
files: 221
Markdown files: 205
content manifest SHA-256: 950cbb7464d81c21b23e90724ed6c6b7cf61bf1c2e3aed1c674a8187b91b94a9
latest source mtime: 2026-08-01T16:00:14.591975Z
```

The manifest hashes each file once with SHA-256, sorts normalized relative paths case-insensitively, and hashes `(relative path, byte length, content hash)`. Two consecutive manifests matched. The live collection has 47 more files and 37 more Markdown files than the TKT-0006 snapshot assumption of approximately 174 files and 168 Markdown files.

Extensions were 205 `.md`, 9 `.gz`, 6 `.json`, and 1 `.log`. No symlink/reparse files, case-folded path collisions, Unicode-normalized path collisions, or duplicate-content groups were found.

### Structural parsing

Of 205 Markdown files, 173 had delimited frontmatter, 172 parsed as YAML mappings, 1 durable-lore file had invalid YAML frontmatter, and 32 had no frontmatter. The existing warning rule correctly handles invalid or absent frontmatter without granting authority.

A deterministic application of the then-current, inventory-inferred classification rules accounted for all 221 files. These outcomes record what the audit observed; the owner-verified scope below supersedes them as importer policy.

| Outcome | Count |
| --- | ---: |
| Real-play candidates | 45 |
| Durable-record candidates | 63 |
| Prepared candidates | 12 |
| Handout review candidates | 4 |
| Non-canon brainstorm records | 5 |
| Non-canon migration evidence | 32 |
| Derived Foundry records | 6 |
| Templates excluded | 10 |
| Backup containers recorded without extraction | 9 |
| Navigation indexes recorded without claims | 5 |
| Quarantined | 30 |

The provisional quarantined set consisted of inbox/unclassified material and isolated root, art, memory, archived-session, GM working, and operational files. TKT-0014 later established that content outside the owner-verified allowlist must be skipped before quarantine rather than imported as a quarantined source.

### Owner-verified scope correction

After the structural audit, the campaign owner confirmed that only `encounters`, `gm`, `handouts`, `locations`, `lore`, `npcs`, `pcs`, `sessions`, and `templates` contain live data relevant to this importer. `art`, `backups`, `foundry`, `inbox`, root files, `memory`, and any other unlisted top-level paths are outside its source scope.

Within `gm`, `location-evidence/**` and `location-migration-inventory.md` are derived and need no import consideration. `gm/campaign-bible.md` is part of v0.1 and may contain uningested data, so it remains admitted as planning evidence. Templates are admitted only far enough to enforce their exclusion and never create live campaign records.

The same 221-path inventory divides into 177 paths under the included top-level roots and 44 paths outside them. Of the 177, 34 are under the two excluded derived `gm` paths and 10 are templates, leaving 133 paths eligible for ordinary classification. Later classification can still exclude navigation indexes or quarantine ambiguity within those admitted paths. These counts describe the audited snapshot and do not hard-code a required live count.

### Representative category findings

- All 10 template documents resemble live record types, confirming that path-based template exclusion must precede frontmatter classification.
- The 18 NPC documents include canonical status plus planning/goal sections; 2 include explicit private-GM sections. Claim-level state and visibility parsing remains required.
- All 4 PC documents include private-GM sections, confirming that campaign direction must remain DM-only `prepared` or `possible` rather than future PC action.
- The live session set contains 44 standard `session-note` records and 1 legacy `type: session` plus `status: note` record under `sessions/notes`. Reviewed, needs-review, draft, applied-delta, and unresolved-delta patterns remain distinct.
- The 3 session-prep records include recap and expected-outcome structures; the 9 encounters include possible outcomes and read-aloud sections. Neither category establishes observed play.
- Five live brainstorm records contain promotion receipts. They remain non-canon audit provenance and cannot re-promote their summaries.
- The audit found derived location-migration material, but the later owner verification excludes `gm/location-evidence/**` and `gm/location-migration-inventory.md` before content processing.
- Four handouts remain canonical artifacts whose extracted facts require review. The observed Foundry files are outside this import's owner-verified path scope.
- The unrelated memory record remains present but is outside this connector's allowlist rather than quarantined.
- The live corpus contains 641 wiki links: 608 resolved structurally and 33 were unresolved across 26 distinct targets. Sixteen unresolved links occur in excluded templates; those are diagnostics rather than campaign review items. Other unresolved links remain stale-link warnings without invented targets.

### Specification differences and resolutions

| Live difference | Resolution |
| --- | --- |
| Nine backup archives exist under `backups/`. | Initially specified for metadata-only inventory; superseded by the owner's instruction to exclude `backups` before content processing. |
| Five navigation/index documents can otherwise resemble canonical records. | Added a hard navigation-index exclusion before durable path classification. |
| Applied location evidence is explicitly non-canon but retains processing metadata. | Initially classified as non-canon evidence; superseded by the owner's instruction to exclude `gm/location-evidence/**` and `gm/location-migration-inventory.md`. |
| One session note uses legacy `type: session` and `status: note`. | Added a narrow legacy mapping that is automatic only under `sessions/notes`. |
| Template/index placeholder links create warning noise. | Limited their broken links to source diagnostics rather than campaign review items. |
| The audited `E:\studio\starfall` manifest is unavailable here, and the historical OpenClaw `starfall` directory is empty. | TKT-0013 adds a synthetic repeated/changed/moved/missing fixture sequence. Without a retained prior manifest, this scan authorizes no missing-source or deletion action. |

`docs/migration/markdown-importer.md` contains the original targeted amendments plus the owner-verified correction from TKT-0014. TKT-0013 tracks executable sanitized importer fixtures. No importer implementation or canonical database mutation occurred.

## Follow-ups

- TKT-0013 builds executable sanitized fixtures for the confirmed structures and synthetic manifest-delta behavior.
- TKT-0014 records the later owner-verified path scope that supersedes provisional inventory classifications.
- Validate the read-only live source mount through its native TrueNAS dataset path during TKT-0007.
- Retain manifests for future scans so real additions, changes, moves, and missing paths can be compared without inferring deletion.
