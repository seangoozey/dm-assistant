"""Weighted relationship extraction + manifest-join retrieval trial (TKT-0103).

Runs against the isolated evaluation venv with the persistent budget gateway.
Strength is requested through the public graph_model/custom_prompt parameters
and captured via the calculate_chunk_graphs hook before Cognee's conversion
drops it; the versioned manifest carries it into retrieval-time ranking.
Gold judgments never reach the provider.
"""
import asyncio
import json
import sys
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

STRENGTH_PROMPT = (
    "Extract only entities and relationships supported by the supplied text. "
    "Preserve negation, intentions, attribution, and direction. Do not invent missing links. "
    "For every relationship set strength between 0.0 and 1.0 describing how explicitly the "
    "text states it: 1.0 means directly and unambiguously stated, 0.5 means stated indirectly "
    "or by interpretation, lower values mean weaker implication. Strength expresses "
    "explicitness of support only, never importance, confidence, or likely relevance."
)


async def run(cognee, report, ledger, *, search_only=False, live_slice=False):
    from cognee.infrastructure.databases.graph import get_graph_engine
    from cognee.infrastructure.llm.extraction import extract_content_graph
    from cognee.modules.search.types import SearchType
    from cognee.shared.data_models import Edge as ExtractedEdge, KnowledgeGraph
    from cognee.tasks.ingestion.data_item import DataItem

    from weighted_manifest import build_manifest, rank_and_path

    root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root / "campaign-core"))
    from tests.support.relevance_benchmark import evaluate_v2  # noqa: E402

    dataset = "relevance-v3-live" if live_slice else "relevance-v2"
    corpus_path = (root / ".local/cognee-evaluation/relevance-v3-live-corpus.json" if live_slice
                   else root / "tests/fixtures/relationship_relevance_cases_v2.json")
    corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
    record_metadata = {}
    document_records = {}
    items = []
    for record in corpus["records"]:
        identity = uuid5(NAMESPACE_URL, f"{dataset}/{record['id']}")
        document_records[str(identity)] = record["id"]
        if live_slice:
            record_metadata[str(identity)] = {
                "record_id": record["id"], "revision": record["revision"],
                "state": record["state"], "authority": record["authority"],
                "visibility": record["visibility"]}
        else:
            record_metadata[str(identity)] = {
                "record_id": record["id"], "revision": "1",
                "state": "intended" if record["id"] == "plan" else "established",
                "authority": "explicit_lore", "visibility": "dm_only"}
        items.append(DataItem(data=record["text"], data_id=identity))

    class WeightedEdge(ExtractedEdge):
        strength: float

    class WeightedKnowledgeGraph(KnowledgeGraph):
        edges: list[WeightedEdge] = []

    captures = []
    if not search_only:
        async def capture_extraction(data_chunks, graph_model, custom_prompt, **kwargs):
            graphs = await asyncio.gather(*[
                extract_content_graph(chunk.text, graph_model, custom_prompt=custom_prompt)
                for chunk in data_chunks])
            for chunk, extracted in zip(data_chunks, graphs):
                document = getattr(chunk, "is_part_of", None)
                document_id = str(document.id) if document is not None else chunk.document_id
                captures.append({"document_id": document_id,
                                 "chunk_id": str(chunk.id),
                                 "graph": extracted.model_dump()})
            return graphs

        print("Indexing v2 corpus with weighted extraction", flush=True)
        await asyncio.wait_for(cognee.add(items, dataset_name=dataset), 120)
        await asyncio.wait_for(cognee.cognify(datasets=[dataset], chunks_per_batch=2,
            chunk_size=512, graph_model=WeightedKnowledgeGraph, custom_prompt=STRENGTH_PROMPT,
            calculate_chunk_graphs=capture_extraction), 600)
        manifest = build_manifest(captures, record_metadata)
        runtime_dir = root / ".local" / "cognee-evaluation"
        stem = "relevance-v3-live" if live_slice else "relevance-v2"
        (runtime_dir / f"{stem}-captures.json").write_text(json.dumps(captures, indent=2))
        (runtime_dir / f"{stem}-manifest.json").write_text(json.dumps(manifest, indent=2))
        report["manifest_summary"] = {
            "version": manifest["version"], "entries": len(manifest["entries"]),
            "strength_range": ([e["strength"] for e in manifest["entries"]] and
                               [min(e["strength"] for e in manifest["entries"]),
                                max(e["strength"] for e in manifest["entries"])])}
        captured_documents = {c["document_id"] for c in captures}
        report["extraction_documents_matched"] = sorted(
            document_records[d] for d in captured_documents if d in document_records)

    report["candidate_limit"] = 100 if search_only else 10
    graph = await (await get_graph_engine()).get_graph_data()
    report["graph"] = graph
    nodes = dict(graph[0])
    associations = {}
    for chunk, entity, label, _ in graph[1]:
        if label == "contains" and nodes.get(chunk, {}).get("document_id") in document_records:
            associations.setdefault(entity, set()).add(
                document_records[nodes[chunk]["document_id"]])
    report["indexed_record_ids"] = sorted({r for rs in associations.values() for r in rs})
    if search_only:
        stem = "relevance-v3-live" if live_slice else "relevance-v2"
        manifest = json.loads((root / ".local" / "cognee-evaluation" /
                               f"{stem}-manifest.json").read_text())
    report["rankings"] = {}
    report["edge_paths"] = {}
    report["join_details"] = {}
    for case in corpus["cases"]:
        if not ledger.can_reserve():
            raise RuntimeError("budget exhausted")
        print(f"Native query {case['id']}", flush=True)
        result = await asyncio.wait_for(cognee.search(query_text=case["question"],
            query_type=SearchType.GRAPH_COMPLETION, datasets=[dataset], only_context=True,
            verbose=True, top_k=report["candidate_limit"]), 90)
        returned_edges = []
        for part in result:
            for edge in part["objects_result"]:
                left, right = str(edge.node1.id), str(edge.node2.id)
                returned_edges.append({"left": left, "right": right,
                    "left_name": nodes.get(left, {}).get("name", ""),
                    "right_name": nodes.get(right, {}).get("name", "")})
        rankings, paths, details = rank_and_path(
            manifest, returned_edges,
            lambda left, right: associations.get(left, set()) & associations.get(right, set()))
        report["rankings"][case["id"]] = rankings
        report["edge_paths"][case["id"]] = paths
        report["join_details"][case["id"]] = details
    report["evaluation"] = evaluate_v2(corpus, report["rankings"], report["indexed_record_ids"],
                                       returned_paths=report["edge_paths"],
                                       arm=("cognee-weighted-manifest-join-live-v1" if live_slice
                                            else "cognee-weighted-manifest-join-v1"))
    report["success"] = True
