from __future__ import annotations

import os
from hashlib import sha256
from uuid import uuid4

import psycopg
import pytest

from dm_assistant_core.adapters.postgres.database import PostgresDatabase
from dm_assistant_core.adapters.postgres.entity_lookup import PostgresEntityLookupRepository
from dm_assistant_core.adapters.postgres.migrate import run_migrations
from dm_assistant_core.adapters.postgres.pc_profiles import PostgresPCProfileRepository
from dm_assistant_core.application.pc_profiles import UpdatePCProfileCommand

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


def seed_character(name: str, *, with_claims: bool = True) -> tuple:
    """An NPC document whose claims evidence exactly one focal entity."""
    assert TEST_DSN is not None
    document_id, revision_id, entity_id = uuid4(), uuid4(), uuid4()
    workflow_id, change_set_id = uuid4(), uuid4()
    content = f"# {name}\n\n{name} exists."
    with psycopg.connect(TEST_DSN) as connection:
        connection.execute(
            "INSERT INTO source_documents (id, source_kind, connector, original_path, first_seen_at) "
            "VALUES (%s, 'markdown', 'markdown', %s, now())",
            (document_id, f"npcs/{name}.md"),
        )
        connection.execute(
            "INSERT INTO source_revisions (id, source_document_id, content_hash, raw_content, "
            "importer_version, captured_at, frontmatter_json) VALUES (%s, %s, %s, %s, 'test', now(), %s)",
            (revision_id, document_id, sha256(content.encode()).hexdigest(),
             content.encode(), psycopg.types.json.Jsonb({"type": "npc"})),
        )
        connection.execute(
            "INSERT INTO workflow_sessions (id, kind, started_at) VALUES (%s, 'lore_entry', now())",
            (workflow_id,),
        )
        connection.execute(
            "INSERT INTO change_sets (id, idempotency_key, workflow_session_id, status, "
            "requested_at, applied_at) VALUES (%s, %s, %s, 'applied', now(), now())",
            (change_set_id, f"seed:{change_set_id}", workflow_id),
        )
        connection.execute(
            "INSERT INTO entities (id, entity_type, canonical_name, created_by_change_set_id, "
            "created_at, updated_at) VALUES (%s, 'npc', %s, %s, now(), now())",
            (entity_id, name, change_set_id),
        )
        if with_claims:
            claim_id, span_id = uuid4(), uuid4()
            connection.execute(
                "INSERT INTO claims (id, subject_entity_id, assertion_text, state, authority, "
                "confidence, visibility, recorded_at, created_at, updated_at) "
                "VALUES (%s, %s, %s, 'established', 'explicit_lore', 1.0, 'dm_only', "
                "now(), now(), now())",
                (claim_id, entity_id, f"{name} exists."),
            )
            connection.execute(
                "INSERT INTO source_spans (id, source_revision_id, start_offset, end_offset, "
                "excerpt_hash) VALUES (%s, %s, 0, %s, %s)",
                (span_id, revision_id, len(content), sha256(content.encode()).hexdigest()),
            )
            connection.execute(
                "INSERT INTO claim_evidence (claim_id, source_span_id, evidence_role) "
                "VALUES (%s, %s, 'support')",
                (claim_id, span_id),
            )
    return document_id, revision_id, entity_id


def repository() -> PostgresPCProfileRepository:
    return PostgresPCProfileRepository(PostgresDatabase(TEST_DSN))


def save(document_id, revision_id, version, aliases, key):
    return repository().update(UpdatePCProfileCommand(
        document_id=document_id, source_revision_id=revision_id, version=version,
        canonical_name="Romulus", status="alive", aliases=aliases, background="",
        idempotency_key=key,
    ))


def managed_aliases(entity_id) -> dict:
    with psycopg.connect(TEST_DSN) as connection:
        rows = connection.execute(
            "SELECT normalized_alias, alias_kind FROM entity_aliases "
            "WHERE entity_id = %s AND namespace = 'profile'",
            (entity_id,),
        ).fetchall()
    return dict(rows)


def test_profile_save_applies_aliases_and_lookup_finds_them():
    document_id, revision_id, entity_id = seed_character("Romulus")
    receipt = save(document_id, revision_id, 0,
                   ["The Grand Inquisitor", "The Shadow"], "key-apply")
    assert receipt.alias_sync is not None
    assert receipt.alias_sync.applied == ("The Grand Inquisitor", "The Shadow")
    assert managed_aliases(entity_id) == {
        "the grand inquisitor": "profile_edit", "the shadow": "profile_edit"}
    matches = PostgresEntityLookupRepository(PostgresDatabase(TEST_DSN)).search(
        "The Grand Inquisitor", 5)
    assert [m.canonical_name for m in matches] == ["Romulus"]
    assert matches[0].match_kind == "alias"


def test_idempotent_replay_keeps_single_rows_and_receipt():
    document_id, revision_id, entity_id = seed_character("Romulus")
    first = save(document_id, revision_id, 0, ["The Grand Inquisitor"], "key-replay")
    replay = repository().update(UpdatePCProfileCommand(
        document_id=document_id, source_revision_id=revision_id, version=0,
        canonical_name="Romulus", status="alive", aliases=["The Grand Inquisitor"],
        background="", idempotency_key="key-replay",
    ))
    assert replay.idempotent_replay is True
    assert replay.receipt_id == first.receipt_id
    assert replay.alias_sync == first.alias_sync
    assert len(managed_aliases(entity_id)) == 1


def test_profile_removal_deletes_only_managed_namespace_rows():
    document_id, revision_id, entity_id = seed_character("Romulus")
    save(document_id, revision_id, 0, ["The Grand Inquisitor", "The Shadow"], "key-v1")
    second = save(document_id, revision_id, 1, ["The Grand Inquisitor"], "key-v2")
    assert second.version == 2
    assert second.alias_sync.removed == ("The Shadow",)
    assert managed_aliases(entity_id) == {"the grand inquisitor": "profile_edit"}


def test_alias_owned_by_another_identity_is_skipped():
    document_id, revision_id, entity_id = seed_character("Romulus")
    seed_character("Rhetus")
    receipt = save(document_id, revision_id, 0, ["Rhetus", "The Shadow"], "key-conflict")
    assert receipt.alias_sync.skipped_conflicting == ("Rhetus",)
    assert receipt.alias_sync.applied == ("The Shadow",)
    assert "rhetus" not in managed_aliases(entity_id)


def test_document_without_focal_entity_skips_sync():
    document_id, revision_id, _ = seed_character("Orphan", with_claims=False)
    receipt = save(document_id, revision_id, 0, ["The Grand Inquisitor"], "key-orphan")
    assert receipt.version == 1
    assert receipt.alias_sync is None
