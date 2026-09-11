import pytest
from pydantic import ValidationError

from dm_assistant_core.domain.derived_retrieval import (
    IndexSuggestion,
    evaluate_suggestions,
    record_fingerprint,
)
from dm_assistant_core.domain.retrieval import RetrievalQuery
from tests.test_evidence_comparison import DM, coordinate, record


def suggestion(r):
    return IndexSuggestion(record_id=r.record_id, fingerprint=record_fingerprint(r))


def query(role="dm"):
    return RetrievalQuery(question="Where is this person?", requester_visibility={"role": role})


def test_compatible_claims_are_context_not_conflict_or_answer():
    a, b = record(), record("b", assertion="The person wears a cloak.")
    result = evaluate_suggestions(query(), (suggestion(a), suggestion(b)), (a, b))
    assert result.answer_mode == "insufficient_evidence"
    assert not result.conflicts
    assert all(e.role == "context" for e in result.evidence)


@pytest.mark.parametrize("change", [{"assertion": "Corrected"}, {"source_id": "new-source"},
                                    {"evidence_binding": "new-revision-or-span"},
                                    {"state": "superseded"}, {"visibility": "character:other"}])
def test_stale_snapshot_cannot_supply_evidence(change):
    original = record()
    updated = original.model_copy(update=change)
    assert not evaluate_suggestions(query(), (suggestion(original),), (updated,)).evidence


def test_hidden_and_absent_are_indistinguishable():
    hidden = record(visibility="dm")
    hints = (suggestion(hidden),)
    assert evaluate_suggestions(query("party"), hints, (hidden,)) == evaluate_suggestions(
        query("party"), hints, ())


def test_verified_conflict_excludes_unrelated_claim_from_conflict_role():
    a, b, c = record(), record("b"), record("c")
    result = evaluate_suggestions(
        RetrievalQuery(question="Where?", requester_visibility=DM),
        tuple(suggestion(r) for r in (a, b, c)), (a, b, c),
        comparison_coordinates=(coordinate(), coordinate("b")))
    assert result.answer_mode == "conflict"
    assert len(result.conflicts) == 1
    assert [e.role for e in result.evidence] == ["conflict", "conflict", "context"]


def test_index_cannot_supply_text_or_comparison_proof():
    with pytest.raises(ValidationError):
        IndexSuggestion.model_validate({
            **suggestion(record()).model_dump(), "assertion": "invented"})


def test_duplicate_suggestions_do_not_duplicate_evidence():
    r = record()
    assert len(evaluate_suggestions(query(), (suggestion(r), suggestion(r)), (r,)).evidence) == 1
