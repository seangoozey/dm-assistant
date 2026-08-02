# Current-System Migration Notes

## Source

The importer specification was originally audited against the snapshot at `E:\studio\starfall`, which contained approximately 174 files, including 168 Markdown files. That snapshot remains historical evidence rather than current campaign data.

The current live collection is `\\HOMESERVER\projects\projects\starfall`. It is authoritative for confirming the legacy campaign corpus and will continue changing until replacement cutover. Access it strictly read-only and provide its location through environment configuration rather than domain logic.

The old system workspace at `\\HOMESERVER\openclaw\.openclaw\dnd-workspace` may be consulted for historical workflows, scripts, prompts, and failure evidence. It is not campaign truth, and its nested Starfall copy is a historical snapshot unless separately verified.

## Owner-verified live import scope

The live importer considers only `encounters`, `gm`, `handouts`, `locations`, `lore`, `npcs`, `pcs`, `sessions`, and `templates`. The `art`, `backups`, `foundry`, and `inbox` folders are not relevant to this import. Root files, `memory`, and any other unlisted top-level paths are likewise outside the connector allowlist.

Within `gm`, `location-evidence/**` and `location-migration-inventory.md` contain derived migration material and need no import consideration. Skip them before reading or hashing content. `gm/campaign-bible.md` is part of v0.1 and may contain uningested data; admit it as section-aware planning evidence, not automatic canon. Templates remain in the managed live tree but must never import as live campaign records.

## Existing authority order

1. Session notes establish table canon.
2. Lore, locations, NPCs, and PCs hold durable canon.
3. Encounters are prepared scenarios.
4. Session prep is planned material.
5. GM brainstorming is non-canon.
6. Handouts are canonical player artifacts.
7. Foundry exports are derived, but the live Starfall importer does not ingest the `foundry` folder.
8. Inbox material is outside the verified import scope.

## Major migration risks

- Document-level canon is too coarse; individual files mix established facts, intentions, plans, and possibilities.
- Most session notes have not been propagated into durable canon records.
- Promoted brainstorm receipts may have replaced original working material.
- Templates resemble live records.
- Unknown content inside an admitted folder could contaminate retrieval.
- Some links use stale identifiers or misspellings.
- PC dossiers contain campaign-shaping plans that must not become predicted PC actions.
- Large documents require section-aware parsing.

## Import policy

- Preserve raw source and hashes.
- Apply the owner-verified path allowlist before content reads, hashing, parsing, or quarantine.
- Exclude templates as live records.
- Quarantine unclassified material only when it occurs inside an admitted path.
- Treat session notes as higher-authority evidence when reconciling durable records.
- Detect additions, edits, moves, and possible deletions incrementally.
- Never translate source absence into automatic deletion.
- Re-importing unchanged sources must not duplicate claims.

## Development import status

The first live evidence import was submitted to the local development Campaign database on 2026-08-01. The aggregate-only preflight matched the earlier audited dry run: 143 admitted files, 405 non-canonical candidates, 9 excluded paths encountered, 10 template exclusions, 2 navigation exclusions, and 8 quarantined files. Campaign Core stored one immutable import run, 143 source documents and revisions, 405 candidates, 143 observations, and 125 open review items. An exact in-memory replay returned the original receipt. Canonical entity, claim, and relationship counts remained zero.

The operation compared admitted path, content-hash, and filesystem-time signatures before and after submission and found no source change. A custom-format logical baseline backup was created outside Git and structurally validated before import. Recovery must restore that archive into a new database, validate it independently, and redirect Campaign Core only after review; never overwrite the evidence-bearing database in place.

## Required fixtures

- Mixed canon and plans in an NPC record.
- PC record containing private campaign direction.
- Location record.
- Campaign-bible planning record that cannot establish canon from its path.
- Unreviewed and applied session notes.
- Promoted brainstorm receipt.
- Session preparation and encounter read-alouds.
- Excluded top-level and derived-`gm` paths, plus unknown content inside an admitted path.
- Stale-link record.
- Partial legacy chat dump showing unauthorized promotion and invented lore.
