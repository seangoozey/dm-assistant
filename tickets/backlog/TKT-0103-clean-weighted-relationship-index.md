---
id: TKT-0103
title: Build clean evidence-linked relationship indexing and aggregation
status: backlog
priority: P0
milestone: shared-campaign-knowledge
depends_on: [TKT-0102]
created: 2026-09-10
updated: 2026-09-28
---


## The decision-track framing (ruling 2026-09-28)

Sean's ruling: **the graph service is foundational to the completion of this project** (see TKT-0094, blocked on the final infrastructure/implementation decision). **Role on the track:** This is the concrete REMAINING BUILD on the decision track: the clean evidence-linked index is the Postgres-native implementation candidate the 0105 decision weighs against native Cognee. This ticket is part of the DECISION TRACK that produces that decision: 0096 (this ticket) + 0103 (build the clean index — the Postgres-native candidate) + 0104 (native-backend comparison) feed 0105 (the call). The 2026-09-14 park stands — "revisit after the DB-completeness front settles" — with a concrete measure now: the DB front is 71/120 qualified with the 186 orphaned claims (TKT-0138) as the remaining mass. When 0138 lands, 0103 → 0105 is the unblock sequence for the foundational service (0094/0095 wait on it).
# TKT-0103: Build clean evidence-linked relationship indexing and aggregation

## Outcome

A reproducible representative Cognee index suitable for relevance evaluation. Delivery slice of TKT-0092 and TKT-0096; not a full-library migration.

## Scope

- Pin installed library/model/prompt/schema/chunker versions and inspect supported extension points before coding; do not patch site-packages as a durable solution.
- Remove instruction boilerplate from indexed source text. Put extraction instructions in prompts and truth/provenance in metadata, preserving exact source spans and offsets.
- Use section-aware token-bounded chunks, preserving neighboring context when needed. Split oversized passages rather than excluding or truncating them; deduplicate overlapping support by original evidence identity.
- Include representative organizational, causal, geographic, planned and incidental relationships, including the previously missing Sorin/Eustice support and Monastery power-release chain. Audit coverage independently of ranking.
- Extract directed relationship descriptions with exact supporting references, modality, negation, attribution and temporal scope. Generated relationships remain derived; optional SPO enrichment is never required of the author.
- If ingestion strength is included, explicitly request and validate it and preserve it through storage/export. Keep it separate from evidence support, support counts and feedback_weight. Trace fields end-to-end; no assumed automatic weight calculation.
- Aggregate compatible relationships across stable identities while retaining individual evidence contributions. Do not merge opposing predicates or contradictory/modally distinct statements merely because endpoints match. Avoid multiplying strength for copied summaries or overlapping chunks; document the chosen aggregation rule rather than blindly summing.
- Audit suspicious boilerplate nodes, unsupported edges and alias collisions. Preserve failures for analysis; source correction invalidates affected derived relationships.

## Acceptance

- [ ] Versioned manifest maps every indexed passage and edge contribution back to original evidence.
- [ ] All representative fixture passages are covered, including oversized input; no instruction-generated campaign nodes.
- [ ] Weight/schema round-trip tests prove requested fields reach storage and retrieval; feedback remains separate.
- [ ] Duplicate-source, conflicting-state, alias and supersession tests pass.
- [ ] Rebuild is isolated and reversible; no canonical mutations or replacement of the active generation without acceptance.

## Validation

Use TKT-0102 corpus; record extraction quality, coverage, failures, tokens and cost. Check the existing authorized key budget before paid work; do not assume its remaining balance. No new service, purchase, or migration is authorized by this planning ticket.

## Preparation findings (2026-09-10, offline; no provider calls)

Verified against the installed package by `deploy/evaluation/verify_extension_points.py` (run with the isolated evaluation venv) plus direct source inspection:

- **Install integrity:** all 2,276 cognee files match the wheel RECORD hashes; the environment is pristine upstream Cognee 1.5.3 with no site-packages patches. The `truth_alignment`/`truth_epoch` fields visible on `Entity`/`DocumentChunk` are upstream, inert metadata slots (excluded from embeddings and identity), not local modifications.
- **Extension points exist:** `cognify(graph_model=..., custom_prompt=...)` are public parameters defaulting to the shared `KnowledgeGraph`; `extract_content_graph(content, response_model, custom_prompt)` is directly importable. A `WeightedKnowledgeGraph` whose edge carries `strength` parses extraction payloads correctly (`strength_requested_parses: true`). The existing `relevance_trial.py` already passes `custom_prompt` but kept the default model, so strength was never requested.
- **Verified drop point:** `_add_extracted_edges` in `modules/graph/utils/expand_with_nodes_and_edges.py` builds each persisted edge from only `relationship_name` + `description`; a custom extracted field does not survive default conversion (`strength_survives_default_conversion: false`; persisted fields are exactly `edge_text`, `relationship_type`). The persisted `Edge` model itself accepts `weight`, `weights: dict[str, float]`, and `properties` — storage can carry weights, conversion just never populates them.
- **Deduplication, not aggregation:** within one extraction batch `_add_extracted_edges` keeps the first edge per `EdgeIdentity`; `attach_new_edges_to_data_points` skips identities already in graph storage. Repeated support across chunks is silently dropped rather than aggregated — the evaluation manifest must do the contribution aggregation (`relationship_projection.py` behavior) itself.
- **Score semantics:** native triplet ranking in `CogneeGraph.score()` is the sum of node/edge embedding distances scaled by `(2 - importance_weight)`; `importance_weight` defaults to 0.5 on chunks/entities. The uniform `feedback_weight=0.5` seen in exports is a fallback default in that scorer, and default `feedback_influence` is 0.0, so it is inert. Neither value is relationship strength.

Implication for implementation: request strength through the public `graph_model`/`custom_prompt` parameters, but do not expect it in Cognee's own edge storage or native scores. Keep a versioned evaluation manifest keyed by edge identity (endpoints + relationship name + chunk/source provenance) that carries strength, evidence, state, and aggregation, and join it to Cognee's returned edges at retrieval time — this also satisfies the manifest acceptance criterion without patching site-packages or fighting the conversion layer.

## First weighted trial (2026-09-10, paid; ledger $0.549520 → $0.567980, 1,455 → 1,621 attempts)

Implemented `deploy/evaluation/weighted_manifest.py` (offline: capture→contribution mapping, aggregation reuse, name-normalizing join, manifest-backed-before-co-occurrence ranking; 9 tests) and `deploy/evaluation/weighted_trial.py` (cognee venv: strength requested via `WeightedKnowledgeGraph` + explicitness-only prompt; extraction payloads captured through the public `calculate_chunk_graphs` hook before conversion drops them; manifest persisted with raw captures for provider-free rebuilds; `--weighted-trial`/`--weighted-search-only` wired into `run_cognee_trial.py`).

Results on the v2 explicit-bridge corpus (arm `cognee-weighted-manifest-join-v1`, Gemini 3.5 Flash Lite, all 17 records extracted, 33 manifest entries, strength range 0.5–1.0, intended state retained on the plan record):

- Fresh index, native top_k=10: development pairwise 3/5, held-out 3/5. Structural/type edges still consume most returned slots — same failure mode as the v1 native diagnostic, not a weighting failure.
- Search-only top_k=100 against the same index (no re-extraction): development pairwise 5/5, held-out 4/5 (80%, exactly at the frozen gate; the miss is organization-paraphrase, where `warden` and `mural` both carry strength-1.0 manifest edges and the first-seen tie-break favors mural — the lexical baseline also fails this case). recall@10 = 1.0 on all ten cases.
- Zero false-bridge claims across all cases including both absent-bridge negatives; path claims arise only from explicit manifest provenance, never co-occurrence.
- precision@10 is 0.10–0.30, below the frozen 0.6 gate: the ranking returns the full expanded pool with no truncation policy. Truncation must be designed against the development split only, then held-out re-run once — not tuned against held-out labels.
- `path_covered` remains false for the two organizational chains by construction: current paths are per-edge provenance sets, so a three-record chain cannot be covered by one edge. Multi-hop coverage requires joining manifest entries into walks through the existing `evidence_paths.discover` harness — next iteration.
- Join robustness: symmetric name normalization (casefold, apostrophe, leading articles) fixed `the Inquisition`/`vale's`-class mismatches, re-keyable offline via `renormalize` without provider calls. Cross-extraction surface variance (`Captain Vale` vs `Captain Vale's Warden patrol` as separate nodes) still falls back to co-occurrence ranking; the durable fix is identity/UUID-based joining using Cognee's own entity-id derivation, not more string rules.

Artifacts: `.local/cognee-evaluation/relevance-v2-manifest.json` (run-1 original preserved alongside), `relevance-v2-captures.json`, `relevance-v2-weighted-report.json`, `relevance-v2-weighted-search-report.json`. Isolated store under `.local/cognee-evaluation/relevance-v2`. No canonical writes, no live deployment, no site-packages changes.

## Traversal and truncation follow-up (2026-09-10, offline; no provider calls)

Added `deploy/evaluation/manifest_traversal.py` (5 tests): manifest endpoints resolve to corpus entity tokens only on a unique whole-word match; ambiguous endpoints exclude their edges rather than merging (the generic extracted `company` endpoint is ambiguous with `Ossler's company`, and resolving it would fabricate the forbidden bridge); negated edges are excluded; resolved edges become suggested-class `Link`s through the existing `evidence_paths.discover` safety harness (depth 3, fanout 12, budget 100, revision-gated); walks are seeded from declared tokens appearing in the question.

`deploy/evaluation/manifest_traversal_report.py` re-ranks the saved paid-run artifacts offline (`relevance-v2-traversal-report.json`): P0 saved (uncapped), P1 backed-only capped at 10, P2 walk-reached records first then P1 remainder capped at 10. All three arms were scored on the same saved run in one pass; P2 is preferred on development-split parity plus the principled ground that seed-anchored walks demote records whose extracted endpoints cannot be anchored to any declared identity — its held-out numbers are therefore reported, not claimed as an untouched final estimate, and the previously inspected held-out labels caveat still stands.

- P2 results: development 5/5, held-out 5/5 pairwise (five-case split; too small for production claims — a fresh final evaluation set remains required), zero false-bridge claims on every arm, recall@10 1.0 throughout.
- The Regent warden chain is covered by a single walk with stepwise evidence (path_covered True); the Sorin organization chain is not, because the extractor's generic `company` endpoint is identity-ambiguous — a correct fail-closed outcome, not missing evidence. Twenty unresolved edges were audited (`unresolved` in the report); the durable fixes are a specificity-demanding extraction prompt and identity/UUID-based joining, not looser string rules.
- organization-paraphrase becomes correct under P2 because the mural record's extracted endpoints (`mural of captain vale`, `window`, `inn corridor`) resolve to no declared identity, so it ranks below walk-anchored records — evidence-based demotion, not a name boost.
- Precision@10 stays 0.10–0.30 under every arm: with only `required` labeled relevant, the frozen 0.6 gate is structurally unreachable for single-gold cases (maximum 1/10). This is a corpus-labeling gap, not a ranking defect; per-case judged relevance pools (several relevant records per question) are needed before the precision gate measures anything meaningful. No truncation was tuned to squeeze the number.

## Live-slice trial (2026-09-11, paid; ledger $0.567980 → $1.055899, of which $0.40 is conservative reservation and $0.155891 provider-reported for the new calls)

`export_slice_v3.py` exported 40 real canonical DM-only claims read-only (Romulus-neighborhood SQL filter, BEGIN READ ONLY, no writes). `assemble_v3_corpus.py` built `.local/cognee-evaluation/relevance-v3-live-corpus.json`: entity associations are derived whole-word mentions of the 53 canonical entity names; six DRAFT judgment cases pending Sean's confirmation (no held-out split, no absent-bridge negatives declared). `weighted_trial.py --live-slice` indexed raw assertion text only (no instruction preamble, unlike the earlier live-pilot v3 index text), extracted strength through the capture hook (170 manifest entries, all 40 records), and ran GRAPH_COMPLETION searches at top_k 10 and 100.

Measured results on the real slice (draft judgments; arm `cognee-weighted-manifest-join-live-v1`, then offline P2 traversal re-ranking via `manifest_traversal_report.py --slice live`):

- Manifest-join ranking: 4/6 draft pairwise (causality, plans, layout counterexample, monastery pass; both organizational cases fail — `grand-inquisitor` first matches at native position 69).
- Traversal-first re-ranking: 2/6 — worse, not better, on live data.
- Zero false-bridge claims (no negatives declared yet; nothing bridged through unresolved endpoints).

Three transfer failures from the synthetic corpus, all root-caused:

1. **Explicitness strength saturates on canonical claims.** Nearly every extracted edge scored 1.0 — canonical claims are direct statements, so "how explicitly is this stated" does not discriminate between them. Ranking degenerated to first-seen tie-breaks decided by native (embedding-distance) order. Ingestion strength as currently defined is not the useful signal for ranking well-formed claims.
2. **Canonical identity coverage is the bottleneck.** Only 46 of 170 extracted edges anchor to canonical entities (27%): the registry has 53 entities and zero aliases. The Inquisition — Romulus's own organization — is not a canonical entity; Grand Inquisitor is a role with no identity; King Peter, Myrin, and the leylines are unregistered; `castle fleurite` is ambiguous between the `Fleurite` and `Fleurite Castle` tokens. Identity-anchored traversal therefore cannot carry organizational structure it was designed around.
3. **Structural junk persists in native returns** (self-loop edges, ~40% empty-name edges), consuming candidate slots exactly as in the synthetic diagnostics.

The synthetic v2 results (90% pairwise) demonstrably do not transfer to real data. The measured path forward is canonical, not algorithmic: enrich the entity registry and aliases for organizations, roles, and recurring concepts through the normal reviewed workflow; make resolution alias-aware; and decide whether role/concept endpoints (Grand Inquisitor, leylines) should be canonical worldbuilding entities or edge properties. None of that is auto-injected here. A separate decision (Sean's): the Eustice/Outriders→Sorin organizational chain is not among promoted claims; including it requires normal reviewed promotion.

## Identity coverage closed; product-path re-check (2026-09-13)

Sean completed the entire identity review (see TKT-0106): 118 identities, 67 aliases, 819 derived claim links, 91% of current claims touching an identity — the measured bottleneck from the live-slice trial (27% anchoring) is closed at the data level. Myrin and the 29 migration-era subject-linked entities were backfilled via the audited `reconcile_links` decision (migration 0053; 428 additional links, receipts recorded; live total 1,247 derived links). A canonical pilot bundle (`live-pilot-v4`, built by `deploy/evaluation/build_canonical_bundle.py` — records through the same adapter transform as Core, graph = entities + contains + co_mention edges, no Cognee, no provider) is deployed and serving Brainstorm graph traces through the live Core: the original complaint queries now return 254+ graph-traced records each ("Romulus's organization" surfaces Dariferra/leyline connections, "Return to the Monastery" the monastery chain, "Who is Corefera" resolves through the misspelling alias). Honest notes: the pilot currently adds every reachable record as context (UI ranking filters); singular/role-marked surfaces ("an Inquisitor") correctly do not seed; the native Cognee weighted-retrieval re-evaluation (the frozen v2 gates) remains open pending a fresh paid re-index of the now-covered corpus.

## Absorbed scope (2026-09-14 ticket audit)

TKT-0092's remainder now lives here: the durable in-database relationship projection with refresh semantics (rebuild equivalence, refresh after correction/merge/alias/visibility changes, fallback during outage). Parked with the graph ruling until the DB-completeness front settles.
