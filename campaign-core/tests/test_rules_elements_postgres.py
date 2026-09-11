"""PostgreSQL integration tests for rules-element creation, mechanics, and card export.

These tests run against a disposable campaign_test database (see the CAMPAIGN_TEST_DATABASE_URL
environment variable). They prove the full chain: a rules-element entity is created through
the candidate-proposal path, its mechanics are persisted by the change-set trigger, and the
Markdown-card export produces a deterministic derived artifact with provenance.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from typing import Any

import httpx
import psycopg
import pytest

from dm_assistant_core.adapters.postgres.migrate import run_migrations
from dm_assistant_core.api.app import create_app
from dm_assistant_core.config import Settings

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


def app() -> Any:
    assert TEST_DSN is not None
    return create_app(Settings(database_url=TEST_DSN, environment="test", run_migrations=False))


def seed_spell_candidate(connection: Any) -> dict[str, Any]:
    """Seed a source document, revision, span, import run, and a rules-element candidate."""
    source_id = uuid.uuid4()
    revision_id = uuid.uuid4()
    span_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    run_id = uuid.uuid4()
    connection.execute(
        "INSERT INTO source_documents (id, source_kind, connector, original_path, first_seen_at) "
        "VALUES (%s, 'durable_evidence', 'test', 'lore/test-spell.md', now())",
        (source_id,),
    )
    connection.execute(
        "INSERT INTO source_revisions (id, source_document_id, content_hash, raw_content, "
        "source_time, importer_version, captured_at) VALUES (%s, %s, %s, %s, now(), 'test', now())",
        (revision_id, source_id, "a" * 64, b"# Force Bolt\nA bolt of force."),
    )
    connection.execute(
        "INSERT INTO source_spans (id, source_revision_id, section_path, start_offset, "
        "end_offset, excerpt_hash) VALUES (%s, %s, 'root', 0, 10, %s)",
        (span_id, revision_id, "b" * 64),
    )
    connection.execute(
        "INSERT INTO import_runs (id, connector, started_at, finished_at, importer_version, "
        "idempotency_key, status, receipt_json) VALUES (%s, 'test', now(), now(), 'test', %s, "
        "'completed', '{}'::jsonb)",
        (run_id, f"test-{run_id}"),
    )
    connection.execute(
        "INSERT INTO import_candidates (id, source_document_id, fingerprint, assertion_text, "
        "state, authority, visibility, is_conditional, predicts_subject_action, evidence_only, "
        "status, extractor_version, first_seen_import_run_id, created_at, updated_at) "
        "VALUES (%s, %s, %s, 'A bolt of force.', 'established', 'explicit_lore', 'dm_only', "
        "false, false, false, 'active', 'test', %s, now(), now())",
        (candidate_id, source_id, "c" * 64, run_id),
    )
    connection.execute(
        "INSERT INTO import_candidate_evidence (candidate_id, source_revision_id, section_path, "
        "start_offset, end_offset) VALUES (%s, %s, 'root', 0, 10)",
        (candidate_id, revision_id),
    )
    return {
        "id": candidate_id,
        "revision_id": revision_id,
        "state": "established",
        "authority": "explicit_lore",
        "visibility": "dm_only",
        "conditional": False,
        "predicts": False,
        "assertion": "A bolt of force.",
    }


def entity_item(
    selected: dict[str, Any],
    target_id: uuid.UUID,
    *,
    entity_kind: str = "rules_element",
    mechanics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "mutation_kind": "create_entity",
        "candidate_id": str(selected["id"]),
        "evidence_revision_id": str(selected["revision_id"]),
        "target_id": str(target_id),
        "entity_type": entity_kind,
        "canonical_name": "Force Bolt",
        "tags": [],
        **({"rules_element_mechanics": mechanics} if mechanics else {}),
    }


async def approve_and_apply(
    client: httpx.AsyncClient, proposal: dict[str, Any], key: str
) -> dict[str, Any]:
    item_ids = [item["item_id"] for item in proposal["items"]]
    approved = await client.post(
        f"/imports/proposals/{proposal['proposal_id']}/approvals?requester_role=dm",
        json={
            "reviewed_version": proposal["version_number"],
            "content_hash": proposal["content_hash"],
            "item_ids": item_ids,
            "idempotency_key": key,
        },
    )
    assert approved.status_code == 200, approved.text
    approval = approved.json()
    applied = await client.post(
        f"/change-sets/{approval['change_set_id']}/apply",
        json={
            "reviewed_version": proposal["version_number"],
            "approval_id": approval["approval_id"],
            "content_hash": proposal["content_hash"],
        },
    )
    assert applied.status_code == 200, applied.text
    return applied.json()


def test_rules_element_creation_persists_mechanics_and_export_is_deterministic() -> None:
    spell_mechanics = {
        "rules_kind": "spell",
        "summary": "A bolt of arcane force.",
        "mechanics": {"school": "Evocation", "level": 1, "description": "Strikes a target."},
    }

    entity_id = uuid.uuid4()

    async def exercise() -> dict[str, Any]:
        with psycopg.connect(TEST_DSN) as connection:  # type: ignore[arg-type]
            selected = seed_spell_candidate(connection)
        async with (
            httpx.ASGITransport(app=app()) as transport,
            httpx.AsyncClient(transport=transport, base_url="http://test") as client,
        ):
            created = await client.post(
                "/imports/proposals?requester_role=dm",
                json={"items": [entity_item(selected, entity_id, mechanics=spell_mechanics)]},
            )
            assert created.status_code == 200, created.text
            await approve_and_apply(client, created.json(), "rules-element-create")

            # Export the card twice; the second must be an idempotent replay.
            first = await client.post(f"/entities/{entity_id}/rules-card")
            assert first.status_code == 200, first.text
            second = await client.post(f"/entities/{entity_id}/rules-card")
            assert second.status_code == 200, second.text
            return {"first": first.json(), "second": second.json()}

    result = asyncio.run(exercise())
    first, second = result["first"], result["second"]

    # The export produces a deterministic artifact.
    assert first["content_hash"] == second["content_hash"]
    assert first["kind"] == "rules_card"
    assert first["format_version"] == "markdown-card/1"
    assert first["source_entity_id"] == str(entity_id)
    assert "Force Bolt" in first["content"]
    assert "Evocation" in first["content"]
    # The second export is an idempotent replay.
    assert second["idempotent_replay"] is True
    assert second["artifact_id"] == first["artifact_id"]

    # Mechanics were persisted by the change-set trigger.
    with psycopg.connect(TEST_DSN) as connection:  # type: ignore[arg-type]
        row = connection.execute(
            "SELECT rules_kind, summary, mechanics_jsonb->>'school' "
            "FROM rules_element_mechanics WHERE entity_id = %s",
            (entity_id,),
        ).fetchone()
    assert row is not None
    assert row[0] == "spell"
    assert row[1] == "A bolt of arcane force."
    assert row[2] == "Evocation"
