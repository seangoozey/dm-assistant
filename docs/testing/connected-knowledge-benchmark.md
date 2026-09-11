# Connected knowledge benchmark

TKT-0090 adds 24 synthetic cases: four each for Ask, encounters, Lore and
Brainstorm, plus eight boundary cases. The original 38-case YAML corpus is unchanged.
The corpus and captured baseline live in `tests/fixtures/connected_knowledge_*.json`.

TKT-0091 privacy update: the captured JSON remains historical. Only the two security
cases may differ from that snapshot at this stage. Their desired mode is now
`insufficient_evidence`, not a `restricted` signal announcing private knowledge.
Hidden-present and hidden-absent runs must match. The original 38-case corpus also
retains every case/assertion, with two visibility-mode expectations corrected.

## Run

From `campaign-core`:

```powershell
.\.venv\Scripts\python.exe -m tests.support.connected_knowledge_harness
.\.venv\Scripts\python.exe -m pytest tests/test_connected_knowledge.py tests/test_retrieval_acceptance.py
```

The runner prints machine-readable JSON. It never connects to campaign storage,
providers or Windmill. Tests compare evidence, modes and metrics with the captured
baseline, excluding timings, and repeat with reversed record input order.

## Scope and limitations

This is an **offline lexical-selection simulation followed by the actual production
RetrievalPolicy**, not an end-to-end measurement. It reuses PostgreSQL's query
tokenizer, simulates its lexical intersection, citation ordering, 100-record cap and
supersession exclusion. It does not exercise SQL joins, entity alias search fields,
database/network latency, UI consumers or model answers. Workflow labels describe
intended use cases; they do not claim those four UI paths were exercised.

The contradictory Vale assertion is excluded by default and enabled only in the
conflict scenario. The PC's declared intention is an observed statement, not an NPC
intention or a prediction. Synthetic names stand in for the reported command-site
versus summoning-site distinction; these are not assertions about live Starfall canon.

Required paths are retrieval associations, not semantic facts. For example, a
command and ritual connected through Eastwatch must not imply that their destinations
are identical. Paths specify relevant claim/entity nodes. Today's API returns no
paths: required path recall is zero, while unsupported-connection counts and path
safety are **unmeasurable**, not zero violations. Hidden evidence is separately tested.

## Baseline and targets

Captured baseline: recall@10 **0.881**, precision@10 **0.463**, answer-mode accuracy
**0.333**. Reversed-input ordering matches. No forbidden evidence or forbidden
support was returned in this corpus. These narrow checks do not prove general safety.
Multiple compatible facts are incorrectly classified as conflicts or possible retcons;
intended behavior and question sufficiency also need work in TKT-0091.

Recall is required IDs retrieved / required IDs, excluding cases without required
evidence. Precision is relevant IDs / actual returned IDs up to ten, excluding empty
results. Each case is weighted equally. Required IDs define relevance for scoring;
other returned facts may be true but unhelpful. Latency is one local policy-only run,
recorded in the baseline JSON; it is not a service performance target.

Proposed frozen gates for backend comparison: recall@10 >= 0.90, precision@10 >= 0.75,
mode accuracy >= 0.90, required-path recall >= 0.90, zero forbidden evidence/support
and zero unsupported reported connections, with deterministic ordering. These are
engineering proposals pending agreement, not measured achievements. End-to-end
latency needs a representative database baseline before setting a credible budget.

Do not loosen gold cases to make a backend pass. When intentional policy changes
alter the baseline, inspect per-case differences and record why. Before TKT-0096,
add an actual database/shared-retrieval runner and measured path validation; this
offline baseline alone cannot justify selecting Cognee or another graph backend.
