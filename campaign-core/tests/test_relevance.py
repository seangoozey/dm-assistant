import pytest
from pydantic import ValidationError

from dm_assistant_core.domain.relevance import PathEvidence, Purpose, Signals, score


def evidence(**changes):
    return PathEvidence(source_id="source", state="established", visible=True,
                        current=True, time_eligible=True, identity_resolved=True).model_copy(update=changes)


@pytest.mark.parametrize("field", ["visible", "current", "time_eligible", "identity_resolved"])
def test_ineligible_intermediate_cannot_be_rescued(field):
    result = score(Signals(semantic=1, evidence_support=1, feedback=1),
                   (evidence(), evidence(**{field: False})), Purpose.BRAINSTORM)
    assert result == {"version": "relevance-v1", "eligible": False}


def test_plans_remain_plans_and_suitability_depends_on_purpose():
    from dm_assistant_core.domain.models import ClaimState
    path = (evidence(), evidence(state=ClaimState.PREPARED))
    signals = Signals(semantic=.8, evidence_support=.9)
    factual = score(signals, path, Purpose.FACTUAL)
    planning = score(signals, path, Purpose.ENCOUNTER)
    assert factual["states"] == ["established", "prepared"]
    assert factual["components"]["truth_suitability"] == .25
    assert planning["score"] > factual["score"]
    assert factual["authority"] == "not_assigned_by_ranking"


def test_missing_feedback_is_neutral_and_repetition_is_capped():
    base = score(Signals(semantic=.5, evidence_support=.5), (evidence(),), Purpose.BRAINSTORM)
    assert base["components"]["feedback"] == .5
    assert "feedback" in base["missing"]
    a = Signals(semantic=.5, evidence_support=.5, independent_sources=3)
    b = a.model_copy(update={"independent_sources": 100})
    assert score(a, (evidence(),), Purpose.BRAINSTORM)["score"] == score(b, (evidence(),), Purpose.BRAINSTORM)["score"]


def test_semantic_relevance_beats_incidental_proximity():
    meaningful = Signals(semantic=.9, evidence_support=.9, path_strength=.6)
    incidental = Signals(semantic=.1, evidence_support=.9, path_strength=1, independent_sources=100)
    assert score(meaningful, (evidence(),), Purpose.BRAINSTORM)["score"] > score(incidental, (evidence(),), Purpose.BRAINSTORM)["score"]


@pytest.mark.parametrize("bad", [-.1, 1.1, float("nan"), float("inf")])
def test_invalid_scores_rejected(bad):
    with pytest.raises(ValidationError):
        Signals(semantic=bad, evidence_support=.5)
