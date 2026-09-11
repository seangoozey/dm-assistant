"""Score saved backend results offline; never call providers or mutate campaign data.

Usage: python -m tests.support.knowledge_evaluation results.json
"""

import json
import sys
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from tests.support.connected_knowledge_harness import Corpus, load


class CaseOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    case_id: str
    evidence_ids: list[str] = Field(default_factory=list)
    mode: str | None = None
    paths: list[list[str]] | None = None
    error: str | None = None
    latency_ms: float | None = Field(default=None, ge=0, allow_inf_nan=False)

    @model_validator(mode="after")
    def unique_evidence(self):
        if len(self.evidence_ids) != len(set(self.evidence_ids)):
            raise ValueError("duplicate evidence IDs would inflate ranking scores")
        return self


class EvaluationRun(BaseModel):
    model_config = ConfigDict(extra="forbid")
    arm: Literal["lexical", "known_links", "llm_discovery"]
    backend_version: str = Field(min_length=1)
    model: str | None = None
    embedding_model: str | None = None
    configuration_id: str = Field(min_length=1)
    cost_usd: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    outputs: list[CaseOutput]

    @model_validator(mode="after")
    def validate_run(self):
        ids = [output.case_id for output in self.outputs]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate case output")
        if self.arm == "llm_discovery" and not self.model:
            raise ValueError("LLM discovery requires a recorded model")
        return self


def score(corpus: Corpus, run: EvaluationRun) -> dict[str, object]:
    cases = {case.id: case for case in corpus.cases}
    outputs = {output.case_id: output for output in run.outputs}
    if set(outputs) - set(cases):
        raise ValueError("unknown benchmark case")
    records = {record.record_id: record for record in corpus.records}
    rows = []
    for identity, case in cases.items():
        output = outputs.get(identity)
        failed = output is None or output.error is not None
        ranked = [] if failed else output.evidence_ids[:10]
        required = set(case.required_ids)
        hits = len(required & set(ranked))
        # Validate ALL exposed IDs, not only the first ten used for ranking.
        exposed = [] if output is None else output.evidence_ids
        forbidden = set(case.forbidden_ids + case.excluded_ids)
        requester = case.requester_visibility
        for record in corpus.records:
            visible = (requester.role == "dm" or record.visibility == "party"
                       or (requester.role == "character"
                           and record.visibility == f"character:{requester.character_id}"))
            if not visible or record.state == "superseded":
                forbidden.add(record.record_id)
        paths = None if failed else output.paths
        returned_paths = {tuple(path) for path in paths or []}
        expected_paths = {tuple(path) for path in case.required_paths}
        forbidden_paths = {tuple(path) for path in case.forbidden_paths}
        all_paths = {tuple(path) for path in (output.paths or [])} if output else set()
        rows.append({
            "case_id": identity, "failed": failed,
            "latency_ms": output.latency_ms if output else None,
            "recall_at_10": hits / len(required) if required else None,
            "precision_at_10": hits / len(ranked) if ranked else None,
            "mode_correct": not failed and output.mode == case.expected_mode,
            "unknown_evidence_ids": sorted(set(exposed) - set(records)),
            "forbidden_evidence_ids": sorted(set(exposed) & forbidden),
            "required_path_recall": (len(returned_paths & expected_paths) / len(expected_paths)
                                     if expected_paths else None),
            "paths_supported": paths is not None,
            "forbidden_paths": sorted(all_paths & forbidden_paths),
            "forbidden_path_evidence_ids": sorted({
                node for path in all_paths for node in path if node in forbidden
            }),
            # Matching a gold path isn't proof every reported edge is grounded.
            "semantic_edge_grounding": "not_assessed",
        })
    return {
        "arm": run.arm, "backend_version": run.backend_version,
        "configuration_id": run.configuration_id, "model": run.model,
        "embedding_model": run.embedding_model, "cost_usd": run.cost_usd,
        "case_count": len(cases), "failed_cases": sum(row["failed"] for row in rows),
        "cases": rows,
        "limitations": "Gold-path matching only; semantic edge grounding needs separate review. "
                       "No backend adoption or safety certification is implied.",
    }


if __name__ == "__main__":
    run = EvaluationRun.model_validate_json(Path(sys.argv[1]).read_text(encoding="utf-8"))
    print(json.dumps(score(load(), run), indent=2))
