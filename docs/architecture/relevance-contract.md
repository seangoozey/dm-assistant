# Experimental relevance contract v1

This is a testable candidate contract for TKT-0102, not live ranking or a new truth policy.

Core eligibility precedes scoring: every path element must be visible, current, time-eligible and unambiguously resolved. Missing checks fail closed. Historical support needs an explicit future policy extension; this version excludes superseded/rejected evidence. No hidden-path score or explanation is returned.

Score components are normalized to [0,1]: semantic relevance (50%), path strength (15%), evidence support (20%), distinct original-source support (5%, capped at three), purpose-dependent truth suitability (8%), feedback (2%). These coefficients are frozen starting values, not measured optimal values. Missing path strength and feedback are neutral .5 and explicitly identified. Semantic and evidence support are required; provider adapters must document calibration and invert distances appropriately. NaN and out-of-range values fail validation.

Factual queries favor observed/established evidence; Brainstorm treats observed, established, intended, prepared and possible as equally suitable context; encounters favor observed/established/intended/prepared. Comparison accepts all otherwise eligible states for review, never as proof of contradiction. Nonpreferred states remain lower-ranked labeled context. Factual support still requires the existing authority/content checks; even an established passage may contain an embedded plan. Mixed paths retain all original states and use minimum suitability, never a promoted aggregate state.

Source independence refers to original evidence, not documents, generated summaries or overlapping chunks. Extraction strength is not confidence or authority. Model suggestions never verify a relationship merely by scoring highly.

## Frozen evaluation gates before tuning

- Zero visibility, stale-path or planning-as-occurrence violations.
- At least 80% of held-out pairwise comparisons correct; ties count as failures.
- Passage recall@10 at least .8 and precision@10 at least .6 on the declared judged candidate pool; report missing corpus coverage separately, not as successful ranking.
- Report exact sample sizes, coverage, latency, cost and uncertainty; synthetic scoring-unit tests do not establish end-to-end relevance.
- Pairwise judgments must include organizational/causal versus incidental associations, paraphrases, hub entities and counterexamples. Named campaign examples are acceptance judgments, never provider input or named score boosts.

The existing exported-graph walker remains the baseline. The interrupted `graph_relevance` heuristic (pilot target scoring, `RetrievedEvidence.graph_relevance`, and its client ranking term) was inspected against this contract and removed on 2026-09-10; trace selection is deterministic first-match, and the tested graph pilot traversal, traces, and shared-source context are retained. No grouping during ranking evaluation.

## Explicit-bridge corpus v2

`tests/fixtures/relationship_relevance_cases_v2.json` extends the v1 diagnostic corpus after the v1 limitation was documented: record coverage is not path coverage. Every declared required path bridges through an explicit bridge record (`company-bridge`, `warden-bridge`), and absent-bridge cases (`silver-helms`/`ossler-company`, `ossler-company`/`company`, `ossler-company`/`command`) must never be connected. Records carry explicit entity tokens so bridge coverage is checkable offline; fixture-invariant tests prove declared chains bridge and forbidden pairs sit in different components of the explicit-bridge graph. Ten cases, five held out. The frozen lexical baseline is `tests/fixtures/relationship_relevance_baseline_v2.json`; the lexical arm still fails both organizational pairwise cases and returns no paths, an honest diagnostic of why ranked/traversal arms are needed. `evaluate_v2` reports record coverage, bridge coverage, returned-path coverage, and false-bridge claims as separate signals; a recall hit never implies a supported path, and a returned path is a retrieval explanation, never a proven transitive fact.

## Isolated path safety harness

`deploy/evaluation/evidence_paths.py` accepts query-ranked links, requires current evidence revisions and explicit eligibility metadata, excludes structural links, and bounds depth (default two), fanout and total steps. Inverse navigation preserves the recorded direction. Every returned step retains its individual evidence and dimensions; there is no composed predicate or promoted path truth state. Alternate paths remain distinct. Truncation refers only to eligible paths, never hidden edges.

This harness assumes upstream identity and evidence validation; it does not prove that an extracted relation is entailed by its citation. Its synthetic known-link tests prove safety behavior, not retrieval quality. Integration with real extracted contributions and comparative evaluation remain pending.
