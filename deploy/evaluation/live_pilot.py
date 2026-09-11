"""User-authorized small live campaign experiment, never a canonical write."""
import asyncio
import hashlib
import json
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from evidence_expansion import Source, expand
from pilot_input import embedding_batches, index_text


async def run(cognee, report, ledger, generation="live-pilot-v2", search_only=False):
    from cognee.infrastructure.databases.graph import get_graph_engine
    from cognee.modules.search.types import SearchType
    from cognee.modules.visualization.cognee_network_visualization import cognee_network_visualization
    from cognee.tasks.ingestion.data_item import DataItem
    from cognee.infrastructure.databases.vector.embeddings.OpenAICompatibleEmbeddingEngine import (
        OpenAICompatibleEmbeddingEngine,
    )

    # Cognee's engine may receive more texts than its configured batch size.
    # Split at the adapter boundary; retain the gateway's per-request cap.
    original_embed = OpenAICompatibleEmbeddingEngine.embed_text

    async def bounded_embed(self, texts):
        if isinstance(texts, str):
            texts = [texts]
        vectors = []
        for batch in embedding_batches(texts):
            vectors.extend(await original_embed(self, batch))
        return vectors

    OpenAICompatibleEmbeddingEngine.embed_text = bounded_embed

    runtime = Path.cwd()
    records = json.loads((runtime / f"{generation}-input.json").read_text(encoding="utf-8"))
    if not 1 <= len(records) <= (12 if generation == "live-pilot-v2" else 64):
        raise ValueError("pilot exceeds authorized subset")
    output = runtime / generation
    output.mkdir(exist_ok=True)
    manifest, items = {}, []
    for r in records:
        revision = hashlib.sha256(json.dumps(r, sort_keys=True).encode()).hexdigest()
        identity = uuid5(NAMESPACE_URL, f"dm-assistant/live-pilot/{r['record_id']}/{revision}")
        text = index_text(r, generation)
        manifest[str(identity)] = Source(r["record_id"], revision, text)
        items.append(DataItem(data=text, data_id=identity))
    report["input_records"] = len(records)
    if not search_only:
        print(f"Indexing {len(records)} authorized DM-only claims", flush=True)
        await asyncio.wait_for(cognee.add(items, dataset_name=f"dm-{generation}"), timeout=120)
        await asyncio.wait_for(cognee.cognify(datasets=[f"dm-{generation}"], chunks_per_batch=2),
                               timeout=900)
    graph = await (await get_graph_engine()).get_graph_data()
    report["graph"] = graph
    (output / "graph.json").write_text(json.dumps(graph, default=str), encoding="utf-8")
    await cognee_network_visualization(graph, str(output / "graph.html"))
    report["expanded_results"] = {}
    for question in (
        "Where was Ishi'go'dan sent, and on which island is that place?",
        "Where are the cultists summoning Ragga'na'ken?",
    ):
        if not ledger.can_reserve():
            raise RuntimeError("budget limit reached")
        print("Retrieving graph context", flush=True)
        result = await asyncio.wait_for(cognee.search(query_text=question,
            query_type=SearchType.GRAPH_COMPLETION, datasets=[f"dm-{generation}"],
            only_context=True, verbose=True, top_k=5), timeout=90)
        seeds = list(dict.fromkeys(str(n.id) for part in result for edge in part["objects_result"]
                                   for n in (edge.node1, edge.node2)))
        report["expanded_results"][question] = expand(graph, seeds, manifest)
    report["success"] = True
    report["viewer"] = str(output / "graph.html")
