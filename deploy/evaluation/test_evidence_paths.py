import pytest

from evidence_paths import Evidence, Link, discover


def link(identity, source, target, **changes):
    evidence = Evidence(id=identity, revision="1", state="established", authority="explicit_lore",
                        visibility="dm_only", current=True, time_eligible=True)
    return Link(id=identity, source=source, target=target, relation="member_of", kind="suggested",
                evidence=(evidence,), identities_resolved=True).model_copy(update=changes)


def walk(links, **changes):
    args = dict(allowed_visibility={"dm_only"}, current_revisions={x.id: "1" for x in links})
    return discover("a", links, **(args | changes))


def test_two_steps_have_independent_evidence_and_keep_inverse_direction():
    result = walk([link("1", "a", "b"), link("2", "c", "b")])
    path = next(p for p in result["paths"] if p["target"] == "c")
    assert [s["evidence"][0]["id"] for s in path["steps"]] == ["1", "2"]
    assert path["steps"][1]["source"] == "c"
    assert path["steps"][1]["reverse_navigation"]
    assert path["meaning"] == "retrieval_path_not_transitive_fact"


@pytest.mark.parametrize("change", [dict(visibility="secret"), dict(current=False),
    dict(time_eligible=False), dict(state="superseded"), dict(revision="old")])
def test_ineligible_intermediate_leaks_neither_endpoint_nor_counts(change):
    first = link("1", "a", "b")
    first = first.model_copy(update={"evidence": (first.evidence[0].model_copy(update=change),)})
    assert walk([first, link("2", "b", "c")]) == {"paths": [], "truncated": False}


def test_absent_bridge_and_structural_links_cannot_supply_semantic_paths():
    assert walk([link("1", "a", "type", kind="structural"), link("2", "type", "c")])["paths"] == []
    assert walk([link("2", "b", "c")])["paths"] == []


def test_cycles_budgets_and_fanout_are_bounded():
    links = [link("1", "a", "b"), link("2", "b", "c"), link("3", "c", "a")]
    result = walk(links, budget=2)
    assert len(result["paths"]) == 2 and result["truncated"]
    assert all(p["target"] != "a" for p in walk(links)["paths"])
    assert walk(links, fanout=1)["truncated"]


def test_mixed_state_path_does_not_promote_plan():
    plan = link("2", "b", "c")
    plan = plan.model_copy(update={"evidence": (plan.evidence[0].model_copy(update={"state": "intended"}),)})
    result = walk([link("1", "a", "b"), plan])
    assert result["paths"][-1]["steps"][-1]["evidence"][0]["state"] == "intended"
    assert "state" not in result["paths"][-1]


def test_unresolved_identity_and_missing_revision_fail_closed():
    assert walk([link("1", "a", "b", identities_resolved=False)])["paths"] == []
    assert walk([link("1", "a", "b")], current_revisions={})["paths"] == []
