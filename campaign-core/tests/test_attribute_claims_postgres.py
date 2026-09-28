"""Claim-backed attribute minting (TKT-0143): the dropdown mints dated claims,
changes supersede through the presumed-retcon rule."""

import os
from uuid import uuid4

import psycopg
import pytest

from dm_assistant_core.adapters.postgres.migrate import run_migrations

TEST_DSN = os.getenv("CAMPAIGN_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    TEST_DSN is None,
    reason="set CAMPAIGN_TEST_DATABASE_URL to a disposable PostgreSQL database",
)


def _seed_entity(connection, name: str, kind: str = "npc") -> str:
    workflow, change_set, entity = uuid4(), uuid4(), uuid4()
    connection.execute(
        "INSERT INTO workflow_sessions (id, kind, started_at) VALUES (%s, 'lore_entry', now())",
        (workflow,),
    )
    connection.execute(
        "INSERT INTO change_sets (id, idempotency_key, workflow_session_id, status, requested_at, applied_at) "
        "VALUES (%s, %s, %s, 'applied', now(), now())",
        (change_set, f"seed:{change_set}", workflow),
    )
    connection.execute(
        "INSERT INTO entities (id, entity_type, canonical_name, created_by_change_set_id, created_at, updated_at) "
        "VALUES (%s, %s, %s, %s, now(), now())",
        (entity, kind, name, change_set),
    )
    return str(entity)


def test_mint_change_and_presumed_retcon() -> None:
    assert TEST_DSN is not None
    run_migrations(TEST_DSN)
    with psycopg.connect(TEST_DSN) as connection:
        connection.execute(
            "TRUNCATE TABLE import_runs, source_documents, workflow_sessions, change_sets CASCADE"
        )
        entity = _seed_entity(connection, "Romulus")
        key = f"attr-test:{uuid4()}"

        first = connection.execute(
            "SELECT apply_attribute_claim(%s, 'race', 'High Elf', %s)",
            (entity, key),
        ).fetchone()[0]
        assert first["presumed_retcon"] is False
        first_claim = first["claim_id"]

        second = connection.execute(
            "SELECT apply_attribute_claim(%s, 'race', 'Orc', %s)",
            (entity, f"{key}:2"),
        ).fetchone()[0]
        assert second["presumed_retcon"] is True
        assert str(second["superseded_claim_id"]) == str(first_claim)

        replay = connection.execute(
            "SELECT apply_attribute_claim(%s, 'race', 'Orc', %s)",
            (entity, f"{key}:2"),
        ).fetchone()[0]
        assert replay["idempotent_replay"] is True

        binding = connection.execute(
            "SELECT claim_id FROM attribute_claim_bindings WHERE entity_id = %s AND field_name = 'race'",
            (entity,),
        ).fetchone()
        assert str(binding[0]) == str(second["claim_id"])

        supersession = connection.execute(
            "SELECT reason FROM claim_supersessions WHERE superseded_claim_id = %s",
            (first_claim,),
        ).fetchone()
        assert supersession[0] == "presumed retcon"

        claim = connection.execute(
            "SELECT assertion_text, predicate, state, authority FROM claims WHERE id = %s",
            (second["claim_id"],),
        ).fetchone()
        assert claim[0] == "race: Orc"
        assert claim[1] == "race"
        assert claim[2] == "established"
        assert claim[3] == "explicit_lore"


def test_observed_opposition_blocks() -> None:
    assert TEST_DSN is not None
    run_migrations(TEST_DSN)
    with psycopg.connect(TEST_DSN) as connection:
        connection.execute(
            "TRUNCATE TABLE import_runs, source_documents, workflow_sessions, change_sets CASCADE"
        )
        entity = _seed_entity(connection, "Blocked One")
        key = f"attr-block:{uuid4()}"
        connection.execute(
            "SELECT apply_attribute_claim(%s, 'status', 'active', %s)", (entity, key)
        ).fetchone()
        observed = uuid4()
        connection.execute(
            "INSERT INTO claims (id, subject_entity_id, assertion_text, state, authority, "
            "confidence, visibility, recorded_at, created_at, updated_at, "
            "observed_year, observed_month, observed_day) "
            "VALUES (%s, %s, 'status: dead at the table', 'observed', 'real_play', "
            "0.9500, 'dm_only', now(), now(), now(), 505, 11, 1)",
            (observed, entity),
        )
        try:
            connection.execute(
                "SELECT apply_attribute_claim(%s, 'status', 'active', %s)",
                (entity, f"{key}:2"),
            ).fetchone()
            raised = False
        except psycopg.DatabaseError as error:
            raised = error.sqlstate == "P0001" and "observed claim" in str(error)
        assert raised, "observed opposition must block the change"
