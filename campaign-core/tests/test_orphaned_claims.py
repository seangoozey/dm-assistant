"""Orphaned-claims review list contract (TKT-0138 slice 1)."""

from uuid import UUID

from dm_assistant_core.application.orphaned_claims import OrphanedClaimsService

RUFUS = UUID("aa000000-0000-0000-0000-000000000001")
ROMULUS = UUID("aa000000-0000-0000-0000-000000000002")
ARKIN = UUID("aa000000-0000-0000-0000-000000000003")
RAVEN = UUID("aa000000-0000-0000-0000-000000000004")
ART = UUID("aa000000-0000-0000-0000-000000000005")
ZANDER = UUID("aa000000-0000-0000-0000-000000000006")
CLAIM_A = UUID("cc000000-0000-0000-0000-000000000001")
CLAIM_B = UUID("cc000000-0000-0000-0000-000000000002")


class FakeRepository:
    def __init__(self, orphans, related=(), names=(), aliases=(), documents=()):
        self._orphans = orphans
        self._related = related
        self._names = names
        self._aliases = aliases
        self._documents = documents

    def orphaned_claims(self):
        return self._orphans

    def related_entities(self):
        return self._related

    def entity_names(self):
        return self._names

    def entity_aliases(self):
        return self._aliases

    def document_paths(self):
        return self._documents


def test_co_mentions_outrank_name_matches_and_cap_at_three():
    orphans = [
        (CLAIM_A, "Romulus rages at Rufus in the Ravenholdt keep.", "observed",
         "real_play", "505-10-20", ["sessions/note.md"]),
    ]
    related = [
        # Co-mention says Romulus AND Arkin — both outrank text matches.
        (CLAIM_A, ROMULUS, "Romulus", "npc"),
        (CLAIM_A, ARKIN, "Arkin", "npc"),
    ]
    names = [
        (RUFUS, "Rufus", "npc"),
        (ROMULUS, "Romulus", "npc"),
        (RAVEN, "Ravenholdt", "location"),
        (ARKIN, "Arkin", "npc"),
    ]
    result = OrphanedClaimsService(FakeRepository(orphans, related, names)).gather()
    assert result.total_claims == 1 and result.claims_with_suggestions == 1
    suggestions = result.claims[0].suggestions
    assert [(s.entity_name, s.basis) for s in suggestions] == [
        ("Romulus", "co-mention"), ("Arkin", "co-mention"), ("Ravenholdt", "name in text"),
    ]
    # Rufus is in the text but the cap excludes the fourth candidate.


def test_word_boundaries_prevent_substring_false_positives():
    orphans = [
        (CLAIM_B, "The artisan made a blade.", "established", "explicit_lore", None, []),
    ]
    names = [(ART, "Art", "npc")]  # must NOT match "artisan"
    result = OrphanedClaimsService(FakeRepository(orphans, names=names)).gather()
    assert result.claims[0].suggestions == ()
    assert result.claims_with_suggestions == 0


def test_apostrophe_names_match_on_their_own_boundaries():
    orphans = [
        (CLAIM_A, "Ishi'ra'la watches the gate.", "observed", "real_play", None, []),
    ]
    aliases = [("Ishi'ra'la", ARKIN, "Arkin", "npc")]
    result = OrphanedClaimsService(
        FakeRepository(orphans, names=[(ARKIN, "Arkin", "npc")], aliases=aliases)
    ).gather()
    # The alias displays the entity's canonical name; the basis is the match.
    assert result.claims[0].suggestions[0].entity_name == "Arkin"
    assert result.claims[0].suggestions[0].basis == "name in text"


def test_actionable_first_sort_and_source_paths_carry():
    orphans = [
        (CLAIM_A, "Zzz the claim nobody suggests for.", "established", "explicit_lore", None, ["lore/a.md", "lore/b.md", "lore/c.md", "lore/d.md"]),
        (CLAIM_B, "Aaa the claim with a home.", "observed", "real_play", "505-11-01", ["sessions/n.md"]),
    ]
    related = [(CLAIM_B, ROMULUS, "Romulus", "npc")]
    result = OrphanedClaimsService(FakeRepository(orphans, related)).gather()
    assert [c.claim_id for c in result.claims] == [CLAIM_B, CLAIM_A]
    assert result.claims[0].source_paths == ("sessions/n.md",)
    assert len(result.claims[1].source_paths) == 3  # capped in the adapter; honored here

def test_document_owner_is_the_default_disposition():
    docs = [(UUID("dd000000-0000-0000-0000-000000000001"), "npcs/zander-thromius.md")]
    names = [(ZANDER, "Zander Thromius", "pc")]
    orphans = [
        (CLAIM_A, "A strange tattoo appeared.", "established", "explicit_lore", None, ["npcs/zander-thromius.md"]),
    ]
    result = OrphanedClaimsService(FakeRepository(orphans, names=names, documents=docs)).gather()
    assert result.claims[0].document_owner_id == ZANDER
    assert result.claims[0].document_owner_name == "Zander Thromius"
    # Document-backed rows sort first (the mechanical drain).
    result2 = OrphanedClaimsService(FakeRepository(
        orphans + [(CLAIM_B, "zzz no attachment anywhere.", "observed", "real_play", None, ["sessions/notes/x"])],
        names=names, documents=docs,
    )).gather()
    assert result2.claims[0].claim_id == CLAIM_A
    assert result2.claims[1].document_owner_id is None

def test_encounter_groups_ready_to_mint():
    orphans = [
        (CLAIM_A, "Perch guard rotation.", "established", "explicit_lore", None, ["encounters/Ishirala/ishirala-perch.md"]),
        (CLAIM_B, "Floor three crystal forest.", "established", "explicit_lore", None, ["encounters/Ishirala/ishirala-floor3.md"]),
        (UUID("cc000000-0000-0000-0000-0000000000c3"), "The descent begins.", "established", "explicit_lore", None, ["encounters/the-descent.md"]),
        (UUID("cc000000-0000-0000-0000-0000000000c4"), "A session observation.", "observed", "real_play", None, ["sessions/notes/x"]),
    ]
    result = OrphanedClaimsService(FakeRepository(orphans)).gather()
    groups = result.encounter_groups
    # One encounter PER DOCUMENT (2026-10-02 ruling): the Ishirala directory
    # is a GROUP of encounters — one per floor — not a single encounter.
    assert {g.name: len(g.claim_ids) for g in groups} == {
        "Ishirala Perch": 1, "Ishirala Floor 3": 1, "The Descent": 1,
    }
    # Session claims never group; page-backed claims never group.
    assert all("sessions" not in path for g in groups for path in g.document_paths)

def test_encounter_group_names_flag_identity_collisions():
    orphans = [
        (CLAIM_A, "Perch guard rotation.", "established", "explicit_lore", None, ["encounters/Ishirala/ishirala-perch.md"]),
        (CLAIM_B, "The descent begins.", "established", "explicit_lore", None, ["encounters/the-descent.md"]),
    ]
    names = [(UUID("aa000000-0000-0000-0000-000000000007"), "Ishirala Perch", "encounter")]
    result = OrphanedClaimsService(FakeRepository(orphans, names=names)).gather()
    by_name = {g.name: g for g in result.encounter_groups}
    assert by_name["Ishirala Perch"].name_available is False
    assert by_name["The Descent"].name_available is True

