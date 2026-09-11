"""Repair-ready conflict exposure is separate from legacy answer-mode compatibility."""

import pytest
from pydantic import ValidationError

from dm_assistant_core.domain.evidence_comparison import retrieval_conflicts
from dm_assistant_core.domain.retrieval import RetrievalPolicy, RetrievalQuery
from tests.test_evidence_comparison import DM, coordinate, record


def test_verified_conflict_has_both_assertions_and_repair_identity():
    query = RetrievalQuery(question="Where is the person?", requester_visibility=DM)
    result = RetrievalPolicy().evaluate(
        query, (record(), record("b")),
        comparison_coordinates=(coordinate(), coordinate("b")),
    )
    issue, = result.conflicts
    assert issue.classification == "factual_conflict"
    assert issue.verification == "verified_comparison"
    assert issue.requires_review
    assert issue.subject_id == "person"
    assert issue.property_key == "location"
    assert issue.scope_key == "same-instant"
    assert [item.record_id for item in issue.evidence] == ["a", "b"]
    assert [item.citation for item in issue.evidence] == ["fixture/a", "fixture/b"]
    assert all(item.assertion for item in issue.evidence)
    assert result.comparison_coverage == "partial"
    assert not result.conflicts_truncated


def test_issue_identity_is_stable_but_changes_when_evidence_changes():
    query = RetrievalQuery(question="Where?", requester_visibility=DM)
    first, _ = retrieval_conflicts(query, (record(), record("b")),
                                  (coordinate(), coordinate("b")))
    reversed_result, _ = retrieval_conflicts(query, (record("b"), record()),
                                            (coordinate("b"), coordinate()))
    changed, _ = retrieval_conflicts(
        query, (record(assertion="A corrected assertion."), record("b")),
        (coordinate(), coordinate("b")),
    )
    assert first == reversed_result
    assert first[0].issue_id != changed[0].issue_id


def test_hidden_conflicts_do_not_expose_issue_counts_or_scope():
    query = RetrievalQuery(question="Where?", requester_visibility={"role": "party"})
    assert retrieval_conflicts(query, (record(visibility="dm"), record("b")),
                               (coordinate(), coordinate("b"))) == ((), False)


def test_legacy_alert_is_explicitly_unverified():
    result = RetrievalPolicy().evaluate(
        RetrievalQuery(question="Tell me about this person", requester_visibility=DM),
        (record(), record("b", assertion="This person wears a blue cloak.")),
    )
    issue, = result.conflicts
    assert issue.verification == "unverified"
    assert issue.classification == "suspected_conflict"
    assert issue.reason == "legacy_alert_requires_explicit_comparison"


def test_clients_cannot_submit_verified_coordinates():
    with pytest.raises(ValidationError):
        RetrievalQuery.model_validate({
            "question": "Where?", "requester_visibility": {"role": "dm"},
            "comparison_coordinates": [coordinate().model_dump()],
        })


def test_conflict_limit_is_explicit():
    records = tuple(record(str(index)) for index in range(12))
    coordinates = tuple(coordinate(str(index)) for index in range(12))
    issues, truncated = retrieval_conflicts(
        RetrievalQuery(question="Where?", requester_visibility=DM), records, coordinates,
    )
    assert len(issues) == 50
    assert truncated
