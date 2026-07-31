# Incremental Markdown Importer Specification

The importer reads a Starfall snapshot and submits only reviewed, idempotent candidate changes to Campaign Core. It never writes legacy files and never receives direct canonical-table credentials.

## Discovery and source versions

1. Start from an explicitly configured, read-only root; reject symlink escapes and paths outside that root.
2. Walk files deterministically by normalized relative path. Accept `.md`; record other recognized formats (such as Foundry JSON) as derived candidates; quarantine everything else unless a connector policy explicitly permits it.
3. Read bytes once, calculate SHA-256, preserve exact bytes/text, path, filesystem timestamps, frontmatter, importer version, and discovery time in an immutable `source_revision`.
4. An unchanged `(source_document_id, content_hash)` produces `unchanged`, creates no source revision, and creates no candidate claims.
5. Parse frontmatter only when valid YAML between opening delimiters. Invalid or missing frontmatter is a warning, not permission to guess classification.

## Classification

Classification uses a configured path rule first, then a consistent frontmatter rule. A conflict is quarantined for review rather than resolved by precedence.

| Path/frontmatter evidence | Classification | Import result |
| --- | --- | --- |
| `templates/**` | template | Preserve source metadata only; never create entities, claims, or retrieval chunks. |
| `sessions/notes/**` or `type: session-note` | real-play evidence | Parse section-aware observed claim candidates; retain original note. |
| `lore/**`, `npcs/**`, `pcs/**`, `locations/**` with durable-canon markers | durable evidence | Parse claim and relationship candidates; do not assume every section shares one state. |
| `encounters/**` or `type: encounter` | preparation | Parse prepared scenarios/read-alouds; no observed claims. |
| `sessions/prep/**` or `type: session-prep` | planned preparation | Parse planned claims separately from quoted/referenced historical recap. |
| `gm/brainstorming/**` or `type: brainstorm` | non-canon evidence | Import `possible`/receipt provenance only; promoted receipts do not re-promote claims. |
| `handouts/**` | canonical artifact | Preserve exact artifact text; extract durable facts only as reviewable candidates. |
| `foundry/**` or recognized export JSON | derived artifact | Preserve and link only; cannot establish campaign truth. |
| `inbox/**`, `memory/**`, unknown directory/type, or unrelated content | quarantine | Preserve raw source, warning, and classification rationale; exclude from normal retrieval. |

`memory/2026-06-08.md` is the representative unrelated-content fixture. A session-prep document is the representative mixed-status fixture: recap is evidence with its cited session source, while `Expected Outcomes` remains `prepared`.

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

## Reconciliation and deletion safety

For each changed source revision, Campaign Core compares candidate fingerprints `(source_span, normalized assertion, state, target)` with prior candidates from that source document.

- Matching fingerprints are retained with updated evidence linkage, not duplicated.
- New candidates are submitted as a scoped import change set or review item according to authority/conflict rules.
- Removed candidates are marked `source_removed` in provenance; they never delete, supersede, or downgrade canonical claims automatically.
- A source path missing from a later scan creates a `missing_source` review item after a configurable confirmation threshold. Its existing source revisions, claims, and entity links remain intact.
- Conflicts, low confidence, classification ambiguity, unresolved links, possible moves, and unknown file types are quarantined or reviewed before normal retrieval.

## Import receipt

Every run creates one immutable `import_run` receipt, including root identifier, snapshot time, importer/parser versions, file count, hashes, and one outcome per discovered or previously tracked path:

`new`, `unchanged`, `changed`, `possible_move`, `missing_source`, `template_excluded`, `derived_recorded`, `quarantined`, `review_required`, or `failed`.

The receipt lists source-document/revision IDs, extracted candidate IDs, canonical change-set IDs when any, warnings, errors, and retry/idempotency keys. Repeating the run against the same root snapshot returns the prior equivalent outcomes without duplicate source revisions, candidates, entities, or claims.

## Required importer fixtures

Automated importer tests must use sanitized fixtures for: a mixed NPC document, a PC with campaign-sculpting notes, a location plus associated evidence, unreviewed and applied session notes, a promoted brainstorm receipt, session prep and encounter read-alouds, unrelated memory content, a stale link, and a repeated/moved/missing source sequence.
