"""Isolated, bounded retrieval paths. Never infer transitive campaign facts."""
from collections import defaultdict, deque
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str
    revision: str
    state: str
    authority: str
    visibility: str
    current: bool
    time_eligible: bool


class Link(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str
    source: str
    target: str
    relation: str
    kind: Literal["recorded", "suggested", "structural"]
    evidence: tuple[Evidence, ...] = Field(min_length=1)
    identities_resolved: bool


def discover(seed: str, links: list[Link], *, allowed_visibility: set[str],
             current_revisions: dict[str, str], max_depth: int = 2,
             fanout: int = 12, budget: int = 100) -> dict:
    """Input ordering is the upstream query ranking; this is not a ranker.

    Inverse navigation retains original endpoints and marks its direction.
    Output paths remain retrieval explanations, not composed predicates.
    """
    if not 1 <= max_depth <= 4 or not 1 <= fanout <= 100 or not 1 <= budget <= 1000:
        raise ValueError("invalid traversal bounds")
    if len({link.id for link in links}) != len(links):
        raise ValueError("duplicate link identity")
    adjacency = defaultdict(list)
    for link in links:
        if link.kind == "structural" or not link.identities_resolved:
            continue
        if not all(e.current and e.time_eligible and e.visibility in allowed_visibility
                   and e.state not in {"rejected", "superseded"}
                   and current_revisions.get(e.id) == e.revision for e in link.evidence):
            continue
        adjacency[link.source].append((link.target, link, False))
        adjacency[link.target].append((link.source, link, True))
    queue = deque([(seed, (seed,), [])])
    paths = []
    steps = 0
    truncated = False
    while queue:
        node, visited, path = queue.popleft()
        if len(path) >= max_depth:
            continue
        options = [x for x in adjacency[node] if x[0] not in visited]
        truncated |= len(options) > fanout
        for target, link, reverse in options[:fanout]:
            if steps >= budget:
                return {"paths": paths, "truncated": True}
            steps += 1
            step = {"link_id": link.id, "source": link.source, "target": link.target,
                    "relation": link.relation, "kind": link.kind, "reverse_navigation": reverse,
                    "evidence": [e.model_dump() for e in link.evidence]}
            extended = path + [step]
            paths.append({"target": target, "steps": extended,
                          "meaning": "retrieval_path_not_transitive_fact"})
            queue.append((target, visited + (target,), extended))
    return {"paths": paths, "truncated": truncated}
