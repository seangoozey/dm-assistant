import pytest

from dm_assistant_core.domain.projection_build import validate_manifest
from dm_assistant_core.domain.retrieval_paths import CurrentLink
from tests.test_derived_retrieval import query, suggestion
from tests.test_evidence_comparison import record


def test_manifest_stable_order_and_revision_sensitive():
    a, b = (record(i, evidence_binding="bound") for i in ("a", "b"))
    digest = validate_manifest(query(), (a, b), ())
    assert digest == validate_manifest(query(), (b, a), ())
    assert digest != validate_manifest(query(), (a.model_copy(
        update={"evidence_binding": "new"}), b), ())


@pytest.mark.parametrize("change", [{"visibility": "dm"}, {"accepted": False},
                                    {"state": "superseded"}, {"evidence_binding": None}])
def test_invalid_node_rejects_entire_build(change):
    original = record(evidence_binding="bound")
    r = type(original).model_validate({**original.model_dump(), **change})
    with pytest.raises(ValueError):
        validate_manifest(query("party"), (r,), ())


def test_dangling_and_stale_link_rejected():
    a, b = (record(i, evidence_binding="bound") for i in ("a", "b"))
    edge = CurrentLink(edge_id="ab", from_id="a", to_id="b", evidence=(suggestion(a),))
    with pytest.raises(ValueError):
        validate_manifest(query(), (a,), (edge,))
    with pytest.raises(ValueError):
        validate_manifest(query(), (a.model_copy(update={"evidence_binding": "new"}), b), (edge,))
