from __future__ import annotations

import os
from hashlib import sha256
from uuid import uuid4

import psycopg
import pytest

from dm_assistant_core.adapters.postgres.database import PostgresDatabase
from dm_assistant_core.adapters.postgres.entity_profiles import (
    PostgresEntityProfileRepository,
)
from dm_assistant_core.adapters.postgres.migrate import run_migrations
from dm_assistant_core.application.entity_profiles import (
    EntityProfileError,
    UpdateEntityProfileCommand,
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


def seed_identity(name: str, kind: str = "npc") -> tuple:
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
            "created_at, updated_at) VALUES (%s, %s, %s, %s, now(), now())",
            (entity_id, kind, name, change_set_id))
    return entity_id


def seed_linked_claim(entity_id, text: str) -> None:
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
        connection.execute(
            "INSERT INTO claim_related_entities (claim_id, entity_id, relation_kind) "
            "VALUES (%s, %s, 'mentioned')", (claim_id, entity_id))


def repository() -> PostgresEntityProfileRepository:
    return PostgresEntityProfileRepository(PostgresDatabase(TEST_DSN))


def profile(entity_id, version=0, **changes):
    base = dict(entity_id=entity_id, version=version, canonical_name="Far Realm",
                status=None, location_type=None, parent_location=None, player=None,
                race=None, sex=None, aliases=(), summary="")
    base.update(changes)
    return UpdateEntityProfileCommand(idempotency_key=f"key:{uuid4()}", **base)


def test_location_profile_saves_versions_and_syncs_aliases():
    far_realm = seed_identity("Far Realm", kind="location")
    seed_linked_claim(far_realm, "The Far Realm presses against the veil.")
    repo = repository()
    first = repo.update(profile(far_realm, location_type="planar region",
                                status="sealed", parent_location="cosmology",
                                aliases=["the Far Realm Entity"]))
    assert first.version == 1
    assert first.alias_sync.applied == ("the Far Realm Entity",)
    second = repo.update(profile(far_realm, version=1, location_type="planar region",
                                 status="breached",
                                 aliases=["the Far Realm Entity"]))
    assert second.version == 2
    assert second.alias_sync is None  # no alias changes
    stored = repo.get(far_realm)
    assert stored.status == "breached"
    assert stored.location_type == "planar region"
    with psycopg.connect(TEST_DSN) as connection:
        alias_row = connection.execute(
            "SELECT alias_kind FROM entity_aliases WHERE entity_id = %s AND "
            "normalized_alias = 'the far realm entity'", (far_realm,)).fetchone()
        revisions = connection.execute(
            "SELECT count(*) FROM entity_profile_revisions WHERE entity_id = %s",
            (far_realm,)).fetchone()
    assert alias_row == ("profile_edit",)
    assert revisions[0] == 2
    with pytest.raises(EntityProfileError):
        repo.update(profile(far_realm, version=1))  # stale version refused


def test_alias_removal_and_conflict_skips_follow_profile_edits():
    ruh = seed_identity("Ruh")
    other = seed_identity("Rhetus")
    seed_linked_claim(ruh, "Ruh fell at The Ocho.")
    repo = repository()
    repo.update(profile(ruh, canonical_name="Ruh", status="active",
                        aliases=["Rhetus", "the fallen knight"]))
    with psycopg.connect(TEST_DSN) as connection:
        rows = connection.execute(
            "SELECT normalized_alias FROM entity_aliases WHERE entity_id = %s AND "
            "namespace = 'profile' ORDER BY normalized_alias", (ruh,)).fetchall()
    # "Rhetus" belongs to another identity and is skipped, not stolen.
    assert rows == [("the fallen knight",)]
    receipt = repo.update(profile(ruh, version=1, canonical_name="Ruh",
                                  status="active", aliases=[]))
    assert receipt.alias_sync.removed == ("the fallen knight",)
    with psycopg.connect(TEST_DSN) as connection:
        count = connection.execute(
            "SELECT count(*) FROM entity_aliases WHERE entity_id = %s AND "
            "namespace = 'profile'", (ruh,)).fetchone()
    assert count[0] == 0


def test_idempotent_replay_returns_same_receipt():
    entity = seed_identity("White Cloaks", kind="faction")
    seed_linked_claim(entity, "The White Cloaks patrol the gates.")
    command = profile(entity, canonical_name="White Cloaks", status="active")
    repo = repository()
    first = repo.update(command)
    replay = repo.update(command)
    assert replay.idempotent_replay is True
    assert replay.receipt_id == first.receipt_id
    stored = repo.get(entity)
    assert stored.version == 1


def test_profile_editor_removes_mistaken_manual_declarations_but_not_queue_aliases():
    from dm_assistant_core.application.identity_gaps import CreateEntityDecision
    from dm_assistant_core.adapters.postgres.identity_gaps import (
        PostgresIdentityQueueRepository,
    )
    queue_repo = PostgresIdentityQueueRepository(PostgresDatabase(TEST_DSN))
    seed_claim_holder = seed_identity("Narrator")
    seed_linked_claim(seed_claim_holder, "Only the Inquisitors patrol the gates. The Inquisitors rest.")
    created = queue_repo.create_entity(CreateEntityDecision(
        surface="Inquisitors", entity_kind="faction",
        alias_surfaces=("Only the Inquisitors",),  # evidenced suggestion
        manual_aliases=("Inquisition",),           # owner declaration
        idempotency_key="create-mixed"))
    entity = created.entity_id
    assert entity is not None
    repo = repository()
    # Profile save drops "Inquisition" (a mistaken declaration) without
    # duplicating the evidence-based queue alias as a profile row.
    repo.update(profile(entity, version=0, canonical_name="Inquisitors",
                        aliases=["Only the Inquisitors"]))
    with psycopg.connect(TEST_DSN) as connection:
        remaining = connection.execute(
            "SELECT normalized_alias, alias_kind FROM entity_aliases "
            "WHERE entity_id = %s ORDER BY normalized_alias", (entity,)).fetchall()
    assert remaining == [("only the inquisitors", "queue_decision")]
    # Clearing the profile's aliases removes only owner-named rows; the
    # evidence-based queue alias keeps its own lifecycle (queue revert).
    repo.update(profile(entity, version=1, canonical_name="Inquisitors",
                        aliases=[]))
    with psycopg.connect(TEST_DSN) as connection:
        after = connection.execute(
            "SELECT normalized_alias FROM entity_aliases WHERE entity_id = %s",
            (entity,)).fetchall()
    assert after == [("only the inquisitors",)]


def test_faction_base_location_and_members_shape():
    faction = seed_identity("Carpet Rollers", kind="faction")
    ruhrogue = seed_identity("Ruhrogue", kind="pc")
    coreferra = seed_identity("Coreferra")
    seed_linked_claim(faction, "The Council recognized the party as the Carpet Rollers.")
    with psycopg.connect(TEST_DSN) as connection:
        connection.execute(
            "INSERT INTO claim_related_entities (claim_id, entity_id, relation_kind) "
            "SELECT c.id, %s, 'derived_mention' FROM claims c "
            "WHERE c.subject_entity_id = %s LIMIT 1", (ruhrogue, faction))
        connection.execute(
            "INSERT INTO claim_related_entities (claim_id, entity_id, relation_kind) "
            "SELECT c.id, %s, 'derived_mention' FROM claims c "
            "WHERE c.subject_entity_id = %s LIMIT 1", (coreferra, faction))
    repo = repository()
    repo.update(profile(faction, canonical_name="Carpet Rollers", status="active",
                        base_location="The manor in Unity"))
    stored = repo.get(faction)
    assert stored.base_location == "The manor in Unity"
    from dm_assistant_core.adapters.postgres.library_entries import (
        PostgresLibraryEntryRepository,
    )
    entry = PostgresLibraryEntryRepository(PostgresDatabase(TEST_DSN)).get(faction)
    # No explicit roster exists, so co-mention associations land in `related` —
    # display context only, never removable roster members.
    assert entry.members == ()
    assert set(entry.related) == {"Coreferra", "Ruhrogue"}
