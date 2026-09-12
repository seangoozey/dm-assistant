import pytest

from manifest_traversal import entity_tokens, manifest_links, resolve, seed_entities, walk
from weighted_manifest import build_manifest

CORPUS = {"records": [
    {"id": "regent", "text": "The Regent commands the Wardens.",
     "entities": ["Regent", "Wardens"]},
    {"id": "warden-bridge", "text": "Captain Vale's Warden patrol is part of the Wardens.",
     "entities": ["Vale", "Vale's Warden patrol", "Wardens"]},
    {"id": "warden", "text": "Mira belonged to Captain Vale's Warden patrol.",
     "entities": ["Mira", "Vale", "Vale's Warden patrol"]},
    {"id": "eustice-co", "text": "Sorin served in Eustice's company.",
     "entities": ["Sorin", "Eustice", "Eustice's company"]},
    {"id": "ossler-co", "text": "Kade served in Ossler's company.",
     "entities": ["Kade", "Ossler", "Ossler's company"]},
]}
METADATA = {f"doc-{r['id']}": {"record_id": r["id"], "revision": "1", "state": "established",
                               "authority": "explicit_lore", "visibility": "dm_only"}
             for r in CORPUS["records"]}


def graph(nodes, edges):
    return {"nodes": [{"id": str(i), "name": n, "type": "Entity"} for i, n in enumerate(nodes)],
            "edges": [{"source_node_id": str(s), "target_node_id": str(t),
                       "relationship_name": r, "description": d, "strength": k}
                      for s, t, r, d, k in edges]}


def links_for(captures):
    return manifest_links(build_manifest(captures, METADATA), CORPUS)


def test_resolution_requires_a_unique_token_match():
    tokens = entity_tokens(CORPUS)
    assert resolve(tokens, "romulus") is None
    assert resolve(tokens, "The Regent") == "regent"
    assert resolve(tokens, "captain vales warden patrol") == "vales warden patrol"
    # Generic endpoint matches both companies: ambiguous, never merged.
    assert resolve(tokens, "company") is None
    assert resolve(tokens, "inquisitor eustices company") == "eustices company"


def test_ambiguous_and_negated_edges_are_excluded_not_merged():
    negated_metadata = dict(METADATA, **{"doc-eustice-co": dict(
        METADATA["doc-eustice-co"], negated=True)})
    manifest = build_manifest([
        {"document_id": "doc-eustice-co", "graph": graph(
            ["Regent", "Wardens"], [(0, 1, "commands", "Negated command.", 1.0)])},
    ], negated_metadata)
    links, unresolved, _ = manifest_links(manifest, CORPUS)
    assert links == [] and unresolved == []

    links, unresolved, _ = links_for([
        {"document_id": "doc-eustice-co", "graph": graph(
            ["Sorin", "Eustice's company"], [(0, 1, "served in", "Sorin served.", 1.0)])},
        {"document_id": "doc-ossler-co", "graph": graph(
            ["Kade", "company"], [(0, 1, "served in", "Kade served.", 1.0)])},
    ])
    # The specifically named company resolves; the generic endpoint stays ambiguous.
    assert [(l.source, l.target) for l in links] == [("sorin", "eustices company")]
    assert {tuple(u["records"]) for u in unresolved} == {("ossler-co",)}


def test_chain_is_covered_by_one_walk_with_stepwise_evidence():
    links, unresolved, revisions = links_for([
        {"document_id": "doc-regent", "graph": graph(
            ["Regent", "Wardens"], [(0, 1, "commands", "Commands.", 1.0)])},
        {"document_id": "doc-warden-bridge", "graph": graph(
            ["Captain Vale's Warden patrol", "Wardens"], [(0, 1, "part of", "Part of.", 1.0)])},
        {"document_id": "doc-warden", "graph": graph(
            ["Mira", "Captain Vale's Warden patrol"], [(0, 1, "belonged to", "Belonged.", 1.0)])},
    ])
    assert unresolved == []
    result = walk("Who served under the Regent's officers?", links, entity_tokens(CORPUS),
                  revisions)
    assert result["seeds"] == ["regent"]
    covering = [w for w in result["walks"]
                if set(w["records"]) == {"regent", "warden-bridge", "warden"}]
    assert covering, result["walks"]
    steps = covering[0]["steps"]
    assert [s["relation"] for s in steps] == ["commands", "part of", "belonged to"]
    assert all(s["kind"] == "suggested" for s in steps)
    assert result["meaning"] == "retrieval_path_not_transitive_fact"


def test_stale_revision_blocks_the_walk():
    captures = [
        {"document_id": "doc-regent", "graph": graph(
            ["Regent", "Wardens"], [(0, 1, "commands", "Commands.", 1.0)])},
        {"document_id": "doc-warden-bridge", "graph": graph(
            ["Captain Vale's Warden patrol", "Wardens"], [(0, 1, "part of", "Part of.", 1.0)])},
    ]
    links, _, revisions = links_for(captures)
    stale = dict(revisions)
    stale["warden-bridge"] = "2"
    result = walk("Regent's officers", links, entity_tokens(CORPUS), stale)
    assert all("warden-bridge" not in w["records"] for w in result["walks"])


def test_seeds_need_a_declared_token_in_the_question():
    tokens = entity_tokens(CORPUS)
    assert seed_entities("Romulus's organization", tokens) == []
    assert seed_entities("The Regent plans", tokens) == ["regent"]
    assert seed_entities("What about Ossler's company?", tokens) == ["ossler", "osslers company"]
