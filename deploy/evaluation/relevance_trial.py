"""Isolated native retrieval diagnostic; gold judgments never reach providers."""
import asyncio
import json
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5


async def run(cognee, report, ledger, *, search_only=False):
    from cognee.infrastructure.databases.graph import get_graph_engine
    from cognee.modules.search.types import SearchType
    from cognee.tasks.ingestion.data_item import DataItem

    root = Path(__file__).resolve().parents[2]
    corpus = json.loads((root / "tests/fixtures/relationship_relevance_cases.json").read_text())
    manifest = {}
    items = []
    for record in corpus["records"]:
        identity = uuid5(NAMESPACE_URL, f"relevance-v1/{record['id']}")
        manifest[str(identity)] = record["id"]
        items.append(DataItem(data=record["text"], data_id=identity))
    dataset = "relevance-v1"
    if not search_only:
        print("Indexing clean synthetic relevance corpus", flush=True)
        await asyncio.wait_for(cognee.add(items, dataset_name=dataset), 120)
        await asyncio.wait_for(cognee.cognify(datasets=[dataset], chunks_per_batch=2,
            chunk_size=512, custom_prompt="Extract only entities and relationships supported by the supplied text. Preserve negation, intentions, attribution, and direction. Do not invent missing links."), 600)
    report["candidate_limit"] = 100 if search_only else 10
    graph = await (await get_graph_engine()).get_graph_data()
    report["graph"] = graph
    nodes = dict(graph[0])
    associations = {}
    for chunk, entity, label, _ in graph[1]:
        if label == "contains" and nodes.get(chunk, {}).get("document_id") in manifest:
            associations.setdefault(entity, set()).add(manifest[nodes[chunk]["document_id"]])
    report["rankings"] = {}
    report["indexed_record_ids"] = sorted({r for rs in associations.values() for r in rs})
    report["edge_paths"] = {}
    for case in corpus["cases"]:
        if not ledger.can_reserve():
            raise RuntimeError("budget exhausted")
        print(f"Native query {case['id']}", flush=True)
        result = await asyncio.wait_for(cognee.search(query_text=case["question"],
            query_type=SearchType.GRAPH_COMPLETION, datasets=[dataset], only_context=True,
            verbose=True, top_k=report["candidate_limit"]), 90)
        ranked, paths = [], []
        for part in result:
            for edge in part["objects_result"]:
                left, right = str(edge.node1.id), str(edge.node2.id)
                # Shared original passage supports the returned relationship.
                # Endpoint-only fallback is kept separate from this diagnostic.
                sources = sorted(associations.get(left, set()) & associations.get(right, set()))
                for source in sources:
                    if source not in ranked:
                        ranked.append(source)
                paths.append({"left": left, "right": right, "sources": sources})
        report["rankings"][case["id"]] = ranked
        report["edge_paths"][case["id"]] = paths
    report["success"] = True
