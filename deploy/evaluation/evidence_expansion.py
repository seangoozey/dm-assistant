"""Synthetic evaluator only: expand retrieved IDs to validated source passages.

This does not validate semantic entailment or authorize a production graph path.
The manifest is supplied by the caller, never inferred from generated descriptions.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Source:
    source_id: str
    revision: str
    text: str


def expand(graph, seeds: list[str], manifest: dict[str, Source], limit: int = 10) -> dict:
    if not 1 <= limit <= 100:
        raise ValueError("passage limit must be 1..100")
    nodes = dict(graph[0])
    eligible = {}
    for identity, node in nodes.items():
        if node.get("type") != "DocumentChunk":
            continue
        source = manifest.get(node.get("document_id"))
        text = node.get("text")
        if not source or not isinstance(text, str) or not text or source.text.count(text) != 1:
            continue
        start = source.text.index(text)
        eligible[identity] = {
            "chunk_id": identity, "document_id": node["document_id"],
            "source_id": source.source_id, "revision": source.revision,
            "start": start, "end": start + len(text), "text": text,
        }
    incoming = {}
    for source, target, kind, _ in graph[1]:
        if kind == "contains" and source in eligible and nodes.get(target, {}).get("type") == "Entity":
            incoming.setdefault(target, set()).add(source)
    results = {}
    for seed in dict.fromkeys(seeds):
        chunks = [seed] if seed in eligible else sorted(incoming.get(seed, []))
        for chunk in chunks:
            if chunk not in results:
                results[chunk] = {**eligible[chunk], "retrieval_path": [seed, chunk] if seed != chunk else [chunk]}
    return {"passages": list(results.values())[:limit], "truncated": len(results) > limit,
            "generated_descriptions_are_evidence": False}
