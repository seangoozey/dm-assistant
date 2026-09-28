"""Assertion re-attribution (TKT-0099)."""

import asyncio
from uuid import uuid4

import httpx
import pytest

from dm_assistant_core.api.app import create_app
from dm_assistant_core.application.claim_reattribution import (
    ClaimReattributionService,
    ReattributeClaim,
)
from dm_assistant_core.config import Settings


class MemoryRepository:
    def __init__(self) -> None:
        self.subjects: dict = {}
        self.moves: list = []
        self.entity_names: dict = {}

    def claim_subject(self, claim_id):
        return self.subjects.get(claim_id)

    def claim_exists(self, claim_id):
        return claim_id in self.subjects

    def move(self, receipt, reason):
        self.subjects[receipt.claim_id] = receipt.new_entity_id
        self.moves.append((receipt, reason))

    def moved_from(self, entity_id):
        from dm_assistant_core.application.claim_reattribution import MovedAssertion
        return [
            (r.claim_id, "text", "established", r.new_entity_id,
             self.entity_names.get(r.new_entity_id, "?"), r.moved_at, reason)
            for r, reason in self.moves if r.old_entity_id == entity_id
        ]


def test_reattribute_changes_subject_and_records() -> None:
    repo = MemoryRepository()
    claim, old_owner, new_owner = uuid4(), uuid4(), uuid4()
    repo.subjects[claim] = old_owner
    service = ClaimReattributionService(repo)
    receipt = service.reattribute(ReattributeClaim(
        claim_id=claim, new_entity_id=new_owner, reason="belongs to the child"))
    assert receipt.old_entity_id == old_owner
    assert receipt.new_entity_id == new_owner
    assert repo.subjects[claim] == new_owner
    moved = service.moved_from(old_owner)
    assert len(moved) == 1
    assert moved[0].new_entity_id == new_owner


def test_reattribute_same_entity_rejected() -> None:
    repo = MemoryRepository()
    claim, owner = uuid4(), uuid4()
    repo.subjects[claim] = owner
    with pytest.raises(ValueError, match="already belongs"):
        ClaimReattributionService(repo).reattribute(
            ReattributeClaim(claim_id=claim, new_entity_id=owner, reason="x"))


def test_reattribute_missing_claim_rejected() -> None:
    with pytest.raises(ValueError, match="does not exist"):
        ClaimReattributionService(MemoryRepository()).reattribute(
            ReattributeClaim(claim_id=uuid4(), new_entity_id=uuid4(), reason="x"))


def test_reattribution_api_is_dm_only_and_round_trips() -> None:
    service = ClaimReattributionService(MemoryRepository())
    app = create_app(Settings(
        database_url="postgresql://campaign:secret@localhost:5432/campaign",
        run_migrations=False,
    ), claim_reattribution=service)
    claim, old_owner, new_owner = uuid4(), uuid4(), uuid4()
    service._repository.subjects[claim] = old_owner
    service._repository.entity_names[new_owner] = "Fleurite Treasury"

    async def requests():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            forbidden = await client.post(
                f"/claims/{claim}/reattribute?requester_role=party",
                json={"claim_id": str(claim), "new_entity_id": str(new_owner), "reason": "test"})
            ok = await client.post(
                f"/claims/{claim}/reattribute?requester_role=dm",
                json={"claim_id": str(claim), "new_entity_id": str(new_owner), "reason": "child entity"})
            moved = await client.get(
                f"/entities/{old_owner}/moved-assertions?requester_role=dm")
            return forbidden, ok, moved

    forbidden, ok, moved = asyncio.run(requests())
    assert forbidden.status_code == 403
    assert ok.status_code == 200 and ok.json()["old_entity_id"] == str(old_owner)
    assert moved.status_code == 200
    assert moved.json()[0]["new_entity_name"] == "Fleurite Treasury"


def test_postgres_reattribution_is_durable() -> None:
    import os
    import pytest

    dsn = os.getenv("CAMPAIGN_TEST_DATABASE_URL")
    if not dsn:
        pytest.skip("integration test requires CAMPAIGN_TEST_DATABASE_URL")
    from dm_assistant_core.adapters.postgres.database import PostgresDatabase
    from dm_assistant_core.adapters.postgres.migrate import run_migrations
    from dm_assistant_core.adapters.postgres.claim_reattribution import (
        PostgresClaimReattributionRepository,
    )

    run_migrations(dsn)
    # Seed a workflow, entity, claim, second entity
    import psycopg

    workflow, change_set = uuid4(), uuid4()
    old_entity, new_entity, claim = uuid4(), uuid4(), uuid4()
    with psycopg.connect(dsn) as conn:
        conn.execute("INSERT INTO workflow_sessions (id, kind, started_at) VALUES (%s, 'lore_entry', now())", (workflow,))
        conn.execute("INSERT INTO change_sets (id, idempotency_key, workflow_session_id, status, requested_at, applied_at) VALUES (%s, %s, %s, 'applied', now(), now())", (change_set, f"seed:{change_set}", workflow))
        conn.execute("INSERT INTO entities (id, entity_type, canonical_name, created_by_change_set_id, created_at, updated_at) VALUES (%s, 'location', 'Old Owner', %s, now(), now())", (old_entity, change_set))
        conn.execute("INSERT INTO entities (id, entity_type, canonical_name, created_by_change_set_id, created_at, updated_at) VALUES (%s, 'location', 'New Owner', %s, now(), now())", (new_entity, change_set))
        conn.execute(
            "INSERT INTO claims (id, subject_entity_id, assertion_text, state, authority, "
            "confidence, visibility, recorded_at, created_at, updated_at) "
            "VALUES (%s, %s, 'A test assertion.', 'established', 'explicit_lore', "
            "0.9500, 'dm_only', now(), now(), now())",
            (claim, old_entity))

    service = ClaimReattributionService(PostgresClaimReattributionRepository(PostgresDatabase(dsn)))
    receipt = service.reattribute(ReattributeClaim(
        claim_id=claim, new_entity_id=new_entity, reason="moved to child"))
    assert receipt.old_entity_id == old_entity
    moved = service.moved_from(old_entity)
    assert len(moved) == 1
    assert moved[0].new_entity_name == "New Owner"
    assert moved[0].assertion_text == "A test assertion."
