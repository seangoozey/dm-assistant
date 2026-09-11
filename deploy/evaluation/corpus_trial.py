"""Synthetic evidence-retrieval benchmark, separated by requester/scenario scope."""

import asyncio
import json
import time
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from evidence_expansion import Source, expand


def scope_for(case):
    if case["requester_visibility"]["role"] != "dm":
        return "party"
    return "conflict" if "contradiction" not in case.get("excluded_ids", ["contradiction"]) else "dm"


def inputs(corpus, scope):
    cases = [c for c in corpus["cases"] if scope_for(c) == scope]
    if not cases:
        raise ValueError("unknown scope")
    # Scope before indexing; expected answers, paths and forbidden IDs never select input.
    excluded = set(cases[0].get("excluded_ids", ["contradiction"]))
    for case in cases:
        if set(case.get("excluded_ids", ["contradiction"])) != excluded:
            raise ValueError("scope mixes scenario exclusions")
    records = [r for r in corpus["records"] if r["record_id"] not in excluded
               and r["state"] != "superseded"
               and (scope != "party" or r["visibility"] == "party")]
    return records, [{"id": c["id"], "question": c["question"]} for c in cases]


async def run(cognee, report, ledger, scope):
    from cognee.infrastructure.databases.graph import get_graph_engine
    from cognee.modules.search.types import SearchType
    from cognee.tasks.ingestion.data_item import DataItem

    root = Path(__file__).resolve().parents[2]
    corpus = json.loads((root / "tests/fixtures/connected_knowledge_cases.json").read_text())
    records, cases = inputs(corpus, scope)
    dataset = f"synthetic-corpus-{scope}-v1"
    manifest = {}
    items = []
    for record in records:
        identity = uuid5(NAMESPACE_URL, f"dm-assistant/corpus/{scope}/{record['record_id']}/r1")
        manifest[str(identity)] = Source(record["record_id"], "r1", record["assertion"])
        items.append(DataItem(data=record["assertion"], data_id=identity,
                              external_metadata={"record_id": record["record_id"], "revision": "r1"}))
    report["indexed_record_ids"] = [r["record_id"] for r in records]
    print(f"Indexing {len(records)} synthetic records for {scope}", flush=True)
    await asyncio.wait_for(cognee.add(items, dataset_name=dataset), timeout=120)
    await asyncio.wait_for(cognee.cognify(datasets=[dataset], chunks_per_batch=4), timeout=300)
    graph = await (await get_graph_engine()).get_graph_data()
    report["graph"] = graph
    report["evaluation"] = {
        "arm": "llm_discovery", "backend_version": "cognee-1.5.3",
        "configuration_id": "scoped-corpus-v1-top5-incoming-chunks10",
        "model": "google/gemini-3.5-flash-lite", "embedding_model": "google/gemini-embedding-001",
        "cost_usd": None, "outputs": [],
    }
    report["expanded_results"] = {}
    for case in cases:
        output = {"case_id": case["id"], "evidence_ids": [], "mode": None, "paths": None}
        report["evaluation"]["outputs"].append(output)
        if not ledger.can_reserve():
            output["error"] = "budget_exhausted"
            continue
        started = time.monotonic()
        print(f"Query {case['id']}", flush=True)
        try:
            result = await asyncio.wait_for(cognee.search(
                query_text=case["question"], query_type=SearchType.GRAPH_COMPLETION,
                datasets=[dataset], only_context=True, verbose=True, top_k=5), timeout=90)
            seeds = list(dict.fromkeys(str(n.id) for part in result for edge in part["objects_result"]
                                       for n in (edge.node1, edge.node2)))
            expanded = expand(graph, seeds, manifest)
            report["expanded_results"][case["id"]] = expanded
            output["evidence_ids"] = list(dict.fromkeys(p["source_id"] for p in expanded["passages"]))
        except Exception as error:  # noqa: BLE001 - local evaluation records bounded errors
            output["error"] = type(error).__name__
        output["latency_ms"] = (time.monotonic() - started) * 1000
    report["success"] = not any(o.get("error") for o in report["evaluation"]["outputs"])
