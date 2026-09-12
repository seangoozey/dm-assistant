"""Versioned weighted-edge manifest: extraction strength kept beside, never as, truth.

Pure offline module (no Cognee import) so tests run in the main development venv.
Aggregation reuses relationship_projection: incompatible contributions stay
separate, repeated original evidence cannot multiply support, and strength is
averaged over unique evidence. The manifest ranks retrieval only; it is not
truth, authority, support count, or conflict verification.
"""
from pydantic import BaseModel, ConfigDict, Field

from relationship_projection import Contribution, aggregate

MANIFEST_VERSION = "weighted-relationship-manifest-v1"


class ExtractedNode(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)
    id: str
    name: str
    type: str


class ExtractedEdge(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)
    source_node_id: str
    target_node_id: str
    relationship_name: str
    description: str | None = None
    strength: float = Field(ge=0, le=1, allow_inf_nan=False)


class ExtractedGraph(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)
    nodes: list[ExtractedNode] = []
    edges: list[ExtractedEdge] = []


def normalize_name(value: str) -> str:
    """Canonical surface form for joining extraction names to returned nodes.

    Case-folding, apostrophe removal, and leading-article stripping are safe
    symmetrical transforms: both sides of a join pass through this function.
    Deeper variance (title prefixes, different surface names for the same
    concept) needs identity-based joining, not more normalization.
    """
    words = value.casefold().replace("'", "").split()
    while words and words[0] in {"the", "a", "an"}:
        words = words[1:]
    return " ".join(words)


def contributions(captures, record_metadata):
    """Map captured extraction graphs to evidence contributions.

    captures: [{"document_id": str, "graph": {...}}] in ingestion order.
    record_metadata: {document_id: {record_id, revision, state, authority,
    visibility, attribution?, negated?, time_scope?}}. Edges referencing
    unknown node ids are skipped, mirroring Cognee conversion behavior.
    """
    out = []
    for capture in captures:
        meta = record_metadata[capture["document_id"]]
        graph = ExtractedGraph.model_validate(capture["graph"])
        names = {node.id: normalize_name(node.name) for node in graph.nodes}
        for edge in graph.edges:
            if edge.source_node_id not in names or edge.target_node_id not in names:
                continue
            out.append(Contribution(
                source=names[edge.source_node_id], target=names[edge.target_node_id],
                relation=normalize_name(edge.relationship_name),
                description=edge.description or "",
                evidence_id=meta["record_id"], revision=meta["revision"],
                state=meta["state"], authority=meta["authority"],
                visibility=meta["visibility"],
                attribution=meta.get("attribution", ""),
                negated=meta.get("negated", False),
                time_scope=meta.get("time_scope", "present"),
                strength=edge.strength))
    return out


def build_manifest(captures, record_metadata):
    return {"version": MANIFEST_VERSION,
            "entries": aggregate(contributions(captures, record_metadata)),
            "notes": ("Extraction strength expresses how explicitly source text states "
                      "a relationship. It ranks retrieval only; it is not truth, authority, "
                      "support count, or conflict verification.")}


def renormalize(manifest):
    """Re-key an existing manifest under the current name normalization, offline.

    Aggregated entries retain every contribution field, so re-normalizing
    endpoint/relation names and re-aggregating reproduces the manifest a fresh
    extraction would have produced — no provider call required.
    """
    rebuilt = []
    for entry in manifest["entries"]:
        for captured in entry["contributions"]:
            rebuilt.append(Contribution(
                source=normalize_name(entry["source"]),
                target=normalize_name(entry["target"]),
                relation=normalize_name(entry["relation"]),
                description=captured.get("description", ""),
                evidence_id=captured["evidence_id"], revision=captured["revision"],
                state=entry["state"], authority=entry["authority"],
                visibility=entry["visibility"], attribution=entry["attribution"],
                negated=entry["negated"], time_scope=entry["time_scope"],
                strength=captured["strength"]))
    return {"version": manifest["version"], "entries": aggregate(rebuilt),
            "notes": manifest.get("notes", "")}


def join_edge(entries, left_name, right_name):
    """Match a returned edge against manifest entries by endpoint pair, either direction."""
    left, right = normalize_name(left_name), normalize_name(right_name)
    for entry in entries:
        if entry["source"] == left and entry["target"] == right:
            return entry, False
        if entry["source"] == right and entry["target"] == left:
            return entry, True
    return None, None


def rank_and_path(manifest, returned_edges, fallback_sources):
    """Join returned edges to the manifest; explicit provenance decides path claims.

    returned_edges: [{"left": id, "right": id, "left_name": str, "right_name": str}]
    in native return order. fallback_sources(left_id, right_id) supplies
    co-occurrence record ids for ranking's lower tier only; it never creates a
    path claim. Manifest-backed records rank by best matching strength
    (descending, then first-seen); co-occurrence-only records follow in return
    order; every result stays deterministic.
    """
    entries = manifest["entries"]
    rankings: list[str] = []
    best: dict[str, float] = {}
    first_seen: dict[str, int] = {}
    fallback_order: list[str] = []
    paths: list[list[str]] = []
    details = []
    for position, edge in enumerate(returned_edges):
        entry, reversed_navigation = join_edge(entries, edge["left_name"], edge["right_name"])
        if entry is None:
            sources = sorted(fallback_sources(edge["left"], edge["right"]))
            for source in sources:
                if source not in first_seen:
                    first_seen[source] = position
                    fallback_order.append(source)
            details.append({"position": position, "left_name": edge["left_name"],
                            "right_name": edge["right_name"], "manifest_matched": False,
                            "records": sources})
            continue
        records = sorted({c["evidence_id"] for c in entry["contributions"]})
        paths.append(records)
        for source in records:
            if source not in first_seen:
                first_seen[source] = position
            best[source] = max(best.get(source, 0.0), entry["strength"])
        details.append({"position": position, "left_name": edge["left_name"],
                        "right_name": edge["right_name"], "manifest_matched": True,
                        "reversed_navigation": reversed_navigation,
                        "relation": entry["relation"], "state": entry["state"],
                        "strength": entry["strength"],
                        "support_count": entry["support_count"], "records": records})
    backed = sorted(best, key=lambda rid: (-best[rid], first_seen[rid]))
    rankings = backed + [r for r in fallback_order if r not in best]
    return rankings, paths, details
