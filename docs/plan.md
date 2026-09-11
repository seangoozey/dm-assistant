# Development Plan

## Next execution priority: shared campaign knowledge

2026-09-10 execution refinement: TKT-0102 → TKT-0103 → TKT-0104 → TKT-0105 stages the next work within existing TKT-0090/0091/0092/0094/0096 scope. Define task-dependent truth-aware relevance and freeze comparative tests; build clean evidence-linked indexing; evaluate native Cognee retrieval instead of the exported JSON walker; then make a measured retention/Neo4j decision. Grouping is deferred until relevance works. Truth remains categorical evidence metadata; query-time suitability is one scoring component, never permission to promote plans or bypass visibility/freshness. TKT-0095 integrates accepted retrieval across consumers afterward. Ticket creation does not deploy pending heuristic changes or authorize a backend migration.

TKT-0089 defines the [shared relationship and retrieval layer](architecture/shared-campaign-knowledge.md) for all workflows. Implement TKT-0090 (benchmark), TKT-0091 (comparison policy), TKT-0092 (projection), TKT-0093 (optional links), TKT-0094 (shared retrieval), and TKT-0095 (consumer integration), in dependency order. TKT-0096 evaluates Cognee and alternate graph backends against the resulting contract. This is the next execution priority; older milestone descriptions below are historical planning context, not instructions to prioritize more isolated UI lookup work.

This plan is the maintained execution summary. The earlier, more narrative [DM Assistant App Planning Document](reference/DM%20Assistant%20App%20Planning%20Document.docx) is retained as a planning baseline and source of historical context. If they disagree, the current Markdown specifications, accepted ADRs, and completed tickets take precedence.

## Current milestone: trustworthy librarian live-data onboarding

The specification, persistence, importer, retrieval, Windmill, live evidence import, review read model, human-controlled candidate commands, narrow React review workflow, first scoped canonical promotion, campaign-bible coverage audit, path-aware wiki-link resolution, calendar-neutral chronology, and structured rules elements with export profiles are implemented and validated. Import remains non-canonical until explicit review and exact approval.

### Exit criteria

- One read-only live import has an immutable, idempotent receipt in the development database.
- Import receipts, candidates, quarantine, and review items are inspectable through Campaign Core.
- Exact candidate proposals, rejection/defer actions, versioned approval, and atomic application are available through typed commands.
- The React app exposes a narrow evidence-review and scoped-promotion workflow.
- A representative live fact set has been promoted with receipts and retrieved with exact citations.
- `gm/campaign-bible.md` has section-level coverage and explicit planning dispositions without default canon promotion.

### Completed tranche

1. TKT-0020 ingested live evidence without canonical mutation.
2. TKT-0021 exposed the import receipt and review read model.
3. TKT-0022 added exact proposal, disposition, and approval commands.
4. TKT-0023 built the narrow React review/promotion slice.
5. TKT-0024 completed the first scoped live promotion and grounded retrieval proof; TKT-0026 completed the proposal-comparison field fix discovered during that exercise.
6. TKT-0025 completed the campaign-bible planning coverage audit, and TKT-0027 completed nested parser-version-aware re-extraction without promoting planning material.
7. TKT-0029 completed the shared referenceable-record identity and kind registry, minimal entity vocabulary migration, PC/NPC agency boundaries, optional extensible tags, exact metadata proposals, and auditable kind evolution.
8. TKT-0031 completed first-class plans with explicit agency/lifecycle boundaries. TKT-0030 completed calendar-neutral campaign chronology with integer-year storage and a hardcoded Gregorian calendar spec (ADR-0007). TKT-0028 completed path-aware wiki-link target resolution. TKT-0032 completed structured rules elements and the Markdown-card derived-artifact export profile.

## Current milestone: planning workspace and direct capture

The provider, grounded extraction pipeline, context-aware extraction validation, source-document browser, and guided editable migration workflow are implemented. Direct capture and the primary thinking workflows (Brainstorm and Lore Entry) follow; chronology and deferred precision/plan-review work form a parallel track.

### Ordered ticket tranche

1. TKT-0033, TKT-0034, and TKT-0035 completed the AI provider, grounded extraction harness, and assertion-to-canon baseline pipeline.
2. TKT-0036, TKT-0037, and TKT-0046 completed the source-document browser, initial migration workspace, and page-based navigation.
3. TKT-0045 completed extraction-context tests and representative PC, NPC, and location validation.
4. TKT-0047 completed the step-based, editable migration workflow and corrected-value proposal prefill.
5. TKT-0038 adds direct input capture so a DM can submit free text without a Markdown source.
6. TKT-0039 builds the Brainstorm workspace; TKT-0040 builds Lore Entry with conflict-gated application.
7. TKT-0041 makes chronology queryable; TKT-0042 builds the timeline view on top of it.
8. TKT-0043 closes the failed-plan review-queue invariant gap; TKT-0044 adds the date-precision vocabulary deferred from TKT-0030.
## Milestone 1: trustworthy librarian

- Private TrueNAS Compose stack.
- Campaign Core skeleton and migrations.
- Windmill Community Edition and local CLI deployment.
- Read-only, repeatable Markdown importer.
- Source hashing, identity matching, and import receipts.
- Structured entities, claims, relationships, sources, and provenance.
- Lexical retrieval baseline and exact citations.
- Canon-versus-planning filters.
- Full-code React shell and grounded `/ask` experience.

Success: the system retrieves correct information without treating brainstorm or preparation as observed canon.

## Milestone 2: planning workspace

- Two-panel Brainstorm and Lore Entry interface.
- Continuously refreshed supporting and contradictory context.
- Versioned proposals with exact affected records.
- Scoped approval, rejection, and promotion receipts.
- Initial continuity checks.
- Direct audio upload, transcript preservation, and Audio Brainstorm synthesis.

## Milestone 3: session support

- Session preparation.
- Encounter runner and requested read-alouds.
- Dedicated Real Play environment.
- Automatic unambiguous updates with receipts.
- Retcon and timing comparison workflow.
- Manicured near-verbatim session logs.
- Failed-plan review queue.

## Milestone 4: deliverables and richer model

- Typed relationships and richer chronology.
- Versioned deliverable framework.
- Foundry VTT export proof of concept.
- Optional campaign calendar.
- Deeper Cognee integration if testing shows value.
- Google Recorder or intermediary connector after access verification.

## Cutover principle

The legacy system remains active until the replacement reaches feature and reliability parity. Development imports are one-way and incremental. Final cutover requires a brief legacy-write freeze, final delta import, parity checks, backup, and rollback plan.
