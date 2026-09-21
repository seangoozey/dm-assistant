"""Entity graph neighborhood gather (TKT-0120 expansion layer).

Precision-profile graph traversal for prose drafting — the opposite operating
point from brainstorm's recall search. Only audited structural edges
(member_of / leader_of seats) and ranked co-mention proximity leave the
bundle, capped and labeled. Rows are discovery aids: they cite the audited
records behind the edges (roster seats, co-mentions), never the graph edge
itself as proof.
"""

import json
from pathlib import Path
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict

MAX_ROWS = 24


class GraphRelationRow(BaseModel):
    model_config = ConfigDict(frozen=True)
    key: str
    text: str
    backing: str


class EntityNameLookup(Protocol):
    def get(self, entity_id: str) -> Any: ...


class EntityGraphNeighborhoodService:
    """Serve a bounded, ranked neighborhood for an entity from the pilot bundle."""

    def __init__(self, bundle_path: str, names: EntityNameLookup) -> None:
        self._bundle_path = Path(bundle_path)
        self._names = names

    def neighborhood(self, entity_id: str) -> list[GraphRelationRow]:
        entity = self._names.get(entity_id)
        name = getattr(entity, "canonical_name", None)
        if not name:
            return []
        try:
            if self._bundle_path.stat().st_size > 8_000_000:
                return []
            bundle = json.loads(self._bundle_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return []
        return graph_neighborhood(bundle, name)


def graph_neighborhood(bundle: dict[str, Any], name: str) -> list[GraphRelationRow]:
    nodes: dict[str, dict[str, Any]] = dict(bundle["graph"][0])
    edges = bundle["graph"][1]

    def node_name(identity: str) -> str:
        return str(nodes.get(identity, {}).get("name", identity))

    seed = next(
        (
            identity
            for identity, node in nodes.items()
            if node.get("type") == "Entity"
            and node.get("name", "").casefold() == name.casefold()
        ),
        None,
    )
    if seed is None:
        return []

    rows: list[GraphRelationRow] = []
    seen_texts: set[str] = set()

    def add(text: str, backing: str) -> None:
        if text in seen_texts or len(rows) >= MAX_ROWS:
            return
        seen_texts.add(text)
        rows.append(GraphRelationRow(
            key=f"graph:{len(rows)}", text=text, backing=backing))

    # Layer 1 — audited seats touching the entity, then one more hop through
    # the factions it belongs to (a member's faction's leadership, siblings).
    # A faction seed reads its own roster (it is the target of the edges).
    factions: set[str] = set()
    for left, right, label, attrs in edges:
        if label not in ("member_of", "leader_of") or seed not in (left, right):
            continue
        if nodes.get(left, {}).get("type") != "Entity" or nodes.get(right, {}).get("type") != "Entity":
            continue
        role = attrs.get("role")
        if seed == left:
            factions.add(right)
            if label == "leader_of":
                add(f"{node_name(seed)} leads {node_name(right)}"
                    + (f" as {role}" if role else ""),
                    "audited leadership seat (receipted roster decision)")
            else:
                add(f"{node_name(seed)} is a member of {node_name(right)}",
                    "audited membership record")
        elif label == "leader_of":
            add(f"{node_name(left)} leads {node_name(seed)}"
                + (f" as {role}" if role else ""),
                "audited leadership seat (receipted roster decision)")
        else:
            add(f"{node_name(left)} is a member of {node_name(seed)}",
                "audited membership record")
    # One hop out through the entity's factions: their seats and siblings.
    for left, right, label, attrs in edges:
        if label not in ("member_of", "leader_of"):
            continue
        if right in factions and left != seed and nodes.get(left, {}).get("type") == "Entity":
            role = attrs.get("role")
            if label == "leader_of":
                add(f"{node_name(left)} leads {node_name(right)}"
                    + (f" as {role}" if role else ""),
                    "audited leadership seat (receipted roster decision)")
            else:
                add(f"{node_name(left)} is a member of {node_name(right)}",
                    "audited membership record")

    # Layer 2 — ranked co-mention proximity (derived, inspectable context).
    counts: dict[str, int] = {}
    for left, right, label, _ in edges:
        if label != "co_mention" or seed not in (left, right):
            continue
        other = left if seed == right else right
        if nodes.get(other, {}).get("type") == "Entity":
            counts[node_name(other)] = counts.get(node_name(other), 0) + 1
    for partner, count in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
        add(f"Frequently appears with {partner} ({count} shared documents)",
            "derived co-mention association")
    return rows
