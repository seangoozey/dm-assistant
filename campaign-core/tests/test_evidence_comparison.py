from itertools import product

import pytest

from dm_assistant_core.domain.evidence_comparison import (
    ComparisonCoordinate,
    compare_evidence,
)
from dm_assistant_core.domain.retrieval import RequesterVisibility, RetrievalRecord

DM = RequesterVisibility(role="dm")


def record(identity="a", **updates):
    values = dict(record_id=identity, kind="claim", assertion="An intact sourced assertion.",
                  state="established", authority="explicit_lore", visibility="party",
                  source_id=f"source-{identity}", citation=f"fixture/{identity}", accepted=True,
                  entity_id="person")
    return RetrievalRecord(**(values | updates))


def coordinate(identity="a", **updates):
    values = dict(record_id=identity, subject_id="person", property_key="location",
                  value_key=identity, scope_key="same-instant", exclusive=True)
    return ComparisonCoordinate(**(values | updates))


def compare(**updates):
    values = dict(left=record(), right=record("b"), requester=DM,
                  left_coordinate=coordinate(), right_coordinate=coordinate("b"))
    return compare_evidence(**(values | updates))


def test_explicit_conflict_and_retcon():
    assert compare().status == "conflict"
    assert compare(right=record("b", state="observed", authority="real_play")).status == (
        "possible_retcon"
    )


@pytest.mark.parametrize("updates", [
    {"property_key": "cloak_color"}, {"scope_key": "next-day"}, {"exclusive": False},
])
def test_different_property_time_or_nonexclusive_values_are_unknown(updates):
    assert compare(right_coordinate=coordinate("b", **updates)).status == "unknown"


def test_unstructured_prose_is_never_verified_conflict():
    assert compare(left_coordinate=None, right_coordinate=None).status == "unknown"
    assert compare(right=record("b", state="observed", authority="real_play"),
                   left_coordinate=None).status == "unknown"


def test_coordinate_equivalence_is_not_whole_claim_equivalence():
    result = compare(right_coordinate=coordinate("b", value_key="a"))
    assert result.status == "equivalent"
    assert result.reason == "same_scoped_property_value"


@pytest.mark.parametrize("state,authority", [
    ("intended", "npc_intention"), ("possible", "brainstorm"),
    ("prepared", "preparation"), ("superseded", "explicit_lore"),
])
def test_plans_and_stale_records_never_prove_conflict(state, authority):
    assert compare(right=record("b", state=state, authority=authority)).status == "unknown"


def test_hidden_evidence_is_indistinguishable_from_unknown():
    expected = compare(left_coordinate=None)
    for role, side in product(("party", "character"), ("left", "right")):
        requester = RequesterVisibility(
            role=role, character_id="pc" if role == "character" else None
        )
        updates = {side: record("a" if side == "left" else "b", visibility="dm")}
        assert compare(requester=requester, **updates) == expected


def test_identity_bindings_cannot_drift():
    with pytest.raises(ValueError, match="exact evidence"):
        compare(right_coordinate=coordinate("wrong"))
    with pytest.raises(ValueError, match="recorded subject"):
        compare(right_coordinate=coordinate("b", subject_id="other"))


def test_order_is_deterministic_and_same_record_is_not_a_pair():
    assert compare() == compare(left=record("b"), right=record(),
                                left_coordinate=coordinate("b"), right_coordinate=coordinate())
    assert compare(right=record(), right_coordinate=coordinate()).status == "unknown"


def test_other_subject_and_unaccepted_evidence_cannot_prove_conflict():
    assert compare(right=record("b", entity_id="other"),
                   right_coordinate=coordinate("b", subject_id="other")).status == "unknown"
    assert compare(right=record("b", accepted=False)).status == "unknown"
