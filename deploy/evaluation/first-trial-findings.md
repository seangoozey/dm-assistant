# First synthetic Cognee trial

Cognee 1.5.3, Gemini 3.5 Flash Lite via OpenRouter; Gemini embedding-001 for vectors.
Input was one synthetic passage, not live campaign content. This is a compatibility
and extraction smoke test, **not** the 24-case comparative evaluation.

## Execution

Cognee add/cognify completed. Graph export contained 12 nodes and 18 edges, including
document/summary/type infrastructure; those totals are not 18 discovered facts.
The gateway ledger recorded two completed chat calls and six completed embedding
calls. These initially reserved $0.80 of the authorized $2 safety allowance. The user
subsequently confirmed **$0.06 actual total** for those eight calls. An immutable
billing checkpoint records that confirmation; all attempt records remain intact.
Do not reset the ledger for subsequent attempts.

## Inspected content

Four extracted domain edges:

- Regent `commanded` Sky Titan, with the complete command in edge text.
- Sky Titan `target` Eastwatch, with the intended destruction described in edge text.
- Eastwatch `located_on` Minor Isle.
- Fire Titan `summoned_on` Ember Island, with the source's summoning-location wording.

The two islands stayed separate. Command versus summoning location survived this
example. However, there are material weaknesses:

- The source says "the castle at Eastwatch"; the derived description calls Eastwatch
  itself a castle. This is unsupported identity conflation.
- "Eastwatch opposes the cultists" survives in the summary but the exported domain
  edges omit that opposition and the cultist entity.
- `summoned_on` can read as a completed event; the edge text alone does not establish
  whether summoning happened. Downstream code must preserve source modality instead
  of treating the short edge label as canonical truth.

## Existing-graph retrieval follow-up

Ran three questions using explicit `GRAPH_COMPLETION`, `only_context=True`, top_k=5,
against the existing synthetic dataset. No add/cognify rerun or answer generation.

| Question | Inspected returned context |
| --- | --- |
| Where was the Sky Titan commanded to attack? | Original command passage, command and target edges; Minor Isle remains in source text. |
| Where is the Fire Titan summoning? | Original passage and Fire Titan–Ember Island edge. |
| Who opposes the cultists? | Original passage and summary retain Eastwatch's opposition despite the missing domain edge. |

All three returned the complete original passage. This is evidence availability in
a one-chunk corpus, not proof of ranking quality or multi-hop discovery. Generated
descriptions are interleaved with original evidence; the incorrect Eastwatch/castle
description remains visible. The text context uses display names and inline synthetic
source markers, not the stable claim/revision binding required by our shared contract.
An adapter must resolve source records and check their current scope before using
this context for canonical answers.

Three additional embedding calls completed, no chat calls. Ledger now has 11
attempts: $0.06 confirmed plus $0.30 conservatively reserved for unconfirmed query
billing, leaving $1.64 unreserved under the $2 cap. $0.36 is **not** actual billed cost.

Validation: five budget tests pass, including checkpoint immutability, retention,
restart, concurrent reservations and exhaustion; evaluation scripts pass Ruff.

Cross-document expansion, correction lifecycle, visibility and the full comparison
remain untested. Next: separate-source benchmark inputs and stable evidence binding,
then assess discovery recall and correction invalidation. Do not adopt on this smoke test.
