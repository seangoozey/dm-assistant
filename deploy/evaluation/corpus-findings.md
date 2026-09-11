# First full synthetic corpus retrieval run

2026-09-07. Cognee 1.5.3, Gemini 3.5 Flash Lite, Gemini embedding-001.
Three isolated graph/vector/relational stores: normal DM, party-visible, and the
contradictory-source scenario. 24 cases queried; no live campaign data transferred.
Gold required/forbidden evidence and expected paths/modes never enter discovery input.
Superseded, requester-hidden and scenario-excluded records are removed before indexing.

## Evidence retrieval results

All queries completed. On the 21 cases with nonempty required evidence sets:

| Metric (mean per case) | Lexical simulation + current policy | Cognee + bounded source expansion |
| --- | --- | --- |
| Recall@10 | 88.10% | 100% |
| Precision@10 against required IDs | 50.66% | 59.91% |

All required evidence appeared in those 21 cases. Three cases have no required
evidence and are excluded from these means, not counted as perfect retrieval.
No exposed forbidden/superseded/unknown evidence IDs were reported by the scorer.
The contradiction case returned both the captain claim and its contradictory claim.
That is availability of comparison evidence, **not** an evaluated conflict decision.

The no-answer case returned the unrelated ritual record. Party queries also returned
loosely related visible records. Retrieval must not itself authorize an answer.
Plans, observations, biographies and possibilities remain mixed as retrieval context;
this adapter deliberately does not assign support roles or decide answer modes.

## What this does not prove

- This is one run over 24 short synthetic records, not realistic campaign-scale recall.
- The comparison is evidence-only. The lexical arm includes existing policy; Cognee
  currently returns context without that policy, so these are not equivalent full
  answer systems. Mode/path fields are null, not successful answers or verified paths.
- No known-link-only comparison arm was run; gains cannot yet be attributed solely
  to LLM discovery rather than vector ranking or expansion.
- Graph edges/descriptions were not comprehensively audited for semantic grounding.
- Physically separated visibility scopes test pre-index exclusion, not dynamic
  permissions or hidden-path safety within a shared production index.
- Projection/outbox freshness, concurrent corrections, alias ambiguity decisions and
  the actual Campaign Core integration remain unimplemented in this evaluator.

Decision: retain Cognee as a promising derived retriever; **defer production adoption**.
Next work is the Core-backed eligibility/projection adapter and comparison policy,
then known-link comparison, larger distractor sets and repeated runs. Do not use
generated descriptions as canonical answers or bring this whole-graph toy adapter
directly into the app.

## Artifacts and budget

Ignored runtime reports: `corpus-dm-report.json`, `corpus-party-report.json`,
`corpus-conflict-report.json`, and `corpus-scored.json` under `.local/cognee-evaluation`.
Reports preserve graphs, per-case returned IDs, expanded passages and errors.
Run `score_corpus_trial.py` with Campaign Core's Python to recompute scores offline.

594 total gateway attempts including earlier probes. First 27 are bounded by the
user's corrected under-$0.06 report; later recorded costs sum to $0.067012 rounded
upward. Four attempts without usable billing retain $0.40 of reservations. Total
conservative accounting is $0.527012, not an exact bill; the authorized cap remains $2.
18 offline evaluator tests and Ruff passed. No application redeploy or canon mutation.
