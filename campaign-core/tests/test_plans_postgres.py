from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime
from hashlib import sha256
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


def seed_entity(entity_kind: str, name: str) -> UUID:
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
            "VALUES (%s, %s, %s, %s, now(), now())",
            (entity_id, entity_kind, name, change_set_id),
        )
    return entity_id


def seed_evidence() -> UUID:
    assert TEST_DSN is not None
    document_id, revision_id, span_id = uuid4(), uuid4(), uuid4()
    raw = b"Sanitized player or DM-authored planning evidence."
    digest = sha256(raw).hexdigest()
    with psycopg.connect(TEST_DSN) as connection:
        connection.execute(
            "INSERT INTO source_documents "
            "(id, source_kind, connector, original_path, first_seen_at) "
            "VALUES (%s, 'markdown', 'test', %s, now())",
            (document_id, f"sanitized/{document_id}.md"),
        )
        connection.execute(
            "INSERT INTO source_revisions "
            "(id, source_document_id, content_hash, raw_content, importer_version, captured_at) "
            "VALUES (%s, %s, %s, %s, 'test', now())",
            (revision_id, document_id, digest, raw),
        )
        connection.execute(
            "INSERT INTO source_spans "
            "(id, source_revision_id, section_path, start_offset, end_offset, excerpt_hash) "
            "VALUES (%s, %s, 'Plan', 0, %s, %s)",
            (span_id, revision_id, len(raw), digest),
        )
    return span_id


def seed_observed_claim(subject_id: UUID, span_id: UUID) -> UUID:
    assert TEST_DSN is not None
    claim_id = uuid4()
    with psycopg.connect(TEST_DSN) as connection:
        connection.execute(
            """
            INSERT INTO claims (
                id, subject_entity_id, predicate, assertion_text, state, authority,
                confidence, visibility, recorded_at, observed_year, created_at, updated_at
            ) VALUES (
                %s, %s, 'followed_route', 'The route was followed during play.',
                'observed', 'real_play', 1, 'dm_only', now(), 505, now(), now()
            )
            """,
            (claim_id, subject_id),
        )
        connection.execute(
            "INSERT INTO claim_evidence (claim_id, source_span_id, evidence_role) "
            "VALUES (%s, %s, 'support')",
            (claim_id, span_id),
        )
    return claim_id


def application() -> Any:
    assert TEST_DSN is not None
    return create_app(Settings(database_url=TEST_DSN, environment="test", run_migrations=False))


async def approve_apply(
    client: httpx.AsyncClient, proposal: dict[str, Any], key: str
) -> dict[str, Any]:
    approved = await client.post(
        f"/plans/proposals/{proposal['proposal_id']}/approvals?requester_role=dm",
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
    return applied.json()


def test_named_in_world_plan_has_stable_identity_owner_relationship_and_evidence() -> None:
    assert TEST_DSN is not None
    owner_id = seed_entity("npc", "Sanitized Architect")
    span_id = seed_evidence()
    app = application()
    larger_plan_id, plan_id = uuid4(), uuid4()

    async def exercise() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            larger = await client.post(
                "/plans/proposals?requester_role=dm",
                json={
                    "target_id": str(larger_plan_id),
                    "plan_kind": "in_world_plan",
                    "canonical_name": "The Larger Migration",
                    "summary": "A separate plan to move the world.",
                    "owner_record_id": str(owner_id),
                    "evidence_source_span_ids": [str(span_id)],
                },
            )
            assert larger.status_code == 200, larger.text
            await approve_apply(client, larger.json(), "plan:larger")
            proposed = await client.post(
                "/plans/proposals?requester_role=dm",
                json={
                    "target_id": str(plan_id),
                    "plan_kind": "in_world_plan",
                    "canonical_name": "The Endless Dusk",
                    "summary": "An actor's plan to end mortality.",
                    "objective": "End mortality without establishing that it succeeds.",
                    "mechanism": "Redirect the world's lifeforce into a reflecting point.",
                    "intended_outcome": "Living beings remain animated indefinitely.",
                    "owner_record_id": str(owner_id),
                    "evidence_source_span_ids": [str(span_id)],
                    "related_plan_ids": [str(larger_plan_id)],
                },
            )
            assert proposed.status_code == 200, proposed.text
            proposal = proposed.json()
            receipt = await approve_apply(client, proposal, "plan:endless-dusk")
            fetched = await client.get(f"/plans/{plan_id}?requester_role=dm")
            assert fetched.status_code == 200, fetched.text
            projection = await client.get(f"/plans/{plan_id}/projection-context?requester_role=dm")
            assert projection.status_code == 200, projection.text
            return proposal, receipt, fetched.json(), projection.json()

    proposal, receipt, record, projection = asyncio.run(exercise())
    assert proposal["item"]["after"]["knowledge_boundary"] == "dm_authored_actor_intention"
    assert receipt["outcome"] == "applied"
    assert record["id"] == str(plan_id)
    assert record["record_type"] == "plan"
    assert record["owner_kind"] == "npc"
    assert record["related_plan_ids"] == [str(larger_plan_id)]
    assert record["evidence_source_span_ids"] == [str(span_id)]
    assert projection == {
        "source_plan_id": str(plan_id),
        "source_plan_name": "The Endless Dusk",
        "evidence_role": "projection",
        "establishes_outcome": False,
        "evidence_source_span_ids": [str(span_id)],
    }
    with psycopg.connect(TEST_DSN) as connection:
        stable = connection.execute(
            "SELECT p.id, r.id, kd.canonical_key FROM plans p "
            "JOIN records r ON r.id = p.id "
            "JOIN kind_definitions kd ON kd.id = p.plan_kind_id WHERE p.id = %s",
            (plan_id,),
        ).fetchone()
    assert stable == (plan_id, plan_id, "in_world_plan")


def test_player_plan_is_attributed_nonbinding_and_outcomes_need_observed_claims() -> None:
    pc_id = seed_entity("pc", "Sanitized PC")
    npc_id = seed_entity("npc", "Sanitized Witness")
    span_id = seed_evidence()
    observed_claim_id = seed_observed_claim(pc_id, span_id)
    app = application()
    plan_id = uuid4()

    async def exercise() -> tuple[dict[str, Any], httpx.Response, httpx.Response, dict[str, Any]]:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            common = {
                "plan_kind": "player_plan",
                "canonical_name": "Communicated route",
                "summary": "A player statement.",
                "player_attribution": "Sanitized Player",
                "communicated_at": datetime.now(UTC).isoformat(),
                "evidence_source_span_ids": [str(span_id)],
            }
            wrong_owner = await client.post(
                "/plans/proposals?requester_role=dm",
                json={**common, "target_id": str(uuid4()), "owner_record_id": str(npc_id)},
            )
            proposed = await client.post(
                "/plans/proposals?requester_role=dm",
                json={**common, "target_id": str(plan_id), "owner_record_id": str(pc_id)},
            )
            assert proposed.status_code == 200, proposed.text
            await approve_apply(client, proposed.json(), "plan:player")
            unsupported = await client.post(
                f"/plans/{plan_id}/lifecycle-proposals?requester_role=dm",
                json={"plan_id": str(plan_id), "lifecycle": "completed"},
            )
            transition = await client.post(
                f"/plans/{plan_id}/lifecycle-proposals?requester_role=dm",
                json={
                    "plan_id": str(plan_id),
                    "lifecycle": "completed",
                    "supporting_claim_ids": [str(observed_claim_id)],
                },
            )
            assert transition.status_code == 200, transition.text
            await approve_apply(client, transition.json(), "plan:player:completed")
            fetched = await client.get(f"/plans/{plan_id}?requester_role=dm")
            projection = await client.get(f"/plans/{plan_id}/projection-context?requester_role=dm")
            assert projection.status_code == 409
            return fetched.json(), wrong_owner, unsupported, transition.json()

    record, wrong_owner, unsupported, transition = asyncio.run(exercise())
    assert wrong_owner.status_code == 409
    assert unsupported.status_code == 422
    assert record["knowledge_boundary"] == "player_communicated_nonbinding"
    assert transition["item"]["before"]["lifecycle"] == "active"
    assert transition["item"]["after"]["supporting_claim_ids"] == [str(observed_claim_id)]
    assert record["lifecycle"] == "completed"
    assert record["supporting_claim_ids"] == [str(observed_claim_id)]
