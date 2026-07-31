# Development Plan

This plan is the maintained execution summary. The earlier, more narrative [DM Assistant App Planning Document](reference/DM%20Assistant%20App%20Planning%20Document.docx) is retained as a planning baseline and source of historical context. If they disagree, the current Markdown specifications, accepted ADRs, and completed tickets take precedence.

## Current milestone: specification foundation

The project is not ready for schema or UI implementation until its truth rules can be expressed as acceptance tests.

### Exit criteria

- Truth states and authority precedence are specified.
- PC-agency and temporal rules have executable examples.
- The partial legacy chat dump has been converted into interaction fixtures.
- Representative Starfall files have expected import results.
- Proposal versioning, confirmation scope, and transactional promotion are specified.

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
