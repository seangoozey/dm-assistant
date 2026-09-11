"""Small synthetic cross-document probe; no expected edges supplied to Cognee."""

import asyncio
import time
from uuid import NAMESPACE_URL, uuid5

DATASET = "synthetic-cross-document-v1"
SOURCES = {
    "dispatch": "The Regent sent envoy Mara to Frostgate to negotiate a ceasefire.",
    "geography": "Frostgate is a port on Northreach Island.",
}
QUESTION = "Which island was envoy Mara sent to?"


async def expanded_query(cognee, report):
    from cognee.infrastructure.databases.graph import get_graph_engine
    from cognee.modules.search.types import SearchType
    from evidence_expansion import Source, expand

    result = await asyncio.wait_for(cognee.search(
        query_text=QUESTION, query_type=SearchType.GRAPH_COMPLETION,
        datasets=[DATASET], only_context=True, verbose=True, top_k=5), timeout=90)
    seeds = list(dict.fromkeys(str(node.id) for part in result
                              for edge in part["objects_result"] for node in (edge.node1, edge.node2)))
    # Explicit synthetic current-source snapshot, outside provider input.
    manifest = {
        str(uuid5(NAMESPACE_URL, "dm-assistant-eval/dispatch/r1")): Source("dispatch", "r1", SOURCES["dispatch"]),
        str(uuid5(NAMESPACE_URL, "dm-assistant-eval/geography/r2")): Source("geography", "r2", "Frostgate is a port on Southreach Island."),
    }
    graph = await (await get_graph_engine()).get_graph_data()
    report["raw_context"] = [part["context_result"] for part in result]
    report["seeds"] = seeds
    report["expanded"] = expand(graph, seeds, manifest)
    report["success"] = True


async def replace_geography(cognee, report):
    from cognee.infrastructure.databases.graph import get_graph_engine
    from cognee.modules.search.types import SearchType
    from cognee.tasks.ingestion.data_item import DataItem

    dataset = next(d for d in await cognee.datasets.list_datasets() if d.name == DATASET)
    rows = await cognee.datasets.list_data(dataset.id)
    if any(d.external_metadata.get("source_id") == "geography" for d in rows):
        raise ValueError("expected retired geography before replacement")
    report["queries"] = []
    for stage in ("retired", "replaced"):
        if stage == "replaced":
            text = "Frostgate is a port on Southreach Island."
            await cognee.add(DataItem(data=text, label="geography",
                                     external_metadata={"source_id": "geography", "revision": "r2"},
                                     data_id=uuid5(NAMESPACE_URL, "dm-assistant-eval/geography/r2")),
                             dataset_name=DATASET)
            await asyncio.wait_for(cognee.cognify(datasets=[DATASET], chunks_per_batch=2), timeout=180)
        result = await asyncio.wait_for(cognee.search(
            query_text=QUESTION, query_type=SearchType.GRAPH_COMPLETION,
            datasets=[DATASET], only_context=True, top_k=5), timeout=90)
        report["queries"].append({"stage": stage, "question": QUESTION, "context": result})
    report["graph"] = await (await get_graph_engine()).get_graph_data()
    report["success"] = True


async def run(cognee, report, ledger):
    from cognee.infrastructure.databases.graph import get_graph_engine
    from cognee.modules.search.types import SearchType
    from cognee.tasks.ingestion.data_item import DataItem

    report["sources"] = SOURCES
    items = [DataItem(data=text, label=source,
                      external_metadata={"source_id": source, "revision": "r1"},
                      data_id=uuid5(NAMESPACE_URL, f"dm-assistant-eval/{source}/r1"))
             for source, text in SOURCES.items()]
    print("Adding two separate synthetic documents", flush=True)
    await cognee.add(items, dataset_name=DATASET)
    print("Extracting cross-document graph", flush=True)
    started = time.monotonic()
    result = await asyncio.wait_for(
        cognee.cognify(datasets=[DATASET], chunks_per_batch=2), timeout=180)
    report["ingestion_seconds"] = time.monotonic() - started
    report["pipeline_result"] = str(result)
    datasets = await cognee.datasets.list_datasets()
    dataset = next(d for d in datasets if d.name == DATASET)
    data = await cognee.datasets.list_data(dataset.id)
    report["stored_sources"] = [
        {"id": str(d.id), "metadata": d.external_metadata} for d in data]
    graph = await get_graph_engine()
    report["graph"] = await graph.get_graph_data()
    if not ledger.can_reserve():
        report["query_status"] = "budget_exhausted"
        return
    print("Retrieving across the two documents", flush=True)
    started = time.monotonic()
    context = await asyncio.wait_for(cognee.search(
        query_text=QUESTION, query_type=SearchType.GRAPH_COMPLETION,
        datasets=[DATASET], only_context=True, top_k=5,
    ), timeout=90)
    report["queries"] = [{"question": QUESTION, "context": context,
                          "latency_seconds": time.monotonic() - started}]
    report["success"] = True


async def retire_geography(cognee, report):
    """Retire only this probe's geography derivative, preserving dispatch evidence."""
    from cognee.infrastructure.databases.graph import get_graph_engine

    datasets = await cognee.datasets.list_datasets()
    dataset = next(d for d in datasets if d.name == DATASET)
    data = await cognee.datasets.list_data(dataset.id)
    matches = [d for d in data if d.external_metadata == {
        "source_id": "geography", "revision": "r1"}]
    if len(matches) != 1:
        raise ValueError("expected exactly one synthetic geography revision")
    target = matches[0]
    if target.id != uuid5(NAMESPACE_URL, "dm-assistant-eval/geography/r1"):
        raise ValueError("synthetic data identity mismatch")
    graph = await get_graph_engine()
    report["before_graph"] = await graph.get_graph_data()
    report["retired_source"] = {"data_id": str(target.id), "metadata": target.external_metadata,
                                "preserved_original_text": SOURCES["geography"]}
    report["deletion_result"] = await cognee.datasets.delete_data(
        dataset_id=dataset.id, data_id=target.id, mode="soft")
    report["graph"] = await graph.get_graph_data()
    report["remaining_sources"] = [
        {"id": str(d.id), "metadata": d.external_metadata}
        for d in await cognee.datasets.list_data(dataset.id)]
    report["success"] = True
