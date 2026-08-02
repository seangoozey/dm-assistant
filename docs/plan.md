# Development Plan

This plan is the maintained execution summary. The earlier, more narrative [DM Assistant App Planning Document](reference/DM%20Assistant%20App%20Planning%20Document.docx) is retained as a planning baseline and source of historical context. If they disagree, the current Markdown specifications, accepted ADRs, and completed tickets take precedence.

## Current milestone: trustworthy librarian live-data onboarding

The specification, persistence, importer, retrieval, Windmill, live evidence import, review read model, human-controlled candidate commands, narrow React review workflow, first scoped canonical promotion, and campaign-bible coverage audit are implemented and validated. The audit identified focused parser-remediation work without promoting planning material. Import remains non-canonical until explicit review and exact approval.

### Exit criteria

- One read-only live import has an immutable, idempotent receipt in the development database.
- Import receipts, candidates, quarantine, and review items are inspectable through Campaign Core.
- Exact candidate proposals, rejection/defer actions, versioned approval, and atomic application are available through typed commands.
- The React app exposes a narrow evidence-review and scoped-promotion workflow.
- A representative live fact set has been promoted with receipts and retrieved with exact citations.
- `gm/campaign-bible.md` has section-level coverage and explicit planning dispositions without default canon promotion.

### Ordered ticket tranche

1. TKT-0020 ingests live evidence without canonical mutation.
2. TKT-0021 exposes the import receipt and review read model.
3. TKT-0022 adds exact proposal, disposition, and approval commands.
4. TKT-0023 builds the narrow React review/promotion slice.
5. TKT-0024 completed the first scoped live promotion and grounded retrieval proof; TKT-0026 completed the proposal-comparison field fix discovered during that exercise.
6. TKT-0025 completed the campaign-bible planning coverage audit, and TKT-0027 completed nested parser-version-aware re-extraction without promoting planning material.
7. TKT-0029 is ready to establish minimal non-overlapping entity types, explicit intent ownership, optional extensible tags, and the corresponding app controls and documentation.
8. TKT-0030 follows with calendar-neutral campaign chronology, a strict audit-time/in-game-time separation, and anchored legacy negative-year normalization. TKT-0028 remains the separate path-aware wiki-link resolution follow-up.

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
