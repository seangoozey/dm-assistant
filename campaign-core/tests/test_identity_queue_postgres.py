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
