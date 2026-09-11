from __future__ import annotations

import asyncio
import os
from typing import Any
from uuid import UUID, uuid4

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


def seed_entity(entity_kind: str = "location") -> UUID:
    assert TEST_DSN is not None
    entity_id, workflow_id, change_set_id = uuid4(), uuid4(), uuid4()
    with psycopg.connect(TEST_DSN) as connection:
        connection.execute(
            "INSERT INTO workflow_sessions (id, kind, started_at) VALUES (%s, 'lore_entry', now())",
            (workflow_id,),
        )
        connection.execute(
            "INSERT INTO change_sets "
            "(id, idempotency_key, workflow_session_id, status, requested_at, applied_at) "
            "VALUES (%s, %s, %s, 'applied', now(), now())",
            (change_set_id, f"seed:{change_set_id}", workflow_id),
        )
        connection.execute(
            "INSERT INTO entities "
            "(id, entity_type, canonical_name, created_by_change_set_id, created_at, updated_at) "
            "VALUES (%s, %s, 'Sanitized Subject', %s, now(), now())",
            (entity_id, entity_kind, change_set_id),
        )
        connection.execute(
            "INSERT INTO tags (id, name, normalized_name) VALUES (%s, 'settlement', 'settlement') "
            "ON CONFLICT (normalized_name) DO NOTHING",
            (uuid4(),),
        )
        connection.execute(
            "INSERT INTO entity_tag_assignments "
            "(id, entity_id, tag_id, assigned_by_change_set_id, assigned_at) "
            "SELECT %s, %s, id, %s, now() FROM tags WHERE normalized_name = 'settlement'",
            (uuid4(), entity_id, change_set_id),
        )
    return entity_id


def app() -> Any:
    assert TEST_DSN is not None
    return create_app(Settings(database_url=TEST_DSN, environment="test", run_migrations=False))


async def propose_approve_apply(
    client: httpx.AsyncClient,
    entity_id: UUID,
    *,
    entity_kind: str,
    tags: list[str],
    key: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    proposed = await client.post(
        f"/entities/{entity_id}/metadata-proposals?requester_role=dm",
        json={"entity_kind": entity_kind, "tags": tags},
    )
    assert proposed.status_code == 200, proposed.text
    proposal = proposed.json()
    approved = await client.post(
        f"/entities/metadata-proposals/{proposal['proposal_id']}/approvals?requester_role=dm",
        json={
            "reviewed_version": proposal["version_number"],
            "content_hash": proposal["content_hash"],
            "item_ids": [proposal["item"]["item_id"]],
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
    return proposal, applied.json()


def test_entity_kind_and_tags_change_atomically_without_changing_record_identity() -> None:
    assert TEST_DSN is not None
    entity_id = seed_entity()
    application = app()

    async def exercise() -> tuple[dict[str, Any], dict[str, Any]]:
        transport = httpx.ASGITransport(app=application)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await propose_approve_apply(
                client,
                entity_id,
                entity_kind="worldbuilding",
                tags=["Cosmology", "Mythology"],
                key="metadata:atomic",
            )

    proposal, receipt = asyncio.run(exercise())
    assert proposal["item"]["before"]["entity_kind"] == "location"
    assert proposal["item"]["before"]["tags"] == ["settlement"]
    assert proposal["item"]["after"]["entity_kind"] == "worldbuilding"
    assert proposal["item"]["after"]["tags"] == ["cosmology", "mythology"]
    assert receipt["outcome"] == "applied"

    with psycopg.connect(TEST_DSN) as connection:
        entity = connection.execute(
            "SELECT e.id, e.entity_type, kd.canonical_key FROM entities e "
            "JOIN records r ON r.id = e.id "
            "JOIN kind_definitions kd ON kd.id = e.entity_kind_id WHERE e.id = %s",
            (entity_id,),
        ).fetchone()
        current_tags = connection.execute(
            "SELECT normalized_name FROM current_entity_tags WHERE entity_id = %s "
            "ORDER BY normalized_name",
            (entity_id,),
        ).fetchall()
        removed = connection.execute(
            "SELECT count(*) FROM entity_tag_assignments "
            "WHERE entity_id = %s AND removed_at IS NOT NULL",
            (entity_id,),
        ).fetchone()
    assert entity == (entity_id, "worldbuilding", "worldbuilding")
    assert current_tags == [("cosmology",), ("mythology",)]
    assert removed == (1,)


def test_stale_metadata_and_pc_reclassification_fail_closed() -> None:
    entity_id = seed_entity()
    pc_id = seed_entity("pc")
    application = app()

    async def exercise() -> tuple[httpx.Response, httpx.Response]:
        transport = httpx.ASGITransport(app=application)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            first = await client.post(
                f"/entities/{entity_id}/metadata-proposals?requester_role=dm",
                json={"entity_kind": "location", "tags": ["region"]},
            )
            stale = await client.post(
                f"/entities/{entity_id}/metadata-proposals?requester_role=dm",
                json={"entity_kind": "location", "tags": ["country"]},
            )
            assert first.status_code == stale.status_code == 200
            first_payload = first.json()
            stale_payload = stale.json()
            await propose_approve_apply(
                client,
                entity_id,
                entity_kind="location",
                tags=["region"],
                key="metadata:first",
            )
            stale_approval = await client.post(
                f"/entities/metadata-proposals/{stale_payload['proposal_id']}/approvals"
                "?requester_role=dm",
                json={
                    "reviewed_version": 1,
                    "content_hash": stale_payload["content_hash"],
                    "item_ids": [stale_payload["item"]["item_id"]],
                    "idempotency_key": "metadata:stale",
                },
            )
            assert stale_approval.status_code == 200
            approval = stale_approval.json()
            stale_apply = await client.post(
                f"/change-sets/{approval['change_set_id']}/apply",
                json={
                    "reviewed_version": 1,
                    "approval_id": approval["approval_id"],
                    "content_hash": stale_payload["content_hash"],
                },
            )
            pc_change = await client.post(
                f"/entities/{pc_id}/metadata-proposals?requester_role=dm",
                json={"entity_kind": "npc", "tags": []},
            )
            assert first_payload["item"]["before"] == stale_payload["item"]["before"]
            return stale_apply, pc_change

    stale_apply, pc_change = asyncio.run(exercise())
    assert stale_apply.status_code == 409
    assert "changed after" in stale_apply.json()["detail"]
    assert pc_change.status_code == 409
    assert "agency kinds" in pc_change.json()["detail"]


def test_kind_evolution_events_preserve_stable_ids_and_historical_coordinates() -> None:
    assert TEST_DSN is not None
    entity_id = seed_entity("worldbuilding")
    application = app()

    async def propose() -> dict[str, Any]:
        transport = httpx.ASGITransport(app=application)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/entities/{entity_id}/metadata-proposals?requester_role=dm",
                json={"entity_kind": "worldbuilding", "tags": ["cosmology"]},
            )
            assert response.status_code == 200, response.text
            return response.json()

    proposal = asyncio.run(propose())
    with psycopg.connect(TEST_DSN) as connection:
        kind_id = connection.execute(
            "SELECT entity_kind_id FROM entities WHERE id = %s", (entity_id,)
        ).fetchone()[0]
        event_id = uuid4()
        connection.execute(
            "INSERT INTO kind_aliases (namespace, alias_key, kind_id) "
            "VALUES ('entity', 'worldbuilding', %s)",
            (kind_id,),
        )
        connection.execute(
            "INSERT INTO kind_evolution_events "
            "(id, operation, reason, migration_version) "
            "VALUES (%s, 'rename', 'Sanitized rename proof', 'test-only')",
            (event_id,),
        )
        connection.execute(
            "INSERT INTO kind_evolution_members (event_id, kind_id, role) "
            "VALUES (%s, %s, 'source'), (%s, %s, 'target')",
            (event_id, kind_id, event_id, kind_id),
        )
        connection.execute(
            "UPDATE kind_definitions SET canonical_key = 'setting_concept' WHERE id = %s",
            (kind_id,),
        )
        stable = connection.execute(
            "SELECT e.id, e.entity_kind_id, kd.canonical_key FROM entities e "
            "JOIN kind_definitions kd ON kd.id = e.entity_kind_id WHERE e.id = %s",
            (entity_id,),
        ).fetchone()
        historical = connection.execute(
            "SELECT after_json->>'entity_kind' FROM proposal_items WHERE id = %s",
            (proposal["item"]["item_id"],),
        ).fetchone()
        alias = connection.execute(
            "SELECT kind_id FROM kind_aliases "
            "WHERE namespace = 'entity' AND alias_key = 'worldbuilding'",
        ).fetchone()
        members = connection.execute(
            "SELECT role FROM kind_evolution_members WHERE event_id = %s ORDER BY role",
            (event_id,),
        ).fetchall()
        other_kinds = dict(
            connection.execute(
                "SELECT canonical_key, id FROM kind_definitions "
                "WHERE namespace = 'entity' AND canonical_key IN ('event', 'faction', 'location')"
            ).fetchall()
        )
        merge_id, split_id, deprecate_id = uuid4(), uuid4(), uuid4()
        connection.execute(
            "INSERT INTO kind_evolution_events "
            "(id, operation, reason, migration_version) VALUES "
            "(%s, 'merge', 'Sanitized merge proof', 'test-only'), "
            "(%s, 'split', 'Sanitized split proof', 'test-only'), "
            "(%s, 'deprecate', 'Sanitized deprecation proof', 'test-only')",
            (merge_id, split_id, deprecate_id),
        )
        connection.execute(
            "INSERT INTO kind_evolution_members (event_id, kind_id, role) VALUES "
            "(%s, %s, 'source'), (%s, %s, 'source'), (%s, %s, 'target'), "
            "(%s, %s, 'source'), (%s, %s, 'target'), (%s, %s, 'target'), "
            "(%s, %s, 'source'), (%s, %s, 'target')",
            (
                merge_id,
                other_kinds["event"],
                merge_id,
                kind_id,
                merge_id,
                other_kinds["location"],
                split_id,
                other_kinds["faction"],
                split_id,
                other_kinds["event"],
                split_id,
                other_kinds["location"],
                deprecate_id,
                other_kinds["event"],
                deprecate_id,
                other_kinds["location"],
            ),
        )
        connection.execute(
            "UPDATE kind_definitions SET status = 'deprecated', replacement_kind_id = %s "
            "WHERE id = %s",
            (other_kinds["location"], other_kinds["event"]),
        )
        evolution_shapes = dict(
            connection.execute(
                "SELECT kee.operation, string_agg(kem.role, ',' ORDER BY kem.role) "
                "FROM kind_evolution_events kee JOIN kind_evolution_members kem "
                "ON kem.event_id = kee.id WHERE kee.id = ANY(%s) GROUP BY kee.operation",
                ([merge_id, split_id, deprecate_id],),
            ).fetchall()
        )
        deprecated = connection.execute(
            "SELECT status::text, replacement_kind_id FROM kind_definitions WHERE id = %s",
            (other_kinds["event"],),
        ).fetchone()
        connection.rollback()

    assert stable == (entity_id, kind_id, "setting_concept")
    assert historical == ("worldbuilding",)
    assert alias == (kind_id,)
    assert members == [("source",), ("target",)]
    assert evolution_shapes == {
        "deprecate": "source,target",
        "merge": "source,source,target",
        "split": "source,target,target",
    }
    assert deprecated == ("deprecated", other_kinds["location"])
