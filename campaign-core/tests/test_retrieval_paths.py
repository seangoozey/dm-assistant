import pytest

from dm_assistant_core.domain.retrieval_paths import (
    CurrentLink,
    PathSuggestion,
    authorized_targets,
)
from tests.test_derived_retrieval import query, suggestion
from tests.test_evidence_comparison import record


def setup_path():
    records = tuple(record(i, visibility="party") for i in ("a", "b", "c", "proof"))
    a, b, c, proof = (suggestion(r) for r in records)
    links = (CurrentLink(edge_id="ab", from_id="a", to_id="b", evidence=(proof,)),
             CurrentLink(edge_id="bc", from_id="b", to_id="c", evidence=(proof,)))
    path = PathSuggestion(scope_id="party", generation="v1", nodes=(a, b, c),
                          edge_ids=("ab", "bc"))
    return records, links, path


def run(records, links, path):
    return authorized_targets(query("party"), (path,), records, links,
                              scope_id="party", generation="v1", seed_ids=frozenset({"a"}))


def test_current_two_hop_path_returns_only_target():
    records, links, path = setup_path()
    assert run(records, links, path) == (suggestion(records[2]),)


@pytest.mark.parametrize("index", [0, 1, 2, 3])
@pytest.mark.parametrize("change", [None, {"visibility": "dm"},
                                    {"state": "superseded"},
                                    {"evidence_binding": "changed"}])
def test_every_node_and_link_evidence_must_remain_current_and_visible(index, change):
    records, links, path = setup_path()
    changed = tuple(r.model_copy(update=change) if i == index else r
                    for i, r in enumerate(records)) if change else tuple(
                        r for i, r in enumerate(records) if i != index)
    assert run(changed, links, path) == ()


@pytest.mark.parametrize("change", [{"scope_id": "dm"}, {"generation": "old"},
                                    {"edge_ids": ("bc", "ab")}, {"edge_ids": ()}])
def test_scope_generation_direction_and_path_shape_fail_closed(change):
    records, links, path = setup_path()
    assert run(records, links, path.model_copy(update=change)) == ()


def test_missing_link_and_unseeded_path_fail_closed():
    records, links, path = setup_path()
    assert run(records, (), path) == ()
    assert run(records, links, path.model_copy(update={"nodes": path.nodes[1:],
                                                       "edge_ids": ("bc",)})) == ()


def test_cycle_fails_closed():
    records, links, path = setup_path()
    assert run(records, links, path.model_copy(update={
        "nodes": (path.nodes[0], path.nodes[1], path.nodes[0])})) == ()


def test_ambiguous_snapshot_rejected():
    records, links, path = setup_path()
    with pytest.raises(ValueError, match="ambiguous"):
        run((*records, records[0]), links, path)


def test_request_budget_rejected():
    records, links, path = setup_path()
    with pytest.raises(ValueError, match="100"):
        authorized_targets(query(), (path,) * 101, records, links,
                           scope_id="party", generation="v1", seed_ids=frozenset({"a"}))
