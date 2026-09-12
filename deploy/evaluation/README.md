# Isolated Cognee trial

`--live-generation live-pilot-v3` selects a separate expanded snapshot/store. Its
50-claim generation is now validated and active (375 nodes, 1,069 edges). Original
assertions are wrapped with recorded state/authority and modality
instructions. `audit_pilot_bundle.py --generation live-pilot-v3` must pass before
activation. Gateway limits concurrent upstream requests to two and waits for active
calls to settle during temporary reservation shortages. Closed-run user-confirmed
billing bounds are recorded without deleting history. Final cumulative upper bound
is $0.536196, including $0.036196 after the user's <=$0.50 checkpoint. V2 remains
available for rollback. The native viewer is served at http://127.0.0.1:8767/graph.html.
`--live-search-only` verifies the stored generation without re-extracting it.

Development-only app pilot: `build_pilot_bundle.py --generation live-pilot-v3` binds the graph to
current Core fingerprints after checking original assertion/provenance equality.
Testing Compose mounts that bundle read-only and configures the pilot adapter.
In Brainstorm, search `Ishi'go'dan`. Related discoveries are separate from direct
matches and include compact suggested connection paths, not internal IDs. The pilot
traverses up to two semantic edges in either direction, bounded to 40 nodes and
skipping broad intermediate hubs. The Mythis Regions result does not name the seed:
it is a live example of nonlexical retrieval. Generated edge labels can misrepresent
planning as action, so cards now show neutral associated names and expandable
unchanged connection sources. Traversal requires shared source context, which is
not proof that a generated relation is true. This is still only a
50-record pilot, not a full-campaign or verified semantic reasoning service. Four
oversized relevant claims remain excluded rather than truncated.
One changed/missing/hidden pilot record disables the entire generation; automatic
refresh is not yet implemented. Disable by clearing CAMPAIGN_GRAPH_PILOT_BUNDLE in
the testing override. Production Compose does not enable this feature.

Full synthetic corpus evidence-only runs now exist. `--corpus-scope dm`, `party`,
and `conflict` each use a separate store and pre-index scope filtering. Use
Campaign Core's Python to run `deploy/evaluation/score_corpus_trial.py` offline.
See `corpus-findings.md` for metrics and limitations. The full *retrieval corpus*
was queried; the full adoption/answer-safety acceptance criteria are not complete.

`--evidence-expansion` queries the existing corrected cross-document graph and returns
exact source excerpts separately from raw generated context. It uses typed returned
endpoint IDs and a bounded incoming-chunk association expansion. Source IDs must be
in the explicit synthetic current-source manifest and text must match exactly. It
does not re-extract or modify the graph. Output: `evidence-expansion-report.json`.
This is an evaluator, not the production authorization or entailment boundary.

Current accounting: the first 27 calls are bounded by the user's corrected **under
$0.06** report, not an exact six-cent charge. `billing_bounds` preserves that update
alongside earlier historical settlements. New completed calls use OpenRouter's
`usage.cost`, rounded up to microdollars; invalid/missing values and uncertain calls
retain reservations. This follows [OpenRouter usage accounting](https://openrouter.ai/docs/cookbook/administration/usage-accounting).

User authorization updated 2026-09-07: the key has an approximately $3 limit, and
the user explicitly authorized a small real-campaign subset for the end-to-end pilot.
The gateway still enforces its stricter $2 cumulative local guard; the ledger is
not reset. Report either key exhaustion or local guard exhaustion distinctly.
This remains an experimental environment, not the application stack.

`export_live_pilot.py` reads at most 12 relevant current claims with provenance from
PostgreSQL, without mutations, into ignored private runtime storage. The v2 selection
prioritizes Tsunadis and Ragga'na'ken mentions, then fills the Ishi'go'dan context.
`run_cognee_trial.py --live-pilot` uses a separate `live-pilot-v2` store. v1 is retained
as a failed batching experiment. The v2 adapter splits embedding batches into at most
32 inputs, preserving the gateway limits. No live source text belongs in tracked files.

`inspect_cognee_graph.py --scope dm` independently reads the existing synthetic
store and creates Cognee's native viewer and a graph JSON snapshot with a checksum.
It blocks Python networking and makes no provider calls. Outputs are private under
`.local/cognee-evaluation/inspector-dm/`; this is real stored graph data, not a mockup.

Pinned package: `cognee==1.5.3`.
Downloaded wheel SHA256:
`575c2791a911edecfa70321c81e984a7ebbc16746f41562361f43636be76308f`.

Runtime files and the separate virtual environment live under ignored
`.local/cognee-evaluation/`. Do not install these dependencies in Campaign Core.
Resolve and capture the complete dependency set after installation before any paid run.

Installation completed; `pip check` passed. Resolved Windows/Python 3.12 dependencies
are captured in `requirements-windows.lock`. Offline import/signature preflight passed
with zero network attempts and zero provider calls. LiteLLM requires an explicit
`CUSTOM_TIKTOKEN_CACHE_DIR`; the preflight uses the trial's `tokenizers` directory.
Populate `cl100k_base` there using tiktoken before the network-blocked check.
The first failed import created a diagnostic log in the user's default `.cognee/logs`
directory; file logging is now disabled for subsequent preflights.

Offline import check, from `.local/cognee-evaluation`:

```powershell
.\.venv\Scripts\python.exe ..\..\deploy\evaluation\cognee_preflight.py
```

The script removes inherited API-key/token/database-URL variables, uses a dummy
endpoint, disables telemetry and blocks Python socket connections and DNS resolution.
It performs an import/signature check, not ingestion or extraction. This is a smoke
test guard, not a general OS network sandbox for arbitrary native code.

`run_cognee_trial.py` now runs one synthetic smoke passage through `budget_gateway.py`.
Only the gateway receives the existing provider key; Cognee receives a random local
token. Each upstream attempt reserves $0.10 before forwarding, within a shared $2
ledger. Do not delete/reset `trial-budget.sqlite` between runs. Externally confirmed
cumulative billing can replace reservations for a completed contiguous prefix via
`Ledger.settle`; the immutable checkpoint retains every attempt and its outcome.
Unconfirmed attempts remain reserved, including failures and timeouts. The user
confirmed $0.06 total for attempts 1–8; this is recorded without resetting history.
The text-only 32 KiB requests and 8192 output-token cap use provider price ceilings
of $0.30/M prompt, $2.50/M completion and no per-request charge. No tools, plugins,
multimedia, client routing or model overrides are forwarded. Reservation is deliberately
larger than these bounded requests, including framing allowance. Unknown or failed
requests never refund a reservation. This is conservative spend bounding, not billing
measurement. See `first-trial-findings.md` for results and remaining limitations.

To query the existing synthetic graph without repeating extraction, from the runtime
directory:

```powershell
.\.venv\Scripts\python.exe ..\..\deploy\evaluation\run_cognee_trial.py --search-only
```

This pins `GRAPH_COMPLETION` with `only_context=True`; the three fixed questions
retrieve context without generating answers. Results go to `retrieval-report.json`,
preserving the ingestion report. Queries still use paid embeddings under the guard.

`--cross-document` is a separate two-DataItem extraction/query probe using isolated
`cross-document/system` and `cross-document/data`, but the same budget ledger.
`--retire-cross-source` removes only its verified geography/r1 derivative with all
provider calls disabled. The target's original text and before/after exports remain
in reports. This is a one-shot destructive lifecycle test of synthetic derivatives,
not a campaign deletion tool. Do not rerun ingestion to undo retirement silently.
See `cross-document-findings.md`: extraction and retirement verified; query blocked
by the remaining reservation budget. Full replacement testing remains outstanding.

Follow-up `--replace-cross-source` has now tested search after retirement, added a
new geography/r2, and queried again. It requires geography to be absent and refuses
to overwrite an existing geography revision. The report is separate from previous
runs. Correction propagation worked, but top_k=5 omitted the supporting geography
chunk while including its generated description; grounding remains a known gap.

Official provider guidance: https://docs.cognee.ai/setup-configuration/llm-providers
supports the custom provider with OpenRouter model routing. Embeddings are configured
separately. The pinned wheel uses `litellm_native` as the default structured-output
framework; do not blindly copy older documentation's Instructor defaults.

`verify_extension_points.py` is an offline (no network, no LLM, no index writes)
check of the installed Cognee's weighted-edge extension points for TKT-0103.
Run it with the evaluation venv. It confirms `cognify(graph_model=...,
custom_prompt=...)` are public parameters, a strength-bearing graph model parses,
the default conversion in `_add_extracted_edges` drops custom fields (persisted
edges carry only `relationship_type`/`edge_text`), and the persisted `Edge`
model does accept `weight`/`weights`/`properties`. Full findings and the
resulting manifest-join design are recorded in the TKT-0103 ticket.

`weighted_trial.py` (via `run_cognee_trial.py --weighted-trial [--weighted-search-only]`)
is the TKT-0103 weighted-edge trial on the v2 explicit-bridge corpus: strength is
requested through public `graph_model`/`custom_prompt` parameters, captured by the
`calculate_chunk_graphs` hook before conversion drops it, aggregated into the
versioned manifest (`relevance-v2-manifest.json`, raw captures alongside), and
joined at retrieval time. The search-only variant reuses the index with a
top_k=100 candidate pool. `weighted_manifest.py` and its tests are offline and
run under the main development venv. See the TKT-0103 ticket for measured
results and open gaps (precision truncation, multi-hop path coverage,
identity-based joining).

`manifest_traversal.py` resolves manifest endpoints to corpus entity identities
(unique whole-word match only; ambiguous endpoints exclude their edges) and runs
seeded multi-hop walks through the `evidence_paths` safety harness.
`manifest_traversal_report.py` re-ranks the saved paid-run artifacts offline
(P0/P1/P2 policies) into `relevance-v2-traversal-report.json`; both run under the
main development venv with no provider calls. Measured outcomes live in the
TKT-0103 ticket notes.

`export_slice_v3.py` (read-only SQL, Romulus-neighborhood canonical claims) and
`assemble_v3_corpus.py` (canonical-mention entity associations, DRAFT judgments)
build the v3 live corpus in ignored local storage; `--live-slice` runs the
weighted trial against it, and `manifest_traversal_report.py --slice live`
re-ranks offline. The live corpus is never committed. Findings and open
canonical gaps are in the TKT-0103 ticket.

`identity_gap_candidates.py` is the TKT-0106 Phase-1 detector proof: mines
current canonical claims read-only for recurring proper-noun phrases matching
no canonical identity, ranked by retrieval demand from the live-slice
unresolved-endpoint audit. Output is derived review material only; nothing is
created or written.
