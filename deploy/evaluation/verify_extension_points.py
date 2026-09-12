"""Offline verification of Cognee 1.5.3 weighted-edge extension points.

No network, no LLM, no index writes. Run with the isolated evaluation venv:
    .local/cognee-evaluation/.venv/Scripts/python.exe deploy/evaluation/verify_extension_points.py

Answers three questions TKT-0103 depends on, against the installed package:
1. Can extraction request edge strength through public parameters?
2. Where exactly does a custom extracted field fail to reach graph storage?
3. Can the persisted edge model carry weights when populated by other means?
"""
import inspect
import json

import cognee
from cognee.api.v1.cognify.cognify import cognify
from cognee.infrastructure.engine.models.Edge import Edge as PersistedEdge
from cognee.modules.engine.models import Entity
from cognee.modules.graph.utils.expand_with_nodes_and_edges import _add_extracted_edges
from cognee.shared.data_models import Edge as ExtractedEdge, KnowledgeGraph, Node


class WeightedEdge(ExtractedEdge):
    strength: float


class WeightedKnowledgeGraph(KnowledgeGraph):
    edges: list[WeightedEdge] = []


def main() -> None:
    report = {"cognee_version": cognee.__version__}

    params = inspect.signature(cognify).parameters
    report["cognify_graph_model_param"] = "graph_model" in params
    report["cognify_graph_model_default_is_knowledge_graph"] = (
        params["graph_model"].default is KnowledgeGraph)
    report["cognify_custom_prompt_param"] = "custom_prompt" in params

    extracted = WeightedKnowledgeGraph.model_validate({
        "nodes": [
            {"id": "n1", "name": "Romulus", "type": "Person", "description": "Grand Inquisitor."},
            {"id": "n2", "name": "Inquisition", "type": "Organization", "description": "An order."},
        ],
        "edges": [{
            "source_node_id": "n1", "target_node_id": "n2",
            "relationship_name": "commands",
            "description": "Romulus commands the Inquisition.",
            "strength": 0.9,
        }],
    })
    report["strength_requested_parses"] = extracted.edges[0].strength == 0.9

    entities = {"n1": Entity(name="Romulus", description="Grand Inquisitor."),
                "n2": Entity(name="Inquisition", description="An order.")}
    edges_by_identity: dict = {}
    _add_extracted_edges(extracted, entities, edges_by_identity)
    persisted = next(iter(edges_by_identity.values()))
    report["persisted_edge_fields"] = sorted(persisted.model_dump(exclude_none=True))
    report["strength_survives_default_conversion"] = "strength" in persisted.model_dump()

    weighted = PersistedEdge(relationship_type="commands", edge_text="Romulus commands the Inquisition.",
                             weight=0.9, weights={"ingestion_strength": 0.9},
                             properties={"source_record": "command"})
    report["persisted_edge_model_accepts_weights"] = weighted.weight == 0.9 \
        and weighted.weights == {"ingestion_strength": 0.9}
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
