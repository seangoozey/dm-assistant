from __future__ import annotations

import os
from hashlib import sha256
from uuid import uuid4

import psycopg
import pytest

from dm_assistant_core.adapters.postgres.database import PostgresDatabase
from dm_assistant_core.adapters.postgres.identity_gaps import PostgresIdentityQueueRepository
from dm_assistant_core.adapters.postgres.migrate import run_migrations
from dm_assistant_core.application.identity_gaps import (
    AddAliasDecision,
    CreateEntityDecision,
    IdentityQueueError,
    SurfaceDecision,
)

TEST_DSN = os.getenv("CAMPAIGN_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    TEST_DSN is None,
    reason="set CAMPAIGN_TEST_DATABASE_URL to a disposable PostgreSQL database",
)


@pytest.fixture(autouse=True)
def disposable_database() -> None:
    if TEST_DSN is None:
        return
    database_name = psycopg.conninfo.conninfo_to_dict(TEST_DSN).get("dbname", "")
    if not database_name.endswith("_test"):
        raise RuntimeError("integration tests require a database name ending in _test")
    run_migrations(TEST_DSN)
    with psycopg.connect(TEST_DSN) as connection:
        connection.execute(
            "TRUNCATE TABLE import_runs, source_documents, workflow_sessions, change_sets CASCADE"
        )


def seed_entity(name: str) -> tuple:
    entity_id, workflow_id, change_set_id = uuid4(), uuid4(), uuid4()
    with psycopg.connect(TEST_DSN) as connection:
        connection.execute(
            "INSERT INTO workflow_sessions (id, kind, started_at) "
            "VALUES (%s, 'lore_entry', now())", (workflow_id,))
        connection.execute(
            "INSERT INTO change_sets (id, idempotency_key, workflow_session_id, status, "
            "requested_at, applied_at) VALUES (%s, %s, %s, 'applied', now(), now())",
            (change_set_id, f"seed:{change_set_id}", workflow_id))
        connection.execute(
            "INSERT INTO entities (id, entity_type, canonical_name, created_by_change_set_id, "
            "created_at, updated_at) VALUES (%s, 'npc', %s, %s, now(), now())",
            (entity_id, name, change_set_id))
    return entity_id


def seed_claim(entity_id, text: str) -> None:
    revision_id, span_id, claim_id = uuid4(), uuid4(), uuid4()
    document_id = uuid4()
    with psycopg.connect(TEST_DSN) as connection:
        connection.execute(
            "INSERT INTO source_documents (id, source_kind, connector, original_path, "
            "first_seen_at) VALUES (%s, 'markdown', 'markdown', %s, now())",
            (document_id, f"lore/{uuid4().hex[:8]}.md"))
        connection.execute(
            "INSERT INTO source_revisions (id, source_document_id, content_hash, raw_content, "
            "importer_version, captured_at) VALUES (%s, %s, %s, %s, 'test', now())",
            (revision_id, document_id, sha256(text.encode()).hexdigest(), text.encode()))
        connection.execute(
            "INSERT INTO claims (id, subject_entity_id, assertion_text, state, authority, "
            "confidence, visibility, recorded_at, created_at, updated_at) "
            "VALUES (%s, %s, %s, 'established', 'explicit_lore', 1.0, 'dm_only', "
            "now(), now(), now())", (claim_id, entity_id, text))
        connection.execute(
            "INSERT INTO source_spans (id, source_revision_id, start_offset, end_offset, "
            "excerpt_hash) VALUES (%s, %s, 0, %s, %s)",
            (span_id, revision_id, len(text), sha256(text.encode()).hexdigest()))
        connection.execute(
            "INSERT INTO claim_evidence (claim_id, source_span_id, evidence_role) "
            "VALUES (%s, %s, 'support')", (claim_id, span_id))


def queue() -> PostgresIdentityQueueRepository:
    return PostgresIdentityQueueRepository(PostgresDatabase(TEST_DSN))


def test_queue_surfaces_recurring_gaps_with_evidence_and_alias_candidates():
    romulus, rhetus = seed_entity("Romulus"), seed_entity("Rhetus")
    seed_claim(romulus, "The Silver Cloaks patrol the harbor gate.")
    seed_claim(romulus, "Members of the Silver Cloaks collect tolls.")
    seed_claim(rhetus, "Romulus commands the Inquisition.")
    result = queue().queue(limit=10)
    surfaces = {gap.normalized_surface: gap for gap in result.gaps}
    assert "silver cloaks" in surfaces
    gap = surfaces["silver cloaks"]
    assert gap.claims_with_phrase == 2
    assert len(gap.evidence) == 2
    # "inquisition" needs two claims to qualify; one mention keeps it out.
    assert "inquisition" not in surfaces


def test_create_entity_decision_resolves_surface_audited():
    romulus = seed_entity("Romulus")
    seed_claim(romulus, "The Silver Cloaks patrol the harbor gate.")
    seed_claim(romulus, "Members of the Silver Cloaks collect tolls.")
    repository = queue()
    receipt = repository.create_entity(CreateEntityDecision(
        surface="Silver Cloaks", entity_kind="faction", idempotency_key="create-1"))
    assert receipt.entity_id is not None
    with psycopg.connect(TEST_DSN) as connection:
        row = connection.execute(
            "SELECT e.entity_type, e.canonical_name, cs.status FROM entities e "
            "JOIN change_sets cs ON cs.id = e.created_by_change_set_id WHERE e.id = %s",
            (receipt.entity_id,)).fetchone()
    assert row == ("faction", "Silver Cloaks", "applied")
    replay = repository.create_entity(CreateEntityDecision(
        surface="Silver Cloaks", entity_kind="faction", idempotency_key="create-1"))
    assert replay.idempotent_replay and replay.decision_id == receipt.decision_id
    surfaces = {gap.normalized_surface for gap in queue().queue(limit=50).gaps}
    assert "silver cloaks" not in surfaces
    # The name now resolves, so a second creation attempt is refused.
    with pytest.raises(IdentityQueueError):
        repository.create_entity(CreateEntityDecision(
            surface="Silver Cloaks", entity_kind="faction", idempotency_key="create-2"))


def test_add_alias_decision_sources_from_evidence_and_refuses_theft():
    romulus, rhetus = seed_entity("Romulus"), seed_entity("Rhetus")
    seed_claim(romulus, "The Grand Inquisitor issues decrees.")
    seed_claim(romulus, "Servants fear the Grand Inquisitor greatly.")
    repository = queue()
    receipt = repository.add_alias(AddAliasDecision(
        surface="Grand Inquisitor", entity_id=romulus, idempotency_key="alias-1"))
    assert receipt.entity_id == romulus
    with psycopg.connect(TEST_DSN) as connection:
        row = connection.execute(
            "SELECT namespace, alias_kind FROM entity_aliases WHERE entity_id = %s",
            (romulus,)).fetchone()
    assert row == ("identity_queue", "queue_decision")
    with pytest.raises(IdentityQueueError):
        repository.add_alias(AddAliasDecision(
            surface="Rhetus", entity_id=romulus, idempotency_key="alias-2"))
    with pytest.raises(IdentityQueueError):
        repository.add_alias(AddAliasDecision(
            surface="Unmentioned Phrase", entity_id=romulus, idempotency_key="alias-3"))


def test_dismiss_and_mark_role_hide_surfaces_from_queue():
    romulus = seed_entity("Romulus")
    seed_claim(romulus, "The Lonely Watch marches at dusk.")
    seed_claim(romulus, "The Lonely Watch rests at dawn.")
    repository = queue()
    assert "lonely watch" in {g.normalized_surface for g in repository.queue(10).gaps}
    repository.dismiss(SurfaceDecision(surface="Lonely Watch", idempotency_key="dismiss-1"))
    assert "lonely watch" not in {g.normalized_surface for g in repository.queue(10).gaps}
    seed_claim(romulus, "The Silent Watch also marches.")
    seed_claim(romulus, "The Silent Watch also rests.")
    repository.mark_role(SurfaceDecision(surface="Silent Watch", idempotency_key="role-1"))
    assert "silent watch" not in {g.normalized_surface for g in repository.queue(10).gaps}


def test_demand_ranks_queue_and_ignores_resolving_names():
    romulus = seed_entity("Romulus")
    # Quiet surface: high frequency, never looked up.
    seed_claim(romulus, "The Quiet Guild meets at dusk.")
    seed_claim(romulus, "The Quiet Guild meets at dawn.")
    seed_claim(romulus, "The Quiet Guild keeps ledgers.")
    # Demanded surface: lower frequency, but lookup misses keep reaching for it.
    seed_claim(romulus, "The Loud Guild marches once.")
    seed_claim(romulus, "The Loud Guild marches twice.")
    repository = queue()
    repository.record_demand("Loud Guild", "entity_lookup")
    repository.record_demand("Loud Guild", "entity_lookup")
    repository.record_demand("Romulus", "entity_lookup")  # resolves: not demand
    result = repository.queue(limit=10)
    surfaces = [gap.normalized_surface for gap in result.gaps]
    assert surfaces.index("loud guild") < surfaces.index("quiet guild")
    by_name = {gap.normalized_surface: gap for gap in result.gaps}
    assert by_name["loud guild"].retrieval_demand == 2
    assert by_name["quiet guild"].retrieval_demand == 0
    with psycopg.connect(TEST_DSN) as connection:
        demand_rows = connection.execute(
            "SELECT count(*) FROM identity_demand_log").fetchone()
    assert demand_rows[0] == 1


def test_entity_lookup_misses_record_demand_through_http():
    import asyncio

    import httpx

    from dm_assistant_core.api.app import create_app
    from dm_assistant_core.config import Settings

    romulus = seed_entity("Romulus")
    seed_claim(romulus, "The Harbor Guild trades at noon.")
    seed_claim(romulus, "The Harbor Guild trades at dusk.")
    app = create_app(Settings(database_url=TEST_DSN, environment="test",
                              run_migrations=False))

    async def lookup() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            miss = await client.get("/entities", params={
                "canonical_name": "Harbor Guild", "requester_role": "dm"})
            hit = await client.get("/entities", params={
                "canonical_name": "Romulus", "requester_role": "dm"})
        assert miss.status_code == 200 and miss.json() == []
        assert hit.status_code == 200 and len(hit.json()) == 1

    asyncio.run(lookup())
    result = queue().queue(limit=10)
    gap = next(g for g in result.gaps if g.normalized_surface == "harbor guild")
    assert gap.retrieval_demand == 1


def test_create_identity_with_aliases_merges_surfaces_audited():
    romulus = seed_entity("Romulus")
    seed_claim(romulus, "The Court of the Stars convenes at midnight.")
    seed_claim(romulus, "The Court of the Stars convenes at dawn.")
    seed_claim(romulus, "The Stars keep vigil nightly.")
    seed_claim(romulus, "The Stars keep vigil daily.")
    repository = queue()
    result = repository.queue(limit=10)
    by_name = {gap.normalized_surface: gap for gap in result.gaps}
    assert by_name["court of the stars"].related_surfaces == ("Stars",)
    assert by_name["stars"].related_surfaces == ("Court of the Stars",)

    receipt = repository.create_entity(CreateEntityDecision(
        surface="Court of the Stars", entity_kind="faction",
        alias_surfaces=("Stars",), idempotency_key="merge-1"))
    assert receipt.entity_id is not None
    with psycopg.connect(TEST_DSN) as connection:
        rows = connection.execute(
            "SELECT a.alias, a.alias_kind FROM entity_aliases a "
            "WHERE a.entity_id = %s ORDER BY a.alias", (receipt.entity_id,)).fetchall()
        decision = connection.execute(
            "SELECT details FROM identity_decisions WHERE id = %s",
            (receipt.decision_id,)).fetchone()
    assert rows == [("Stars", "queue_decision")]
    assert decision[0]["alias_surfaces"] == ["Stars"]
    surfaces = {gap.normalized_surface for gap in repository.queue(10).gaps}
    assert "court of the stars" not in surfaces and "stars" not in surfaces


def test_create_identity_rejects_unevidenced_and_owned_aliases():
    romulus, rhetus = seed_entity("Romulus"), seed_entity("Rhetus")
    seed_claim(romulus, "The Court of the Stars convenes at midnight.")
    seed_claim(romulus, "The Court of the Stars convenes at dawn.")
    repository = queue()
    with pytest.raises(IdentityQueueError, match="no current claim evidence"):
        repository.create_entity(CreateEntityDecision(
            surface="Court of the Stars", entity_kind="faction",
            alias_surfaces=("Unmentioned Guild",), idempotency_key="merge-2"))
    with psycopg.connect(TEST_DSN) as connection:
        leftovers = connection.execute(
            "SELECT count(*) FROM entities e WHERE lower(e.canonical_name) = "
            "'court of the stars'").fetchone()
    assert leftovers[0] == 0  # rejected decision left nothing behind


def test_role_marks_set_precedent_hints_on_similar_surfaces():
    romulus = seed_entity("Romulus")
    seed_claim(romulus, "The Grand Inquisitor issues decrees.")
    seed_claim(romulus, "The Grand Inquisitor attends court.")
    seed_claim(romulus, "The High Inquisitor signs papers.")
    seed_claim(romulus, "The High Inquisitor reads reports.")
    repository = queue()
    repository.mark_role(SurfaceDecision(surface="Grand Inquisitor",
                                         idempotency_key="role-a"))
    by_name = {gap.normalized_surface: gap for gap in repository.queue(10).gaps}
    assert "grand inquisitor" not in by_name  # decided surfaces leave the queue
    assert by_name["high inquisitor"].role_hint is True


def test_queue_suggests_canonical_name_and_kind():
    romulus = seed_entity("Romulus")
    seed_claim(romulus, "King Peter le Fleur rules from the castle.")
    seed_claim(romulus, "King Peter le Fleur signs the charter.")
    seed_claim(romulus, "The Silver Cloaks patrol the gates.")
    seed_claim(romulus, "The Silver Cloaks collect tolls.")
    by_name = {gap.normalized_surface: gap for gap in queue().queue(10).gaps}
    king = by_name["king peter le fleur"]
    assert king.suggested_canonical_name == "Peter le Fleur"
    assert king.suggested_kind is None or king.suggested_kind.value == "npc"
    assert by_name["silver cloaks"].suggested_kind is not None
    assert by_name["silver cloaks"].suggested_kind.value == "faction"


def test_created_identity_arrives_linked_to_its_claims():
    romulus, rhetus = seed_entity("Romulus"), seed_entity("Rhetus")
    seed_claim(romulus, "The Infinite Twilight spreads across the sky.")
    seed_claim(romulus, "The Infinite Twilight darkens the moon.")
    seed_claim(rhetus, "Romulus drives the world toward the Infinite Twilight.")
    receipt = queue().create_entity(CreateEntityDecision(
        surface="Infinite Twilight", entity_kind="worldbuilding",
        idempotency_key="link-1"))
    assert receipt.linked_claims == 3
    with psycopg.connect(TEST_DSN) as connection:
        rows = connection.execute(
            "SELECT c.assertion_text FROM claim_related_entities cre "
            "JOIN claims c ON c.id = cre.claim_id WHERE cre.entity_id = %s",
            (receipt.entity_id,)).fetchall()
        kinds = connection.execute(
            "SELECT DISTINCT relation_kind FROM claim_related_entities "
            "WHERE entity_id = %s", (receipt.entity_id,)).fetchall()
    assert len(rows) == 3
    assert kinds == [("derived_mention",)]


def test_added_alias_links_its_claims_too():
    romulus = seed_entity("Romulus")
    seed_claim(romulus, "The Grand Inquisitor issues decrees.")
    seed_claim(romulus, "Servants fear the Grand Inquisitor.")
    receipt = queue().add_alias(AddAliasDecision(
        surface="Grand Inquisitor", entity_id=romulus, idempotency_key="link-2"))
    assert receipt.linked_claims == 2
    with psycopg.connect(TEST_DSN) as connection:
        count = connection.execute(
            "SELECT count(*) FROM claim_related_entities WHERE entity_id = %s "
            "AND relation_kind = 'derived_mention'", (romulus,)).fetchone()
    assert count[0] == 2


def test_revert_alias_removes_alias_and_unjustified_links_only():
    from dm_assistant_core.application.identity_gaps import RevertDecision
    church = seed_entity("Church of the Golden Dawn")
    seed_claim(church, "The Golden Dawn gathers at dawn.")
    seed_claim(church, "The Golden Dawn disperses by noon.")
    seed_claim(church, "The Church of the Golden Dawn stands in Unity.")
    repository = queue()
    add = repository.add_alias(AddAliasDecision(
        surface="Golden Dawn", entity_id=church, idempotency_key="alias-x"))
    assert add.linked_claims == 3  # word-boundary match, including inside the full name
    revert = repository.revert(RevertDecision(
        decision_id=add.decision_id, idempotency_key="revert-x"))
    assert revert.kind == "revert"
    assert revert.details["aliases_removed"] == 1
    # The canonical-name claim keeps its derived link; alias-only claims lose theirs.
    with psycopg.connect(TEST_DSN) as connection:
        remaining = connection.execute(
            "SELECT c.assertion_text FROM claim_related_entities cre "
            "JOIN claims c ON c.id = cre.claim_id WHERE cre.entity_id = %s",
            (church,)).fetchall()
        alias_row = connection.execute(
            "SELECT count(*) FROM entity_aliases WHERE entity_id = %s AND "
            "normalized_alias = 'golden dawn'", (church,)).fetchone()
    assert [row[0] for row in remaining] == [
        "The Church of the Golden Dawn stands in Unity."]
    assert alias_row[0] == 0
    replayed = repository.revert(RevertDecision(
        decision_id=add.decision_id, idempotency_key="revert-x"))
    assert replayed.idempotent_replay is True


def test_revert_refuses_unknown_receipts_and_double_reverts():
    from dm_assistant_core.application.identity_gaps import RevertDecision
    repository = queue()
    with pytest.raises(IdentityQueueError, match="no decision matches"):
        repository.revert(RevertDecision(
            decision_id=uuid4(), idempotency_key="revert-missing"))
    romulus = seed_entity("Romulus")
    seed_claim(romulus, "The Silver Cloaks patrol the gate.")
    seed_claim(romulus, "The Silver Cloaks rest at dusk.")
    add = repository.add_alias(AddAliasDecision(
        surface="Silver Cloaks", entity_id=romulus, idempotency_key="alias-y"))
    repository.revert(RevertDecision(
        decision_id=add.decision_id, idempotency_key="revert-y"))
    with pytest.raises(IdentityQueueError, match="already reverted"):
        repository.revert(RevertDecision(
            decision_id=add.decision_id, idempotency_key="revert-y2"))


def test_capitalized_alias_links_only_proper_noun_usage():
    arkin = seed_entity("Monastery of Arkin")
    seed_claim(arkin, "Fleurite contains the castle, the harbor, and a small monastery nearby.")
    seed_claim(arkin, "The party returns to the Monastery after the ascent.")
    repository = queue()
    receipt = repository.add_alias(AddAliasDecision(
        surface="Monastery", entity_id=arkin, idempotency_key="alias-case"))
    assert receipt.linked_claims == 1  # lowercase generic mention does not link
    with psycopg.connect(TEST_DSN) as connection:
        linked = connection.execute(
            "SELECT c.assertion_text FROM claim_related_entities cre "
            "JOIN claims c ON c.id = cre.claim_id WHERE cre.entity_id = %s",
            (arkin,)).fetchall()
    assert [row[0] for row in linked] == ["The party returns to the Monastery after the ascent."]


def test_misspelling_resolves_lookups_but_is_never_a_name():
    from dm_assistant_core.adapters.postgres.entity_lookup import (
        PostgresEntityLookupRepository,
    )
    from dm_assistant_core.adapters.postgres.library_entries import (
        PostgresLibraryEntryRepository,
    )
    from dm_assistant_core.application.identity_gaps import MarkMisspellingDecision

    coreferra = seed_entity("Coreferra")
    seed_claim(coreferra, "Corefera feels the pull of the leylines.")
    seed_claim(coreferra, "Coreera watches from the ridge.")  # different typo, stays unlinked
    repository = queue()
    receipt = repository.mark_misspelling(MarkMisspellingDecision(
        surface="Corefera", entity_id=coreferra, idempotency_key="miss-1"))
    assert receipt.kind == "mark_misspelling"
    assert receipt.linked_claims == 1  # only the exact typo links
    with psycopg.connect(TEST_DSN) as connection:
        row = connection.execute(
            "SELECT alias_kind FROM entity_aliases WHERE entity_id = %s AND "
            "normalized_alias = 'corefera'", (coreferra,)).fetchone()
    assert row == ("misspelling",)

    database = PostgresDatabase(TEST_DSN)
    matches = PostgresEntityLookupRepository(database).search("Corefera", 5)
    assert [m.canonical_name for m in matches] == ["Coreferra"]  # resolves
    entry = PostgresLibraryEntryRepository(database).get(coreferra)
    assert entry.misspellings == ("Corefera",)  # but never a name
    assert "Corefera" not in entry.aliases

    # Reverting a misspelling works like any alias decision.
    from dm_assistant_core.application.identity_gaps import RevertDecision
    revert = repository.revert(RevertDecision(
        decision_id=receipt.decision_id, idempotency_key="miss-revert"))
    assert revert.details["aliases_removed"] == 1


def test_manual_alias_declarations_need_no_claim_evidence():
    romulus = seed_entity("Romulus")
    seed_claim(romulus, "The Golden Dawn gathers at dawn.")
    seed_claim(romulus, "The Golden Dawn disperses by noon.")
    receipt = queue().create_entity(CreateEntityDecision(
        surface="Golden Dawn", entity_kind="worldbuilding",
        alias_surfaces=(), manual_aliases=("Era of the Golden Dawn",),
        idempotency_key="manual-1"))
    assert receipt.entity_id is not None
    with psycopg.connect(TEST_DSN) as connection:
        row = connection.execute(
            "SELECT alias_kind FROM entity_aliases WHERE entity_id = %s AND "
            "normalized_alias = 'era of the golden dawn'", (receipt.entity_id,)).fetchone()
        details = connection.execute(
            "SELECT details FROM identity_decisions WHERE id = %s",
            (receipt.decision_id,)).fetchone()
    assert row == ("manual_declaration",)
    assert details[0]["manual_aliases"] == ["Era of the Golden Dawn"]

    # Manual aliases still never steal a name another identity owns.
    seed_entity("Rhetus")
    with pytest.raises(IdentityQueueError, match="belongs to another identity"):
        queue().create_entity(CreateEntityDecision(
            surface="Silver Cloaks", entity_kind="faction",
            alias_surfaces=(), manual_aliases=("Rhetus",),
            idempotency_key="manual-2"))


def test_manual_alias_anchors_to_alias_evidence_when_surface_is_expanded():
    narrator = seed_entity("Narrator")
    # Claims only ever say "Penelope"; the DM knows the full name.
    seed_claim(narrator, "Penelope keeps the ledger.")
    seed_claim(narrator, "Penelope argues with the magistrate.")
    receipt = queue().create_entity(CreateEntityDecision(
        surface="Penelope Clinkhammer", entity_kind="pc",
        alias_surfaces=(), manual_aliases=("Penelope",),
        idempotency_key="penelope-1"))
    assert receipt.linked_claims == 2  # via the manual alias's name
    with psycopg.connect(TEST_DSN) as connection:
        row = connection.execute(
            "SELECT alias_kind FROM entity_aliases WHERE entity_id = %s AND "
            "normalized_alias = 'penelope'", (receipt.entity_id,)).fetchone()
        linked = connection.execute(
            "SELECT count(*) FROM claim_related_entities WHERE entity_id = %s",
            (receipt.entity_id,)).fetchone()
    assert row == ("manual_declaration",)
    assert linked[0] == 2


def test_reconcile_links_connects_pre_linking_identities():
    from uuid import uuid4 as _uuid4
    myrin = seed_entity("Myrin")
    seed_claim(myrin, "Myrin holds the leyline confluence.")
    seed_claim(myrin, "The Titans shaped Myrin itself.")
    seed_claim(myrin, "Unrelated prose about lamps.")
    with psycopg.connect(TEST_DSN) as connection:
        connection.execute("DELETE FROM claim_related_entities WHERE entity_id = %s", (myrin,))
    repository = queue()
    receipt = repository.reconcile_links(myrin, "reconcile-myrin")
    assert receipt.kind == "reconcile_links"
    assert receipt.linked_claims == 2  # lamp claim stays unlinked
    with psycopg.connect(TEST_DSN) as connection:
        rows = connection.execute(
            "SELECT c.assertion_text FROM claim_related_entities cre "
            "JOIN claims c ON c.id = cre.claim_id WHERE cre.entity_id = %s "
            "ORDER BY c.assertion_text", (myrin,)).fetchall()
    assert [row[0] for row in rows] == [
        "Myrin holds the leyline confluence.", "The Titans shaped Myrin itself."]
    replay = repository.reconcile_links(myrin, "reconcile-myrin")
    assert replay.idempotent_replay is True


def test_membership_roster_decisions():
    # seed_entity writes npc; the kind trigger forbids reclassifying pc/npc, so
    # build the faction entity through the audited queue create path instead.
    narrator = seed_entity("Narrator")
    seed_claim(narrator, "The Council recognized the party as the Carpet Rollers.")
    repository = queue()
    created = repository.create_entity(CreateEntityDecision(
        surface="Carpet Rollers", entity_kind="faction", idempotency_key="create-rollers"))
    rollers = created.entity_id
    ruhrogue = seed_entity("Ruhrogue")
    romulus = seed_entity("Romulus")
    from dm_assistant_core.application.identity_gaps import MembershipDecision
    repository = queue()
    receipt = repository.membership(MembershipDecision(
        faction_id=rollers, member_id=ruhrogue, role_title="reluctant hero",
        idempotency_key="member-1"))
    assert receipt.kind == "membership"
    with pytest.raises(IdentityQueueError, match="already a member"):
        repository.membership(MembershipDecision(
            faction_id=rollers, member_id=ruhrogue, idempotency_key="member-2"))
    with pytest.raises(IdentityQueueError, match="requires a faction"):
        repository.membership(MembershipDecision(
            faction_id=ruhrogue, member_id=romulus, idempotency_key="member-3"))

    # Roster drives the members list once any explicit record exists.
    from dm_assistant_core.adapters.postgres.library_entries import (
        PostgresLibraryEntryRepository,
    )
    entry = PostgresLibraryEntryRepository(PostgresDatabase(TEST_DSN)).get(rollers)
    assert [member.name for member in entry.members] == ["Ruhrogue"]
    assert entry.members[0].role_title == "reluctant hero"

    removed = repository.membership(MembershipDecision(
        faction_id=rollers, member_id=ruhrogue, add=False,
        idempotency_key="member-4"))
    assert removed.kind == "membership"
    entry = PostgresLibraryEntryRepository(PostgresDatabase(TEST_DSN)).get(rollers)
    assert entry.members == ()  # roster existed, so the derived fallback stays off
    with pytest.raises(IdentityQueueError, match="no current membership"):
        repository.membership(MembershipDecision(
            faction_id=rollers, member_id=ruhrogue, add=False,
            idempotency_key="member-5"))
    replay = repository.membership(MembershipDecision(
        faction_id=rollers, member_id=ruhrogue, idempotency_key="member-1"))
    assert replay.idempotent_replay is True


def test_faction_role_decisions():
    from dm_assistant_core.application.identity_gaps import MembershipDecision, RoleDecision
    from dm_assistant_core.adapters.postgres.database import PostgresDatabase
    from dm_assistant_core.adapters.postgres.library_entries import (
        PostgresLibraryEntryRepository,
    )

    narrator = seed_entity("Chronicler")
    seed_claim(narrator, "The Inquisitors enforce doctrine across Goodman's City.")
    repository = queue()
    faction = repository.create_entity(CreateEntityDecision(
        surface="Inquisitors", entity_kind="faction",
        idempotency_key="create-inquisitors")).entity_id
    eustice, romulus, rhetus = seed_entity("Eustice"), seed_entity("Romulus"), seed_entity("Rhetus")
    solis = seed_entity("Solis")
    for member in (eustice, romulus, rhetus, solis):
        repository.membership(MembershipDecision(
            faction_id=faction, member_id=member, idempotency_key=f"roster-{member}"))

    library_repo = PostgresLibraryEntryRepository(PostgresDatabase(TEST_DSN))

    # Define-on-assign: the leadership seat and the shared role both come into
    # existence through assignment; reuse is case-insensitive and keeps the
    # catalog's canonical casing.
    repository.role(RoleDecision(faction_id=faction, member_id=eustice,
                                 role_name="Grand Inquisitor", is_leadership=True,
                                 idempotency_key="role-1"))
    repository.role(RoleDecision(faction_id=faction, member_id=romulus,
                                 role_name="Inquisitor", idempotency_key="role-2"))
    repository.role(RoleDecision(faction_id=faction, member_id=rhetus,
                                 role_name="inquisitor", idempotency_key="role-3"))

    library = library_repo.get(faction)
    members = {member.name: member for member in library.members}
    assert members["Eustice"].role_title == "Grand Inquisitor"
    assert members["Eustice"].is_leadership is True
    assert members["Romulus"].role_title == "Inquisitor"
    assert members["Rhetus"].role_title == "Inquisitor"
    assert members["Rhetus"].is_leadership is False
    roles = {role.name: role for role in library.roles}
    assert set(roles) == {"Grand Inquisitor", "Inquisitor"}
    assert roles["Grand Inquisitor"].holder_names == ("Eustice",)
    assert roles["Grand Inquisitor"].is_leadership is True
    assert roles["Inquisitor"].holder_names == ("Rhetus", "Romulus")

    # A leadership seat refuses a second holder by name — never a silent transfer.
    with pytest.raises(IdentityQueueError, match="held by Eustice"):
        repository.role(RoleDecision(faction_id=faction, member_id=romulus,
                                     role_name="Grand Inquisitor",
                                     idempotency_key="role-4"))
    with pytest.raises(IdentityQueueError, match="already holds"):
        repository.role(RoleDecision(faction_id=faction, member_id=rhetus,
                                     role_name="Inquisitor", idempotency_key="role-5"))
    with pytest.raises(IdentityQueueError, match="holds no role"):
        repository.role(RoleDecision(faction_id=faction, member_id=solis,
                                     role_name=None, idempotency_key="role-6"))

    # Succession is explicit: clear the seat, then seat the successor.
    repository.role(RoleDecision(faction_id=faction, member_id=eustice,
                                 role_name=None, idempotency_key="role-7"))
    library = library_repo.get(faction)
    roles = {role.name: role for role in library.roles}
    assert roles["Grand Inquisitor"].holder_names == ()  # a vacant seat survives
    assert {member.name: member.role_title for member in library.members}["Eustice"] is None
    repository.role(RoleDecision(faction_id=faction, member_id=romulus,
                                 role_name="Grand Inquisitor", idempotency_key="role-8"))
    library = library_repo.get(faction)
    roles = {role.name: role for role in library.roles}
    assert roles["Grand Inquisitor"].holder_names == ("Romulus",)

    # Role history rides the membership supersession chain.
    with psycopg.connect(TEST_DSN) as connection:
        prior = connection.execute(
            "SELECT role_title FROM membership_records WHERE member_id = %s "
            "AND superseded_by IS NOT NULL", (eustice,)).fetchall()
    assert {row[0] for row in prior} == {None, "Grand Inquisitor"}

    replay = repository.role(RoleDecision(faction_id=faction, member_id=eustice,
                                          role_name="Grand Inquisitor",
                                          idempotency_key="role-1"))
    assert replay.idempotent_replay is True
    outsider = seed_entity("Outsider")
    with pytest.raises(IdentityQueueError, match="not on the roster"):
        repository.role(RoleDecision(faction_id=faction, member_id=outsider,
                                     role_name="Inquisitor", idempotency_key="role-9"))

    # Removing the holder leaves the seat vacant for a successor.
    repository.membership(MembershipDecision(faction_id=faction, member_id=romulus,
                                             add=False, idempotency_key="role-remove-1"))
    library = library_repo.get(faction)
    roles = {role.name: role for role in library.roles}
    assert roles["Grand Inquisitor"].holder_names == ()


def test_role_definitions_precede_seating():
    from dm_assistant_core.application.identity_gaps import (
        MembershipDecision, RoleDecision, RoleDefinitionDecision,
    )

    narrator = seed_entity("Chronicler")
    seed_claim(narrator, "The White Cloaks guard the northern road.")
    repository = queue()
    faction = repository.create_entity(CreateEntityDecision(
        surface="White Cloaks", entity_kind="faction",
        idempotency_key="create-white-cloaks")).entity_id

    # A leadership seat can be defined before anyone is seated (vacant).
    repository.define_role(RoleDefinitionDecision(
        faction_id=faction, role_name="Captain", is_leadership=True,
        idempotency_key="define-1"))
    listing = [role for role in repository.roles() if role.faction_name == "White Cloaks"]
    assert len(listing) == 1
    assert listing[0].name == "Captain"
    assert listing[0].is_leadership is True
    assert listing[0].holders == ()

    # Case-insensitive duplicate definition is refused, as are non-faction targets.
    with pytest.raises(IdentityQueueError, match="already defines"):
        repository.define_role(RoleDefinitionDecision(
            faction_id=faction, role_name="captain", idempotency_key="define-2"))
    with pytest.raises(IdentityQueueError, match="require a faction target"):
        repository.define_role(RoleDefinitionDecision(
            faction_id=narrator, role_name="Captain", idempotency_key="define-3"))

    # Seating a member into the predefined role keeps the standing definition.
    bran = seed_entity("Bran")
    repository.membership(MembershipDecision(
        faction_id=faction, member_id=bran, idempotency_key="seat-1"))
    repository.role(RoleDecision(faction_id=faction, member_id=bran,
                                 role_name="Captain", is_leadership=False,
                                 idempotency_key="seat-2"))
    listing = [role for role in repository.roles() if role.faction_name == "White Cloaks"]
    assert listing[0].holders == ((bran, "Bran"),)
    assert listing[0].is_leadership is True


def test_role_declarations_bridge_identity_review():
    from dm_assistant_core.application.identity_gaps import (
        RoleDefinitionDecision, SurfaceDecision,
    )

    narrator = seed_entity("Chronicler")
    seed_claim(narrator, "The Inquisitors question travelers at the gate.")
    repository = queue()
    faction = repository.create_entity(CreateEntityDecision(
        surface="Inquisitors", entity_kind="faction",
        idempotency_key="create-inquisitors-2")).entity_id
    repository.mark_role(SurfaceDecision(surface="Inquisitor", idempotency_key="mark-1"))
    repository.mark_role(SurfaceDecision(surface="Grand Inquisitor", idempotency_key="mark-2"))

    surfaces = {declaration.surface for declaration in repository.role_declarations()}
    assert {"Inquisitor", "Grand Inquisitor"} <= surfaces

    # Linking a declared surface to a faction removes it from the unlinked list.
    repository.define_role(RoleDefinitionDecision(
        faction_id=faction, role_name="Grand Inquisitor", is_leadership=True,
        idempotency_key="define-gi"))
    surfaces = {declaration.surface for declaration in repository.role_declarations()}
    assert "Grand Inquisitor" not in surfaces
    assert "Inquisitor" in surfaces


def test_recent_decisions_listing_newest_first():
    from dm_assistant_core.application.identity_gaps import MembershipDecision

    narrator = seed_entity("Chronicler")
    seed_claim(narrator, "The Dawn Wardens patrol the east road at dawn.")
    repository = queue()
    faction = repository.create_entity(CreateEntityDecision(
        surface="Dawn Wardens", entity_kind="faction",
        idempotency_key="create-dawn-wardens")).entity_id
    member = seed_entity("Sable")
    repository.membership(MembershipDecision(
        faction_id=faction, member_id=member, idempotency_key="log-1"))

    entries = repository.recent_decisions(limit=10)
    kinds = [entry.kind for entry in entries]
    assert "create_entity" in kinds and "membership" in kinds
    assert all(entry.decided_at is not None for entry in entries)
    # Newest first (ties tolerated — same-transaction timestamps), details preserved.
    assert all(entries[index].decided_at >= entries[index + 1].decided_at
               for index in range(len(entries) - 1))
    membership_entry = next(entry for entry in entries if entry.kind == "membership")
    assert membership_entry.details["action"] == "add"
