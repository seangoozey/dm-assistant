"""Postgres integration for the Promotion Pipeline commit chain (TKT-0136).

Exercises the real machinery end to end: derive reads claims, approve files
the description with statement candidates, proposes, approves, and applies
the change set in one user action — then replays idempotently.
"""

from __future__ import annotations

import os
from typing import Any
from uuid import uuid4

import psycopg
import pytest

from dm_assistant_core.adapters.postgres.migrate import run_migrations

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
            "TRUNCATE TABLE import_runs, source_documents, workflow_sessions, "
            "change_sets CASCADE"
        )


def _post(path: str, payload: dict) -> Any:
    """Run one request through the app with the async transport the API needs."""
    import asyncio

    import httpx

    from dm_assistant_core.api.app import create_app
    from dm_assistant_core.config import Settings

    assert TEST_DSN is not None
    application = create_app(
        Settings(database_url=TEST_DSN, environment="test", run_migrations=False)
    )

    async def send() -> Any:
        transport = httpx.ASGITransport(app=application)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            return await client.post(path, json=payload)

    return asyncio.run(send())


def _seed_entity(name: str) -> str:
    assert TEST_DSN is not None
    workflow, change_set, entity = uuid4(), uuid4(), uuid4()
    with psycopg.connect(TEST_DSN) as connection:
        connection.execute(
            "INSERT INTO workflow_sessions (id, kind, started_at) "
            "VALUES (%s, 'lore_entry', now())",
            (workflow,),
        )
        connection.execute(
            "INSERT INTO change_sets (id, idempotency_key, workflow_session_id, "
            "status, requested_at, applied_at) "
            "VALUES (%s, %s, %s, 'applied', now(), now())",
            (change_set, f"seed:{change_set}", workflow),
        )
        connection.execute(
            "INSERT INTO entities (id, entity_type, canonical_name, "
            "created_by_change_set_id, created_at, updated_at) "
            "VALUES (%s, 'location', %s, %s, now(), now())",
            (entity, name, change_set),
        )
    return str(entity)


def _approve_payload(entity_id: str, document_text: str, candidates: list, key: str) -> dict:
    return {
        "surface": "description",
        "entity_id": entity_id,
        "document_text": document_text,
        "statements": [
            {
                "span_start": candidate["span_start"],
                "span_end": candidate["span_end"],
                "assertion_text": candidate["assertion_text"],
                "state": "established",
                "included": candidate["included"],
            }
            for candidate in candidates
        ],
        "referenced_claim_ids": [],
        "idempotency_key": key,
    }


def test_promotion_commit_chain_and_idempotent_replay() -> None:
    entity_id = _seed_entity("Fleurite Treasury")
    document_text = (
        "The Treasury funds the rebellion. Its vault lies beneath the palace."
    )

    derived = _post(
        "/promotion/derive",
        {
            "surface": "description",
            "entity_id": entity_id,
            "document_text": document_text,
            "referenced_claim_ids": [],
        },
    )
    assert derived.status_code == 200, derived.text
    candidates = derived.json()["candidates"]
    assert [candidate["consequence"]["kind"] for candidate in candidates] == [
        "new_claim",
        "new_claim",
    ]
    assert all(candidate["included"] for candidate in candidates)

    key = f"promotion-test:{uuid4()}"
    approved = _post(
        "/promotion/approve", _approve_payload(entity_id, document_text, candidates, key)
    )
    assert approved.status_code == 200, approved.text
    receipt = approved.json()
    assert receipt["claims_committed"] == 2
    assert receipt["claim_ids"]

    replay = _post(
        "/promotion/approve", _approve_payload(entity_id, document_text, candidates, key)
    )
    assert replay.status_code == 200, replay.text
    assert replay.json()["claims_committed"] == 2
    assert replay.json()["idempotent_replay"] is True

    with psycopg.connect(TEST_DSN) as connection:
        rows = connection.execute(
            "SELECT assertion_text, state, authority, subject_entity_id "
            "FROM claims WHERE subject_entity_id = %s ORDER BY assertion_text",
            (entity_id,),
        ).fetchall()
    assert len(rows) == 2
    assert {row[1] for row in rows} == {"established"}
    assert {row[2] for row in rows} == {"explicit_lore"}


def test_derive_flags_restatement_of_referenced_claim() -> None:
    entity_id = _seed_entity("Vault of Ishi")
    claim_id = uuid4()
    with psycopg.connect(TEST_DSN) as connection:
        connection.execute(
            "INSERT INTO claims (id, subject_entity_id, assertion_text, state, "
            "authority, confidence, visibility, recorded_at, created_at, updated_at) "
            "VALUES (%s, %s, 'The vault of Ishi was sealed by the Fleurite king', "
            "'established', 'explicit_lore', 0.9500, 'dm_only', now(), now(), now())",
            (claim_id, entity_id),
        )
    derived = _post(
        "/promotion/derive",
        {
            "surface": "description",
            "entity_id": entity_id,
            "document_text": "The vault of Ishi was sealed by the Fleurite king.",
            "referenced_claim_ids": [str(claim_id)],
        },
    )
    assert derived.status_code == 200
    candidate = derived.json()["candidates"][0]
    assert candidate["consequence"]["kind"] == "reference"
    assert candidate["included"] is False
