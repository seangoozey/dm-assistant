import pytest
from pydantic import ValidationError

from tests.support.connected_knowledge_harness import load
from tests.support.knowledge_evaluation import EvaluationRun, score


def run(outputs):
    return EvaluationRun(arm="lexical", backend_version="test", configuration_id="test",
                         outputs=outputs)


def test_missing_runs_are_failures_not_successes():
    report = score(load(), run([]))
    assert report["failed_cases"] == 24
    assert all(not row["mode_correct"] for row in report["cases"])


def test_duplicates_and_unknown_cases_are_rejected():
    case = load().cases[0].id
    with pytest.raises(ValidationError):
        run([{"case_id": case, "evidence_ids": ["command", "command"]}])
    with pytest.raises(ValidationError):
        run([{"case_id": case}, {"case_id": case}])
    with pytest.raises(ValueError, match="unknown benchmark"):
        score(load(), run([{"case_id": "unknown"}]))


def test_ranking_counts_exact_hits_and_flags_unknown_evidence():
    case = load().cases[0]
    report = score(load(), run([{
        "case_id": case.id, "evidence_ids": ["command", "invented"], "mode": "answer",
    }]))
    first = report["cases"][0]
    assert first["recall_at_10"] == 0.5
    assert first["precision_at_10"] == 0.5
    assert first["unknown_evidence_ids"] == ["invented"]
    assert first["semantic_edge_grounding"] == "not_assessed"


def test_hidden_evidence_beyond_top_ten_is_still_flagged():
    corpus = load()
    case = next(case for case in corpus.cases if case.id == "security-hidden")
    ids = [record.record_id for record in corpus.records if record.record_id != "hidden"][:10]
    report = score(corpus, run([{"case_id": case.id, "evidence_ids": [*ids, "hidden"]}]))
    row = next(row for row in report["cases"] if row["case_id"] == case.id)
    assert "hidden" in row["forbidden_evidence_ids"]


def test_llm_run_must_record_model_and_cost_is_unknown_unless_supplied():
    with pytest.raises(ValidationError):
        EvaluationRun(arm="llm_discovery", backend_version="test", configuration_id="test",
                      outputs=[])
    assert run([]).cost_usd is None
