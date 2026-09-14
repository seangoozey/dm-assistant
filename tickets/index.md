# Ticket Index

Update this file whenever a ticket moves or changes scope.

## In progress

- [TKT-0108: Faction roles with unique leadership seats](in-progress/TKT-0108-faction-roles.md) — role catalog + audited assign/clear + ★ UI on the Members block (design agreed 2026-09-13)
- [TKT-0109: Roles page, editor navigation guard, faction template fields, document-link repairs](in-progress/TKT-0109-roles-page-and-link-repairs.md) — Roles page + define-role; editor auto-cancel/force-save; matcher fix drops 16 wrong-page borrows
- [TKT-0111: Entity descriptions as documents, with gathered evidence and AI prose support](in-progress/TKT-0111-entity-descriptions-as-documents.md) — write-description flow files DM prose as entity documents; gathers claims/evidence; extends TKT-0099's draft-from-selected-evidence pattern

## Ready


- [TKT-0098: Compact Brainstorm search categories and discovery cards](in-progress/TKT-0098-brainstorm-search-layout.md) — compact source titles deployed; visual acceptance pending

None.

## Backlog

- [TKT-0103: Clean evidence-linked relationship indexing](backlog/TKT-0103-clean-weighted-relationship-index.md) — after 0102
- [TKT-0104: Native Cognee ranked retrieval evaluation](backlog/TKT-0104-native-cognee-ranked-retrieval.md) — after 0102/0103; grouping deferred
- [TKT-0105: Measured Cognee/Neo4j decision](backlog/TKT-0105-graph-backend-decision.md) — after 0104; no automatic migration

- [TKT-0110: Standing in-app entity/document link audit](backlog/TKT-0110-standing-link-audit.md) — productize the one-off 2026-09-13 traversal into a review surface
- [TKT-0115: Brainstorm truth state — findable prior brainstorm thinking without granting canon](backlog/TKT-0115-brainstorm-truth-state.md) — exploration ticket; sub-canonical 'considered' layer for retrieval, design questions enumerated
- [TKT-0116: Domain glossary with in-app help and definition tooltips](backlog/TKT-0116-domain-glossary-and-tooltips.md) — maintained definitions page + `<Term>` tooltips wherever vocabulary appears
- [TKT-0112: App activity log page](in-progress/TKT-0112-log-page.md) — STARTED 2026-09-13: session bus + identity decision audit merged; other durable sources remain
- [TKT-0113: Global toast notifications with one app-wide event bus](in-progress/TKT-0113-global-toasts.md) — transient outcomes everywhere; scrapes all message/error surfaces; STARTED 2026-09-13 (bus + stack + major surface wiring)
- [TKT-0114: DM settings page on the user menu](backlog/TKT-0114-settings-page.md) — toast/log configurability first, inventory other candidates
- [TKT-0107: In-app graph view of identities and evidence associations](backlog/TKT-0107-in-app-graph-view.md) — deferred by request ("not yet"); renders from Campaign Core canonical data, not Cognee stores; offline live-pilot-v3/graph.html is the visual precedent

- [TKT-0101: Mention and navigate to any library entry](backlog/TKT-0101-mentions-for-all-library-entries.md) — deferred; includes encounters, with reference-only semantics

- [TKT-0100: Shared spellcheck, campaign dictionary, and automatic mention suggestions](backlog/TKT-0100-campaign-spellcheck-and-mentions.md) — deferred; shared prose-editor assistance without silent changes

- [TKT-0099: Lore creation queue with evidence gathering and optional synopsis](backlog/TKT-0099-lore-creation-queue.md) — deferred; Library + capture and a separate visible queue entry point

- [TKT-0097: Review and repair evidence-linked factual conflicts](backlog/TKT-0097-conflict-review-and-repair-surface.md)
- [TKT-0092: Build shared relationship and provenance projection](in-progress/TKT-0092-shared-relationship-projection.md) — 50-claim v3 active and audited; 375 nodes/1,069 edges; billing reconciled; automatic refresh/full coverage pending
- [TKT-0093: Link existing prose to canonical elements without mandatory SPO](backlog/TKT-0093-campaign-entity-link-enrichment.md)
- [TKT-0094: Implement ranked passage and connected evidence retrieval](backlog/TKT-0094-shared-connected-retrieval.md)
- [TKT-0095: Connect every campaign workflow to shared knowledge](backlog/TKT-0095-shared-knowledge-workflow-integration.md)

- [TKT-0040: Lore Entry with conflict-gated direct application](backlog/TKT-0040-lore-entry-conflict-gated-application.md) — P1; depends on TKT-0038, TKT-0091 and TKT-0094
- [TKT-0041: Calendar-aware chronology ordering and current-date config](backlog/TKT-0041-campaign-chronology-ordering.md) — P2; depends on TKT-0030
- [TKT-0042: Timeline view](backlog/TKT-0042-timeline-view.md) — P2; depends on TKT-0041
- [TKT-0043: Failed-plan review queue](backlog/TKT-0043-failed-plan-review-queue.md) — P2; depends on TKT-0031
- [TKT-0044: Date-precision vocabulary and approximate-date handling](backlog/TKT-0044-date-precision-vocabulary.md) — P2; depends on TKT-0030

## In progress

- [TKT-0102: Truth-aware relevance contract and benchmarks](in-progress/TKT-0102-truth-aware-retrieval-contract.md) — isolated policy tests, frozen v1/v2 diagnostic baselines, explicit-bridge corpus; graph_relevance heuristic removed; adapter evaluation pending

- [TKT-0096: Evaluate Cognee and graph retrieval backends against shared contract](in-progress/TKT-0096-knowledge-backend-evaluation.md) — 24-case evidence retrieval run complete; adoption deferred pending Core policy and further comparison; $2 cap
- [TKT-0091: Correct evidence comparison and conflict classification](in-progress/TKT-0091-evidence-comparison-policy.md) — internal scoped path service tested; durable registry and legacy endpoint migration pending
- [TKT-0090: Establish cross-workflow knowledge benchmark](in-progress/TKT-0090-shared-knowledge-benchmark.md)




## Blocked

None.

## Done

- [TKT-0106: Identity review queue](done/TKT-0106-identity-review-queue.md) — COMPLETE 2026-09-13: 281 audited decisions, 118 identities, 91% claim coverage, queue empty

- [TKT-0089: Design the shared campaign relationship and retrieval layer](done/TKT-0089-shared-knowledge-design.md)
- [TKT-0088: Pin all Brainstorm search evidence](done/TKT-0088-pin-all-brainstorm-search-results.md)
- [TKT-0087: Make Brainstorm evidence cards pinnable and searchable at a glance](done/TKT-0087-brainstorm-evidence-cards-and-search-excerpts.md) — P0; depends on TKT-0085 and TKT-0086
- [TKT-0086: Search canonical content within Brainstorm](done/TKT-0086-brainstorm-canonical-content-search.md) — P0; depends on TKT-0085
- [TKT-0085: Add searchable pinned context and entity mentions to Brainstorm](done/TKT-0085-brainstorm-context-tools.md) — P0; depends on TKT-0039 and TKT-0081
- [TKT-0039: Brainstorm workspace vertical slice](done/TKT-0039-brainstorm-workspace.md) — P1; depends on TKT-0038
- [TKT-0084: Preserve real-play sessions across encounter boundaries](done/TKT-0084-real-play-session-continuity.md) — P0; depends on TKT-0038, TKT-0080, and TKT-0082
- [TKT-0038: Direct input capture and evidence-backed candidates](done/TKT-0038-direct-input-capture.md) — P1; depends on TKT-0035
- [TKT-0083: Polish prepared encounters for table use](done/TKT-0083-prepared-encounter-table-polish.md) — P1; depends on TKT-0081 and TKT-0082
- [TKT-0082: Capture chronological table notes from encounter context](done/TKT-0082-chronological-encounter-table-notes.md) — P0; depends on TKT-0038 and TKT-0080
- [TKT-0081: Encounter NPC dossier drawer](done/TKT-0081-encounter-npc-dossier-drawer.md) — P0; depends on TKT-0080
- [TKT-0079: Audit and formally close the live Starfall migration](done/TKT-0079-close-live-migration.md) — P0; depends on TKT-0075, TKT-0076, TKT-0077, and TKT-0078
- [TKT-0078: Merge equivalent claims while retaining all provenance](done/TKT-0078-merge-claims-retain-provenance.md) — P1; depends on TKT-0072
- [TKT-0077: Split and reclassify committed claims through reviewed replacement](done/TKT-0077-revise-committed-claim-dimensions.md) — P1; depends on TKT-0074
- [TKT-0074: Correct committed claims through reviewed replacement](done/TKT-0074-correct-committed-claims.md) — P0; depends on TKT-0072
- [TKT-0073: Project only current claims into curated Documents sections](done/TKT-0073-current-claim-document-projection.md) — P1; depends on TKT-0071 and TKT-0072
- [TKT-0072: Reconcile overlapping claims through reviewed supersession](done/TKT-0072-claim-supersession-reconciliation.md) — P0; depends on TKT-0067
- [TKT-0071: Replace ambiguous conditional flags with explicit claim conditions](done/TKT-0071-explicit-claim-conditions.md) — P0; depends on TKT-0031

- [TKT-0075: Reconcile source-removed candidates through audited dispositions](done/TKT-0075-reconcile-source-removed-candidates.md) — P1; depends on TKT-0067
- [TKT-0076: Supersede stale import reviews after complete scans](done/TKT-0076-supersede-stale-import-reviews.md) — P1; depends on TKT-0016
- [TKT-0070: Correct pending claim proposals before approval](done/TKT-0070-correct-pending-claim-proposals.md) — P0; depends on TKT-0067

- [TKT-0068: Curate PC and NPC profiles before ingestion](done/TKT-0068-curated-character-profiles.md) — P1
- [TKT-0069: Edit curated PC pages from Documents](done/TKT-0069-edit-pc-documents.md) — P1; depends on TKT-0068
- [TKT-0067: Make provenance-first assertions independently promotable](done/TKT-0067-provenance-first-claim-promotion.md) — P1; depends on TKT-0063, TKT-0065, and TKT-0066
- [TKT-0066: Use assertion-first retrieval and conflict detection](done/TKT-0066-assertion-first-retrieval-and-conflicts.md) — P1; depends on TKT-0063, TKT-0064, and TKT-0065
- [TKT-0065: Build assertion-first migration review](done/TKT-0065-assertion-first-review-workflow.md) — P1; depends on TKT-0063 and TKT-0064
- [TKT-0064: Resolve source-backed principal subjects](done/TKT-0064-source-backed-subject-resolution.md) — P1; depends on TKT-0063
- [TKT-0063: Make the complete assertion primary claim content](done/TKT-0063-assertion-primary-claim-model.md) — P1; depends on TKT-0062

## Done

- [TKT-0062: Add corrective extraction retry and failure analysis storage](done/TKT-0062-corrective-retry-and-failure-analysis.md) — P1; depends on TKT-0061 and TKT-0056

- [TKT-0056: Add model selection and prompt tooling](done/TKT-0056-model-and-prompt-tooling.md) — P1; depends on TKT-0055

- [TKT-0055: Evaluate GPT-5 Nano for structured extraction](done/TKT-0055-evaluate-gpt5-nano-extraction.md) — P1; depends on TKT-0054

- [TKT-0061: Retry transient extraction validation failures](done/TKT-0061-bounded-extraction-validation-retry.md) — P1; depends on TKT-0060

- [TKT-0060: Derive exact extraction evidence from source segments](done/TKT-0060-derive-exact-evidence-from-segments.md) — P1; depends on TKT-0059

- [TKT-0059: Canonicalize close AI source excerpts](done/TKT-0059-canonicalize-close-source-excerpts.md) — P1; depends on TKT-0058

- [TKT-0058: Derive extraction segment links deterministically](done/TKT-0058-derive-extraction-segment-links.md) — P1; depends on TKT-0052

- [TKT-0057: Retry failed extractions from Background Tasks](done/TKT-0057-direct-retry-failed-extractions.md) — P1; depends on TKT-0049

- [TKT-0054: Use a non-reasoning model for structured extraction](done/TKT-0054-use-nonreasoning-extraction-model.md) — P1; depends on TKT-0053

- [TKT-0053: Tighten extraction semantic fidelity and subject selection](done/TKT-0053-semantic-fidelity-extraction-prompt.md) — P1; depends on TKT-0052

- [TKT-0052: Add lossless segment-accounted extraction review](done/TKT-0052-lossless-segment-accounted-extraction.md) — P1; depends on TKT-0051

- [TKT-0051: Recover empty provider completions during extraction](done/TKT-0051-recover-empty-provider-completions.md) — P1; depends on TKT-0050

- [TKT-0050: Preserve immutable extraction revisions and report task outcomes accurately](done/TKT-0050-append-only-reextraction-and-task-outcomes.md) — P1; depends on TKT-0049

- [TKT-0049: Durable background AI extraction jobs](done/TKT-0049-durable-background-ai-extraction-jobs.md) — P1; depends on TKT-0048

- [TKT-0048: Focal-entity grounded extraction](done/TKT-0048-focal-entity-grounded-extraction.md) — P1; depends on TKT-0045 and TKT-0047

- [TKT-0047: Migration page step-based workflow](done/TKT-0047-migration-page-step-based-workflow.md) — P1; depends on TKT-0046
- [TKT-0045: Extraction context and prompt improvement](done/TKT-0045-extraction-context-and-prompt-improvement.md) — P1; depends on TKT-0037
- [TKT-0046: Page-based app navigation with document browser](done/TKT-0046-page-based-app-navigation-with-document-browser.md) — P1; depends on TKT-0036
- [TKT-0037: Migration workspace](done/TKT-0037-migration-workspace.md) — P1; depends on TKT-0036
- [TKT-0036: Source document tree view](done/TKT-0036-source-document-tree-view.md) — P1; depends on TKT-0035
- [TKT-0035: Assertion-to-canon baseline pipeline](done/TKT-0035-assertion-to-canon-pipeline.md) — P1; depends on TKT-0034
- [TKT-0034: AI extraction harness with typed contracts and grounding](done/TKT-0034-ai-extraction-harness.md) — P1; depends on TKT-0033
- [TKT-0033: OpenRouter AI provider integration](done/TKT-0033-openrouter-ai-provider-integration.md) — P1
- [TKT-0032: Add structured rules elements and derived artifact export profiles](done/TKT-0032-rules-elements-and-artifact-exports.md) — P2; depends on TKT-0029
- [TKT-0030: Separate audit time from calendar-neutral campaign chronology](done/TKT-0030-calendar-neutral-campaign-time.md) — P1; depends on TKT-0029
- [TKT-0028: Normalize path-aware wiki-link target resolution](done/TKT-0028-normalize-wiki-link-target-resolution.md) — P2; depends on TKT-0025
- [TKT-0031: Add first-class plans with explicit agency and lifecycle boundaries](done/TKT-0031-first-class-plans.md) — P1; depends on TKT-0029
- [TKT-0029: Establish the referenceable-record foundation, minimal entity kinds, and optional tags](done/TKT-0029-minimal-entity-types-intent-and-tags.md) — P1; depends on TKT-0024 and TKT-0027
- [TKT-0027: Re-extract nested planning sections on parser upgrades](done/TKT-0027-versioned-nested-section-reextraction.md) — P1; depends on TKT-0025
- [TKT-0025: Audit campaign-bible planning coverage](done/TKT-0025-campaign-bible-coverage-audit.md) — P1; depends on TKT-0020 and TKT-0023
- [TKT-0026: Display complete proposal item state before approval](done/TKT-0026-complete-proposal-comparison.md) — P1; depends on TKT-0023
- [TKT-0024: Perform the first scoped live canonical promotion](done/TKT-0024-first-live-canonical-promotion.md) — P1; depends on TKT-0020 and TKT-0023
- [TKT-0023: Build the import review React vertical slice](done/TKT-0023-import-review-react-slice.md) — P1; depends on TKT-0019, TKT-0021, and TKT-0022
- [TKT-0022: Implement candidate proposal and approval workflow](done/TKT-0022-candidate-proposal-workflow.md) — P1; depends on TKT-0015 and TKT-0021
- [TKT-0021: Expose import receipts and review queues](done/TKT-0021-import-review-read-api.md) — P1; depends on TKT-0020
- [TKT-0020: Ingest live Starfall evidence into development](done/TKT-0020-ingest-live-starfall-evidence.md) — P1; depends on TKT-0016, TKT-0018, and TKT-0019
- [TKT-0019: Proxy raw-app campaign reads through Windmill](done/TKT-0019-proxy-raw-app-campaign-reads.md) — P1; depends on TKT-0017 and TKT-0018
- [TKT-0018: Automate the local UI test stack lifecycle](done/TKT-0018-test-stack-lifecycle.md) — P1; depends on TKT-0008 and TKT-0017
- [TKT-0017: Bind CampaignClient browser fetch correctly](done/TKT-0017-bind-browser-fetch.md) — P1; depends on TKT-0008
- [TKT-0008: Prototype full-code React shell](done/TKT-0008-react-shell.md) — P1; depends on TKT-0005 and TKT-0007
- [TKT-0007: Establish Windmill source deployment](done/TKT-0007-windmill-deployment.md) — P1; depends on TKT-0004
- [TKT-0012: Execute grounded retrieval acceptance suite](done/TKT-0012-execute-retrieval-suite.md) — P1; depends on TKT-0005, TKT-0010, and TKT-0011
- [TKT-0016: Implement incremental Markdown importer](done/TKT-0016-implement-markdown-importer.md) — P1; depends on TKT-0005, TKT-0013, and TKT-0015
- [TKT-0015: Implement atomic canonical change-set application](done/TKT-0015-atomic-change-set-application.md) — P1; depends on TKT-0005 and TKT-0010
- [TKT-0013: Build sanitized Markdown importer fixtures](done/TKT-0013-markdown-importer-fixtures.md) — P1; depends on TKT-0005 and TKT-0014
- [TKT-0010: Build executable acceptance fixture harness](done/TKT-0010-acceptance-harness.md) — P1; depends on TKT-0005
- [TKT-0005: Scaffold Campaign Core service](done/TKT-0005-core-service.md) — P1; depends on TKT-0003
- [TKT-0014: Correct live Starfall import scope](done/TKT-0014-correct-live-import-scope.md) — P1; depends on TKT-0006A
- [TKT-0006A: Confirm Markdown importer specification against live Starfall data](done/TKT-0006A-live-starfall-confirmation.md) — P1; depends on TKT-0006
- [TKT-0004: Scaffold private TrueNAS stack](done/TKT-0004-truenas-stack.md) — P1
- [TKT-0009: Reconcile repository metadata after migration](done/TKT-0009-reconcile-migrated-repository.md) — P1
- [TKT-0011: Author grounded retrieval acceptance corpus](done/TKT-0011-grounded-retrieval-suite.md) — P1
- [TKT-0002: Build interaction acceptance fixtures](done/TKT-0002-interaction-fixtures.md) — P0
- [TKT-0001: Specify truth states and authority](done/TKT-0001-truth-state-authority.md) — P0
- [TKT-0003: Define Campaign Core schema](done/TKT-0003-core-schema.md) — P0; depends on TKT-0001 and TKT-0002
- [TKT-0006: Specify incremental Markdown importer](done/TKT-0006-importer-spec.md) — P1; depends on TKT-0001
