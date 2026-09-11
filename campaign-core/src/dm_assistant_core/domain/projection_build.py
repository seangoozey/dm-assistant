"""Validate a Core-owned snapshot manifest, not model assertions or index quality."""

import hashlib
import json

from dm_assistant_core.domain.derived_retrieval import record_fingerprint
from dm_assistant_core.domain.retrieval import RetrievalQuery, RetrievalRecord, _is_visible
from dm_assistant_core.domain.retrieval_paths import CurrentLink


def validate_manifest(
    query: RetrievalQuery, records: tuple[RetrievalRecord, ...], links: tuple[CurrentLink, ...],
) -> str:
    """Check complete supplied snapshot, preserving planning only as context.

    Caller obtains this snapshot from Core, not the provider. This cannot prove
    that the producer supplied every campaign record or an external index loaded it.
    """
    nodes = {r.record_id: record_fingerprint(r) for r in records}
    if len(nodes) != len(records) or len({e.edge_id for e in links}) != len(links):
        raise ValueError("duplicate projection identities")
    for record in records:
        if (not _is_visible(record, query) or not record.accepted
                or record.kind not in {"claim", "relationship", "alias"}
                or record.state in {"superseded", "rejected"}
                or not record.evidence_binding):
            raise ValueError("ineligible projection record")
    for link in links:
        if (link.from_id not in nodes or link.to_id not in nodes
                or link.from_id == link.to_id
                or any(nodes.get(e.record_id) != e.fingerprint for e in link.evidence)):
            raise ValueError("invalid projection link")
    payload = {"version": 1, "visibility": query.requester_visibility.model_dump(),
               "nodes": sorted(nodes.items()),
               "links": [e.model_dump() for e in sorted(links, key=lambda e: e.edge_id)]}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
