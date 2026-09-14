"""Opt-in DM-only pilot: stored Cognee associations retrieve current Core text.

No provider calls on reads. One changed/hidden/missing record disables the whole
small generation, so stale intermediate associations cannot leak a visible result.
"""

import json
import re
from pathlib import Path
from typing import Any

from dm_assistant_core.application.retrieval import CurrentRecordRepository, RetrievalService
from dm_assistant_core.domain.derived_retrieval import record_fingerprint
from dm_assistant_core.domain.retrieval import (
    EvidenceRole,
    GraphConnectionSource,
    RetrievalQuery,
    RetrievalRecord,
    RetrievalResult,
)


def normalized(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", text.casefold())


class GraphPilotRetrieval(RetrievalService):
    def __init__(self, fallback: RetrievalService, repository: CurrentRecordRepository,
                 bundle_path: str) -> None:
        self._fallback = fallback
        self._current = repository
        self._bundle_path = Path(bundle_path)

    def query(self, query: RetrievalQuery) -> RetrievalResult:
        result = self._fallback.query(query)
        if query.requester_visibility.role != "dm":
            return result
        try:
            if self._bundle_path.stat().st_size > 8_000_000:
                return result
            bundle = json.loads(self._bundle_path.read_text(encoding="utf-8"))
            expected = tuple(RetrievalRecord.model_validate(r) for r in bundle["records"])
            # The v3 pilot capped at 64 records; canonical bundles (live-pilot-v4+)
            # carry the whole current claim set and every record is still
            # fingerprint-revalidated against Core before any trace is trusted.
            if not 1 <= len(expected) <= 2000:
                return result
            current = self._current.current_records(
                query.model_copy(update={"tags": (), "entity_kinds": ()}),
                tuple(r.record_id for r in expected))
            if {r.record_id: record_fingerprint(r) for r in expected} != {
                    r.record_id: record_fingerprint(r) for r in current}:
                return result
            source_ids: dict[str, tuple[str, ...]] = {}
            traces = graph_targets(bundle, query.question, source_ids)
        except (OSError, ValueError, KeyError, TypeError):
            return result
        from dm_assistant_core.domain.retrieval import RetrievedEvidence

        additions = {r.record_id: RetrievedEvidence(
            record_id=r.record_id, assertion=r.assertion, citation=r.citation,
            state=r.state, authority=r.authority, role=EvidenceRole.CONTEXT, entity_id=r.entity_id,
            graph_trace=traces[r.record_id],
            graph_sources=tuple(GraphConnectionSource(record_id=s.record_id,
                assertion=s.assertion, citation=s.citation, state=s.state)
                for s in current if s.record_id in source_ids.get(r.record_id, ())),
        ) for r in current if r.record_id in traces
            and (not query.tags or set(query.tags).issubset(r.tags))
            and (not query.entity_kinds or r.entity_kind in query.entity_kinds)}
        # Existing policy decisions are unchanged; graph additions supply no support.
        evidence = tuple(e.model_copy(update={"graph_trace": additions[e.record_id].graph_trace,
                         "graph_sources": additions[e.record_id].graph_sources})
                         if e.record_id in additions else e for e in result.evidence)
        present = {e.record_id for e in evidence}
        evidence += tuple(e for identity, e in additions.items() if identity not in present)
        return result.model_copy(update={"evidence": evidence,
            "citations": tuple(sorted({e.citation for e in evidence}))})


def graph_targets(bundle: dict[str, Any], question: str,
                  source_ids: dict[str, tuple[str, ...]] | None = None,
                  ) -> dict[str, tuple[str, ...]]:
    """Bounded associations, not asserted relations; retain shared source context."""
    nodes = dict(bundle["graph"][0])
    # Possessives must still seed: "Romulus's organization" seeds Romulus.
    stripped = question.replace("'s", " ").replace("’s", " ")
    query_text = f" {normalized(stripped)} "
    def _in_query(value: str) -> bool:
        return len(normalized(value)) >= 3 and f" {normalized(value)} " in query_text

    seeds = {identity for identity, node in nodes.items() if node.get("type") == "Entity"
             and (_in_query(node.get("name", ""))
                  or any(_in_query(alias) for alias in node.get("aliases", [])))}
    paths = {s: (f"Matched graph entity: {nodes[s].get('name', s)}",) for s in seeds}
    associations: dict[str, set[str]] = {}
    for chunk, entity, label, _ in bundle["graph"][1]:
        node = nodes.get(chunk, {})
        source = bundle["documents"].get(node.get("document_id"))
        if (label == "contains" and node.get("type") == "DocumentChunk" and source
                and node.get("text") and source["text"].count(node["text"]) == 1):
            associations.setdefault(entity, set()).add(source["record_id"])
    path_sources: dict[str, tuple[str, ...]] = {s: () for s in seeds}
    adjacency: dict[str, list[tuple[str, str, tuple[str, ...]]]] = {}
    for left, right, label, attrs in bundle["graph"][1]:
        if (nodes.get(left, {}).get("type") != "Entity"
                or nodes.get(right, {}).get("type") != "Entity"):
            continue
        if label in ("member_of", "leader_of"):
            # Audited roster seats stand on their DM decision receipt, not on
            # shared claim text — they traverse even when no claim co-mentions
            # the member with the faction.
            role = attrs.get("role")
            hint = (f"{nodes[left].get('name', left)} holds {role} in {nodes[right].get('name', right)}"
                    if role
                    else f"{nodes[left].get('name', left)} is a member of {nodes[right].get('name', right)}")
            adjacency.setdefault(left, []).append((right, hint, ()))
            adjacency.setdefault(right, []).append((left, hint, ()))
            continue
        shared = tuple(sorted(associations.get(left, set()) & associations.get(right, set())))
        if not shared:
            continue
        # Co-occurrence gives inspectable context, not proof of the generated label.
        hint = f"{nodes[left].get('name', left)} ↔ {nodes[right].get('name', right)}"
        adjacency.setdefault(left, []).append((right, hint, shared))
        adjacency.setdefault(right, []).append((left, hint, shared))
    frontier = sorted(seeds)
    for _depth in range(2):
        next_frontier = []
        for origin in frontier:
            # Broad hubs (world, magic, etc.) must not flood the result set.
            if origin not in seeds and len(adjacency.get(origin, [])) > 12:
                continue
            for target, hint, shared in sorted(adjacency.get(origin, [])):
                if target in paths or len(paths) >= 40:
                    continue
                previous = () if origin in seeds else paths[origin]
                paths[target] = (*previous, f"Connected through: {hint}")
                path_sources[target] = tuple(sorted(set(path_sources[origin]) | set(shared)))
                next_frontier.append(target)
        frontier = next_frontier
    targets: dict[str, tuple[str, ...]] = {}
    for chunk, entity, label, _ in bundle["graph"][1]:
        if label != "contains" or entity not in paths:
            continue
        node = nodes.get(chunk, {})
        source = bundle["documents"].get(node.get("document_id"))
        if (node.get("type") == "DocumentChunk" and source
                and node.get("text") and source["text"].count(node["text"]) == 1
                and source["record_id"] not in targets):
            # First deterministic edge wins; ranking is the scoring contract's job.
            if source_ids is not None:
                source_ids[source["record_id"]] = path_sources[entity]
            targets[source["record_id"]] = (*paths[entity],
                f"Stored contains edge: {chunk} → {entity}",
                "Exact source passage; graph labels are not verified facts.")
    return targets
