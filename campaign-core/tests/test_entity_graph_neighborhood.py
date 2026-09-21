"""Entity graph neighborhood gather (TKT-0120 expansion layer)."""

from dm_assistant_core.application.entity_graph_neighborhood import (
    EntityGraphNeighborhoodService,
    graph_neighborhood,
)

BUNDLE = {
    "graph": [
        [
            ("fleur", {"type": "Entity", "name": "Fleurite", "entity_type": "location"}),
            ("exiles", {"type": "Entity", "name": "Fleurite Exiles", "entity_type": "faction"}),
            ("jace", {"type": "Entity", "name": "Jace Valamacke", "entity_type": "npc"}),
            ("lily", {"type": "Entity", "name": "Lily Valamacke", "entity_type": "npc"}),
            ("ruh", {"type": "Entity", "name": "Ruh", "entity_type": "npc"}),
            ("peter", {"type": "Entity", "name": "Peter le Fleur", "entity_type": "npc"}),
            ("chunk", {"type": "DocumentChunk", "name": None, "document_id": "d1"}),
        ],
        [
            ("jace", "exiles", "leader_of", {}),
            ("jace", "exiles", "member_of", {}),
            ("lily", "exiles", "member_of", {}),
            ("fleur", "peter", "co_mention", {}),
            ("fleur", "peter", "co_mention", {}),
            ("fleur", "ruh", "co_mention", {}),
            ("fleur", "chunk", "contains", {}),
        ],
    ],
}


def test_seats_first_then_ranked_co_mentions() -> None:
    rows = graph_neighborhood(BUNDLE, "Fleurite")
    texts = [row.text for row in rows]
    # A location belongs to no faction, so no audited seats qualify — only
    # its co-mention partners, ranked by shared-document count.
    assert texts == [
        "Frequently appears with Peter le Fleur (2 shared documents)",
        "Frequently appears with Ruh (1 shared documents)",
    ]
    assert all(row.backing == "derived co-mention association" for row in rows)
    assert all(row.key.startswith("graph:") for row in rows)


def test_faction_member_sees_sibling_seats_one_hop_out() -> None:
    bundle = {
        "graph": [
            BUNDLE["graph"][0],
            [
                ("jace", "exiles", "leader_of", {"role": "Leader of the Rebellion"}),
                ("lily", "exiles", "member_of", {}),
                ("jace", "exiles", "member_of", {}),
            ],
        ],
    }
    rows = graph_neighborhood(bundle, "Jace Valamacke")
    assert [row.text for row in rows] == [
        "Jace Valamacke leads Fleurite Exiles as Leader of the Rebellion",
        "Jace Valamacke is a member of Fleurite Exiles",
        "Lily Valamacke is a member of Fleurite Exiles",
    ]
    backings = [row.backing for row in rows]
    assert backings[0].startswith("audited leadership seat")
    assert backings[2].startswith("audited membership")


def test_faction_seed_reads_its_own_roster() -> None:
    rows = graph_neighborhood(BUNDLE, "Fleurite Exiles")
    assert [row.text for row in rows] == [
        "Jace Valamacke leads Fleurite Exiles",
        "Jace Valamacke is a member of Fleurite Exiles",
        "Lily Valamacke is a member of Fleurite Exiles",
    ]
    assert all("audited" in row.backing for row in rows)


def test_unknown_entity_yields_no_rows() -> None:
    assert graph_neighborhood(BUNDLE, "Nowhere") == []


def test_service_reads_bundle_from_disk(tmp_path) -> None:
    import json as jsonlib

    path = tmp_path / "bundle.json"
    path.write_text(jsonlib.dumps(BUNDLE), encoding="utf-8")

    class Names:
        def get(self, entity_id):
            return type("Entity", (), {"canonical_name": "Fleurite"})() if entity_id == "e1" else None

    service = EntityGraphNeighborhoodService(str(path), Names())
    rows = service.neighborhood("e1")
    assert rows and rows[0].text.startswith("Frequently appears with Peter le Fleur")
    assert service.neighborhood("missing") == []
