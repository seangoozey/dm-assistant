"""Synthetic, answer-key-free input for future relationship-discovery evaluation.

This exports JSON only. It does not import Cognee, contact a provider, or read live data.
Run from campaign-core with: python -m tests.support.knowledge_discovery_input
"""

import json

from tests.support.connected_knowledge_harness import Corpus, load


def discovery_input(corpus: Corpus, case_id: str) -> dict[str, object]:
    case = next(case for case in corpus.cases if case.id == case_id)
    # A scenario corpus can differ (e.g. an explicitly contradictory source is
    # present only in its conflict scenario). Selection never consults required IDs.
    records = [record for record in corpus.records
               if record.record_id not in case.excluded_ids and record.state != "superseded"]
    return {
        "schema_version": 1,
        "synthetic_only": True,
        "sources": [{
            "record_id": record.record_id,
            "entity_id": record.entity_id,
            "assertion": record.assertion,
            "source_id": record.source_id,
            "citation": record.citation,
            "state": record.state.value,
            "authority": record.authority.value,
            "visibility": record.visibility,
            "accepted": record.accepted,
        } for record in sorted(records, key=lambda item: item.record_id)],
    }


if __name__ == "__main__":
    corpus = load()
    inputs = {case.id: discovery_input(corpus, case.id) for case in corpus.cases}
    print(json.dumps(inputs, indent=2))
