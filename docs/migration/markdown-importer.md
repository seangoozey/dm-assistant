# Incremental Markdown Importer Specification

The importer reads a Starfall snapshot and submits only reviewed, idempotent candidate changes to Campaign Core. It never writes legacy files and never receives direct canonical-table credentials.

## Discovery and source versions

1. Start from an explicitly configured, read-only root; reject symlink escapes and paths outside that root.
2. Apply the owner-verified Starfall path policy before walking or reading descendant files. The included top-level roots are `encounters`, `gm`, `handouts`, `locations`, `lore`, `npcs`, `pcs`, `sessions`, and `templates`. Skip `art`, `backups`, `foundry`, `inbox`, every other unlisted top-level path, `gm/location-evidence/**`, and `gm/location-migration-inventory.md` before content hashing, parsing, quarantine, or source-document creation.
3. Record only that each configured excluded path was encountered; do not descend into excluded directories or create per-file outcomes for them. Changing the allowlist or exclusions requires an explicit, reviewed connector-policy version.
4. Walk admitted files deterministically by normalized relative path. Accept `.md`; quarantine an unknown format inside an admitted path unless a reviewed connector policy explicitly permits it.
5. Read admitted bytes once, calculate SHA-256, preserve exact bytes/text, path, filesystem timestamps, frontmatter, importer version, path-policy version, and discovery time in an immutable `source_revision`.
6. An unchanged `(source_document_id, content_hash, parser_version)` produces `unchanged` and creates no source revision or candidate claims. A parser upgrade does not implicitly reparse every unchanged document in a full-root scan. The operator must explicitly scope unchanged paths with `--reextract-path`; the first scoped scan with the newer parser produces `reextracted`, records one append-only source-extraction row, reconciles candidates against the same immutable revision, and does not inherit dispositions for changed fingerprints. Unscoped unchanged paths retain their prior extraction until separately selected.
7. Parse frontmatter only when valid YAML between opening delimiters. Invalid or missing frontmatter is a warning, not permission to guess classification.

`gm/campaign-bible.md` is explicitly admitted. It may contain material not ingested by v0.1, but its planning notes do not become established truth merely because the file is in scope. Parse it section by section as reviewable planning evidence under the ordinary authority rules.

## Classification

Classification runs only after discovery-scope exclusions. It applies hard safety exclusions for templates and navigation indexes before ordinary path and frontmatter rules. It then uses a configured path rule followed by a consistent frontmatter rule. A conflict is quarantined for review rather than resolved by precedence.

| Path/frontmatter evidence | Classification | Import result |
| --- | --- | --- |
| `templates/**` | template | Preserve source metadata only; never create entities, claims, or retrieval chunks. |
| `**/00_index.md`, root `00_index.md`, or a `type` ending in `-index` | navigation index | Preserve source metadata and link diagnostics only; never create entities, claims, or normal retrieval chunks from duplicated index summaries. |
| `sessions/notes/**`, `type: session-note`, or legacy `type: session` plus `status: note` | real-play evidence | Parse section-aware observed claim candidates; retain original note. The legacy type/status pair is accepted automatically only under the session-notes path. |
| `lore/**`, `npcs/**`, `pcs/**`, `locations/**` with durable-canon markers | durable evidence | Parse claim and relationship candidates; do not assume every section shares one state. |
| `encounters/**` or `type: encounter` | preparation | Parse prepared scenarios/read-alouds; no observed claims. |
| `sessions/prep/**` or `type: session-prep` | planned preparation | Parse planned claims separately from quoted/referenced historical recap. |
| `gm/brainstorming/**` or `type: brainstorm` | non-canon evidence | Import `possible`/receipt provenance only; promoted receipts do not re-promote claims. |
| `gm/campaign-bible.md` | planning evidence | Parse section-aware `possible`, `prepared`, or `intended` review candidates as supported; never infer `established` or `observed` from the path. |
| `handouts/**` | canonical artifact | Preserve exact artifact text; extract durable facts only as reviewable candidates. |
| Unknown type or unrelated content inside an admitted path | quarantine | Preserve raw source, warning, and classification rationale; exclude from normal retrieval. |

Paths outside the allowlist do not enter quarantine; they are outside this connector's source scope. A session-prep document is the representative mixed-status fixture: recap is evidence with its cited session source, while `Expected Outcomes` remains `prepared`.

## Identity matching

The importer first resolves the source document, then entities mentioned within it.

1. Exact connector external ID or previously seen normalized path resolves the existing source document.
2. For a new path, match an existing source only when a retained stable identifier, exact prior hash, or an explicitly reviewed move record exists.
3. If an old path is absent and a new path has a different hash but matching frontmatter ID, canonical name, and high-overlap body evidence, create a `possible_move` review item. Never merge automatically on name similarity alone.
4. Entity matching uses explicit entity ID, exact normalized alias in the same namespace, then a reviewed candidate list. Ambiguous aliases create an identity review item.
5. A source move adds a new source revision/path history to the existing source document. It does not change entity IDs or duplicate imported claims.

## Section-aware parsing

The parser builds a heading tree, block spans, links, frontmatter fields, tables, and fenced/code sections. For each candidate it records source span, extractor rule/version, target entity candidates, state, authority, visibility, time values, and confidence.

- Do not create a candidate from placeholders such as `[Not yet established.]`.
- Preserve prose when no safe predicate/object decomposition exists.
- `Private GM Notes` in PC records become DM-only `prepared` or `possible` planning candidates; they must not assert future PC actions.
- Session notes produce `observed` candidates only for statements of what happened; unresolved `Canon Deltas` are not imported as applied truth.
- Brainstorm promotion receipts are evidence of prior promotion and audit history. Their summaries can be matched to already-imported owning records but cannot create a second claim.
- Resolve wiki links to source documents when exact path/alias matching succeeds; retain unresolved or stale links as warnings rather than inventing targets.
- Broken placeholder links inside excluded templates or navigation indexes remain source diagnostics and do not create campaign review items.

## Reconciliation and deletion safety

For each changed source revision, Campaign Core compares candidate fingerprints `(source_span, normalized assertion, state, target)` with prior candidates from that source document.

- Matching fingerprints are retained with updated evidence linkage, not duplicated.
- New candidates are submitted as a scoped import change set or review item according to authority/conflict rules.
- Removed candidates are marked `source_removed` in provenance; they never delete, supersede, or downgrade canonical claims automatically.
- A source path missing from a later scan creates a `missing_source` review item after a configurable confirmation threshold. Its existing source revisions, claims, and entity links remain intact.
- Conflicts, low confidence, classification ambiguity, unresolved links, possible moves, and unknown file types are quarantined or reviewed before normal retrieval.

## Import receipt

Every run creates one immutable `import_run` receipt, including root identifier, snapshot time, importer/parser/path-policy versions, admitted file count, hashes, configured excluded paths encountered, and one outcome per admitted discovered or previously tracked path:

`new`, `unchanged`, `changed`, `reextracted`, `moved`, `possible_move`, `missing_source`, `template_excluded`, `navigation_excluded`, `quarantined`, `review_required`, or `failed`.

The receipt lists source-document/revision IDs, extracted candidate IDs, canonical change-set IDs when any, warnings, errors, and retry/idempotency keys. Repeating the run against the same root snapshot returns the prior equivalent outcomes without duplicate source revisions, candidates, entities, or claims.

Open import-warning, quarantine, and classification reviews are reused when a later scan reports the same source condition. If an older importer run already created a duplicate review, preserve it as `superseded` audit history; default review queues omit superseded rows, while an explicit `status=superseded` query can inspect them.

## Required importer fixtures

Automated importer tests must use sanitized fixtures for: a mixed NPC document, a PC with campaign-sculpting notes, a location, unreviewed and applied session notes, a promoted brainstorm receipt, planning material modeled on the role of `gm/campaign-bible.md`, session prep and encounter read-alouds, an unknown file inside an admitted path, a stale link, path-scope exclusions, and a repeated/moved/missing source sequence.

## Implemented connector boundary

The production connector is `dm_assistant_core.importer`. Its CLI requires an explicit source root, non-path root identifier, versioned importer/parser/path policy, and `--read-only`. It reads admitted bytes once, returns a transport-safe typed batch, and has no PostgreSQL dependency. `--dry-run` prints aggregate counts only. Repeat `--reextract-path <relative-path>` to deliberately apply a new parser to specific unchanged sources while still submitting the complete root scan needed for missing-source safety.

Campaign Core accepts the batch at `POST /imports/markdown/scan`. The Core transaction verifies every supplied hash and path, reconciles stable IDs, path history, exact hashes, possible moves, changed content, and missing sources, and then atomically records immutable revisions, candidates, review items, observations, and the import receipt. Exact retries return the original receipt. No importer operation creates canonical entities, claims, or relationships; reviewed promotion uses `apply_change_set`.

The live collection uses both the fixture-compatible `status: canon` form and the established `canon_status: canon` form. Operational NPC/location values such as alive or active remain separate from truth authority. Section rules recognize explicit established, intended, possible, private-planning, evidence, read-aloud, and session-note headings; unknown or conflicting classification fails into review or quarantine.
