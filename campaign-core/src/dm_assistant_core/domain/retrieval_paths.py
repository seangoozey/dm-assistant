"""Internal path authorization over trusted current Core snapshots.

Not a graph importer: the index supplies only node snapshots and edge IDs. Core
must load edges and all their evidence records in the same snapshot as nodes.
All records here use the existing retrieval families; entity traversal is deferred.
"""

from pydantic import BaseModel, ConfigDict, Field

from dm_assistant_core.domain.derived_retrieval import IndexSuggestion, record_fingerprint
from dm_assistant_core.domain.retrieval import RetrievalQuery, RetrievalRecord, _is_visible


class PathSuggestion(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    scope_id: str = Field(min_length=1)
    generation: str = Field(min_length=1)
    nodes: tuple[IndexSuggestion, ...] = Field(min_length=1, max_length=3)
    edge_ids: tuple[str, ...] = Field(max_length=2)


class CurrentLink(BaseModel):
    """Trusted Core association, never deserialized from provider output."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    edge_id: str
    from_id: str
    to_id: str
    evidence: tuple[IndexSuggestion, ...] = Field(min_length=1, max_length=20)


def authorized_targets(
    query: RetrievalQuery,
    paths: tuple[PathSuggestion, ...],
    records: tuple[RetrievalRecord, ...],
    links: tuple[CurrentLink, ...],
    *,
    scope_id: str,
    generation: str,
    seed_ids: frozenset[str],
) -> tuple[IndexSuggestion, ...]:
    """Return context candidates, never transitive facts or rejection details.

Scope/generation and seed IDs must come from Core's authenticated request context,
not from the index. Scope IDs identify visibility-isolated projection generations.
This function validates, but does not build or authenticate, those projections.
"""
    if len(paths) > 100:
        raise ValueError("at most 100 paths allowed")
    current = {r.record_id: r for r in records}
    edges = {e.edge_id: e for e in links}
    if len(current) != len(records) or len(edges) != len(links):
        raise ValueError("ambiguous current snapshot")

    def eligible(node: IndexSuggestion) -> bool:
        r = current.get(node.record_id)
        return bool(r is not None and _is_visible(r, query)
                    and r.kind in {"claim", "relationship", "alias"}
                    and r.state not in {"superseded", "rejected"}
                    and record_fingerprint(r) == node.fingerprint)

    targets: dict[str, IndexSuggestion] = {}
    for path in paths:
        ids = tuple(n.record_id for n in path.nodes)
        if (path.scope_id != scope_id or path.generation != generation
                or ids[0] not in seed_ids or len(set(ids)) != len(ids)
                or len(path.edge_ids) != len(ids) - 1
                or not all(eligible(n) for n in path.nodes)):
            continue
        valid = True
        for i, edge_id in enumerate(path.edge_ids):
            edge = edges.get(edge_id)
            if (edge is None or (edge.from_id, edge.to_id) != (ids[i], ids[i + 1])
                    or not all(eligible(e) for e in edge.evidence)):
                valid = False
                break
        if valid:
            target = path.nodes[-1]
            targets[target.record_id] = target
    return tuple(targets.values())
