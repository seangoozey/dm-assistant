import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from weighted_manifest import (
    MANIFEST_VERSION,
    build_manifest,
    contributions,
    join_edge,
    normalize_name,
    rank_and_path,
    renormalize,
)

FIXTURE = Path(__file__).resolve().parents[2] / "tests/fixtures/relationship_relevance_cases_v2.json"
METADATA = {"doc-1": {"record_id": "command", "revision": "1", "state": "established",
                      "authority": "explicit_lore", "visibility": "dm_only"},
            "doc-2": {"record_id": "company", "revision": "1", "state": "established",
                      "authority": "explicit_lore", "visibility": "dm_only"},
            "doc-plan": {"record_id": "plan", "revision": "1", "state": "intended",
                         "authority": "explicit_lore", "visibility": "dm_only"}}


def graph(nodes, edges):
    return {"nodes": [{"id": i, "name": n, "type": t} for i, n, t in nodes],
            "edges": [{"source_node_id": s, "target_node_id": t,
                       "relationship_name": r, "description": d, "strength": k}
                      for s, t, r, d, k in edges]}


def test_contributions_map_extraction_to_evidence_with_states():
    result = contributions([
        {"document_id": "doc-1", "graph": graph(
            [("a", "Romulus", "Person"), ("b", "Inquisition", "Organization")],
            [("a", "b", "commands", "Romulus commands the Inquisition.", 1.0)])},
        {"document_id": "doc-plan", "graph": graph(
            [("c", "Regent", "Person"), ("d", "harbor", "Place")],
            [("c", "d", "intends to close", "Planned closure only.", 0.8)])},
    ], METADATA)
    assert [(c.source, c.target, c.evidence_id, c.state, c.strength) for c in result] == [
        ("romulus", "inquisition", "command", "established", 1.0),
        ("regent", "harbor", "plan", "intended", 0.8)]


def test_unknown_node_reference_is_skipped_like_cognee_conversion():
    result = contributions([{"document_id": "doc-1", "graph": graph(
        [("a", "Romulus", "Person")],
        [("a", "ghost", "commands", "Dangling reference.", 0.9)])}], METADATA)
    assert result == []


def test_strength_bounds_are_enforced():
    with pytest.raises(ValidationError):
        contributions([{"document_id": "doc-1", "graph": graph(
            [("a", "Romulus", "Person"), ("b", "Inquisition", "Organization")],
            [("a", "b", "commands", "Out of range.", 1.5)])}], METADATA)


def test_manifest_aggregates_without_inflating_copies_or_merging_states():
    manifest = build_manifest([
        {"document_id": "doc-1", "graph": graph(
            [("a", "Romulus", "Person"), ("b", "Inquisition", "Organization")],
            [("a", "b", "commands", "Romulus commands the Inquisition.", 1.0)])},
        # Same original evidence extracted twice: one unique contribution.
        {"document_id": "doc-1", "graph": graph(
            [("a", "Romulus", "Person"), ("b", "Inquisition", "Organization")],
            [("a", "b", "commands", "Romulus commands the Inquisition.", 1.0)])},
        # Distinct evidence for the same relationship: averaged, not summed.
        {"document_id": "doc-2", "graph": graph(
            [("a", "Romulus", "Person"), ("b", "Inquisition", "Organization")],
            [("a", "b", "commands", "Confirmed elsewhere.", 0.6)])},
    ], METADATA)
    assert manifest["version"] == MANIFEST_VERSION
    entry = manifest["entries"][0]
    assert entry["support_count"] == 2
    assert entry["strength"] == pytest.approx(0.8)
    assert {c["evidence_id"] for c in entry["contributions"]} == {"command", "company"}


def test_join_matches_either_direction_and_reports_reversal():
    manifest = build_manifest([{"document_id": "doc-1", "graph": graph(
        [("a", "Romulus", "Person"), ("b", "Inquisition", "Organization")],
        [("a", "b", "commands", "Romulus commands the Inquisition.", 0.9)])}], METADATA)
    entry, reversed_navigation = join_edge(manifest["entries"], "Inquisition", "Romulus")
    assert entry is not None and reversed_navigation is True
    assert join_edge(manifest["entries"], "Sorin", "Romulus") == (None, None)


def test_ranking_backed_before_fallback_and_paths_need_provenance():
    manifest = build_manifest([
        {"document_id": "doc-1", "graph": graph(
            [("a", "Romulus", "Person"), ("b", "Inquisition", "Organization")],
            [("a", "b", "commands", "Romulus commands the Inquisition.", 1.0)])},
        {"document_id": "doc-2", "graph": graph(
            [("a", "Sorin", "Person"), ("b", "Eustice's company", "Organization")],
            [("a", "b", "served in", "Sorin served in the company.", 0.6)])},
    ], METADATA)
    returned = [
        {"left": "n1", "right": "n2", "left_name": "Sorin", "right_name": "Eustice's company"},
        {"left": "n3", "right": "n4", "left_name": "Silver Helms", "right_name": "Kade"},
        {"left": "n5", "right": "n6", "left_name": "Romulus", "right_name": "Inquisition"},
    ]
    rankings, paths, details = rank_and_path(
        manifest, returned, lambda left, right: {"rooms"} if {left, right} == {"n3", "n4"} else set())
    assert rankings == ["command", "company", "rooms"]
    assert paths == [["company"], ["command"]]
    assert [d["manifest_matched"] for d in details] == [True, False, True]
    assert details[1]["records"] == ["rooms"]


def test_absent_bridge_pair_never_becomes_a_path_claim():
    corpus = json.loads(FIXTURE.read_text(encoding="utf-8"))
    captures = [{"document_id": f"doc-{r['id']}", "graph": graph(
        [(r["id"], r["entities"][0], "Entity"), (r["id"] + "x", r["entities"][-1], "Entity")],
        [(r["id"], r["id"] + "x", "relates to", "Synthetic.", 0.9)])} for r in corpus["records"]]
    metadata = {f"doc-{r['id']}": {"record_id": r["id"], "revision": "1", "state": "established",
                                   "authority": "explicit_lore", "visibility": "dm_only"}
                for r in corpus["records"]}
    manifest = build_manifest(captures, metadata)
    forbidden = {tuple(sorted(pair)) for case in corpus["cases"]
                 for pair in case.get("absent_bridges", [])}
    for left, right in forbidden:
        entry, _ = join_edge(manifest["entries"], left, right)
        assert entry is None, (left, right)


def test_normalize_name_is_stable():
    assert normalize_name("  Captain   Vale's Warden patrol ") == "captain vales warden patrol"
    assert normalize_name("The Inquisition") == "inquisition"
    assert normalize_name("the regent") == "regent"


def test_renormalize_rekeys_saved_manifest_without_provider_calls():
    legacy = {"version": MANIFEST_VERSION,
              "notes": "kept",
              "entries": [{"source": "The Regent", "target": "the harbor",
                           "relation": "intends to close", "state": "intended",
                           "authority": "explicit_lore", "negated": False,
                           "time_scope": "present", "visibility": "dm_only",
                           "attribution": "", "strength": 1.0, "support_count": 1,
                           "contributions": [{"evidence_id": "plan", "revision": "1",
                                              "strength": 1.0,
                                              "description": "Planned closure only."}]}]}
    rebuilt = renormalize(legacy)
    assert rebuilt["notes"] == "kept"
    entry, reversed_navigation = join_edge(rebuilt["entries"], "regent", "harbor")
    assert entry is not None and reversed_navigation is False
    assert entry["state"] == "intended" and entry["support_count"] == 1
