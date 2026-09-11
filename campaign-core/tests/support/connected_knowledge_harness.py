"""Offline lexical-policy baseline; not a database or end-to-end benchmark."""

import json
from pathlib import Path
from time import perf_counter

from pydantic import BaseModel, ConfigDict

from dm_assistant_core.adapters.postgres.retrieval import _query_terms
from dm_assistant_core.domain.retrieval import (
    RequesterVisibility,
    RetrievalPolicy,
    RetrievalQuery,
    RetrievalRecord,
)

FIXTURE = Path(__file__).resolve().parents[3] / "tests/fixtures/connected_knowledge_cases.json"


class Case(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    workflow: str
    question: str
    required_ids: list[str]
    expected_mode: str
    forbidden_ids: list[str]
    forbidden_support_ids: list[str]
    required_paths: list[list[str]]
    forbidden_paths: list[list[str]]
    requester_visibility: RequesterVisibility
    ambiguity_expected: bool = False
    excluded_ids: list[str] = ["contradiction"]


class Corpus(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: int
    origin: str
    records: list[RetrievalRecord]
    cases: list[Case]


def load() -> Corpus:
    corpus = Corpus.model_validate_json(FIXTURE.read_text(encoding="utf-8"))
    ids = {record.record_id for record in corpus.records}
    assert len(ids) == len(corpus.records)
    assert len({case.id for case in corpus.cases}) == len(corpus.cases)
    nodes = ids | {record.entity_id for record in corpus.records if record.entity_id}
    for case in corpus.cases:
        assert set(case.required_ids + case.forbidden_ids + case.forbidden_support_ids) <= ids
        assert set(case.excluded_ids) <= ids
        assert not set(case.required_ids) & set(case.forbidden_ids + case.excluded_ids)
        assert all(set(path) <= nodes for path in case.required_paths + case.forbidden_paths)
    return corpus


def run(corpus: Corpus, *, reverse: bool = False) -> dict:
    results = []
    for case in corpus.cases:
        query = RetrievalQuery(
            question=case.question, requester_visibility=case.requester_visibility
        )
        terms = _query_terms(case.question)
        records = list(reversed(corpus.records)) if reverse else corpus.records
        # Simulate SQL supersession exclusion and lexical matching. This deliberately
        # does not claim to exercise SQL, entity-name/alias joins, or network latency.
        selected = tuple(sorted((
            record for record in records
            if record.state != "superseded" and record.record_id not in case.excluded_ids
            and (not terms or terms & _query_terms(record.assertion))
        ), key=lambda record: (record.citation, record.record_id))[:100])
        start = perf_counter()
        result = RetrievalPolicy().evaluate(query, selected)
        elapsed = (perf_counter() - start) * 1000
        ids = [item.record_id for item in result.evidence[:10]]
        relevant = set(case.required_ids)
        hits = len(set(ids) & relevant)
        results.append({
            "id": case.id, "workflow": case.workflow, "returned_ids": ids,
            "required_ids": case.required_ids, "mode": result.answer_mode.value,
            "expected_mode": case.expected_mode,
            "mode_correct": result.answer_mode.value == case.expected_mode,
            "recall_at_10": hits / len(relevant) if relevant else None,
            "precision_at_10": hits / len(ids) if ids else None,
            "forbidden_evidence": sorted(set(ids) & set(case.forbidden_ids)),
            "forbidden_support": [item.record_id for item in result.evidence
                                  if item.role == "support"
                                  and item.record_id in case.forbidden_support_ids],
            "required_paths": case.required_paths,
            "path_recall": 0 if case.required_paths else None,
            "unsupported_connections": None,
            "ambiguity_supported": False if case.ambiguity_expected else None,
            "policy_latency_ms": elapsed,
        })
    return {"schema_version": 1, "baseline": "offline lexical simulation + production policy",
            "path_status": "unsupported; safety and path precision not measurable",
            "cases": results}


if __name__ == "__main__":
    print(json.dumps(run(load()), indent=2))
