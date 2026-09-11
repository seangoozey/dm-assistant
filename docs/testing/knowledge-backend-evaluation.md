# Offline backend result comparison

Preparation for TKT-0096, extending the TKT-0090 benchmark. No Cognee installation,
provider calls, live-data reads, or backend quality results are produced by these tools.

From `campaign-core`, export synthetic discovery inputs:

```powershell
.\.venv\Scripts\python.exe -m tests.support.knowledge_discovery_input
```

Discovery inputs omit expected answers and paths. An isolated backend adapter must
later record results in the following format. Example below is a **fabricated format
example**, not measured output; omitted cases will correctly be counted as failures.

```json
{
  "arm": "llm_discovery",
  "backend_version": "record-the-exact-version",
  "configuration_id": "record-a-versioned-config-or-hash",
  "model": "record-the-actual-model",
  "embedding_model": null,
  "cost_usd": null,
  "outputs": [
    {
      "case_id": "ask-command-destination",
      "evidence_ids": ["command", "island"],
      "mode": "answer",
      "paths": null,
      "latency_ms": null
    }
  ]
}
```

Score a saved result file without contacting its backend:

```powershell
.\.venv\Scripts\python.exe -m tests.support.knowledge_evaluation results.json
```

Arms are `lexical`, `known_links`, and `llm_discovery`. Model identity is mandatory
for the discovery arm; null cost/latency means unknown, not free or instantaneous.
Missing cases or explicit errors count as failures. Duplicate cases/evidence and
unknown case IDs are rejected. Unknown returned evidence IDs and forbidden evidence
are violations, including records outside the top-ten scoring window. Superseded,
excluded and requester-hidden records are forbidden. Known forbidden record IDs
appearing inside paths are also reported.

Each case reports recall@10, precision@10, mode correctness and exact expected-path
recall. Empty precision is undefined, not perfect. Path direction and order matter.
No returned paths means unsupported, not proof of zero bad connections. Exact path
matching and known forbidden-node checks do **not** establish semantic grounding,
full graph authorization or inference fidelity. A separate grounding review and
actual adapter lifecycle tests remain necessary before any adoption decision.

The next integration step is a pinned Cognee/OpenRouter adapter run against these
synthetic inputs under an agreed provider budget. It must preserve provenance IDs
through extraction and retrieval so outputs can be scored without guessing matches.
