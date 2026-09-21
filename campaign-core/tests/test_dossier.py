"""DM-curated dossier promotion (TKT-0121)."""

import asyncio
from uuid import uuid4

import httpx

from dm_assistant_core.api.app import create_app
from dm_assistant_core.application.dossier import DossierService
from dm_assistant_core.config import Settings


class MemoryRepository:
    def __init__(self) -> None:
        self.decisions: list[tuple] = []

    def latest_by_claim(self, entity_id):
        latest = {}
        for row in self.decisions:
            if row[0] == entity_id:
                latest[row[1]] = row[2]
        return latest

    def record(self, receipt):
        self.decisions.append((receipt.entity_id, receipt.claim_id, receipt.action))


def test_latest_decision_wins_and_view_is_entity_scoped() -> None:
    repository = MemoryRepository()
    service = DossierService(repository)
    entity, other = uuid4(), uuid4()
    claim_a, claim_b = uuid4(), uuid4()

    service.promote(entity, claim_a)
    service.promote(entity, claim_b)
    service.demote(entity, claim_a)
    service.promote(other, claim_a)  # another entity's decision stays there

    view = service.view(entity)
    assert set(view.promoted_claim_ids) == {claim_b}
    assert set(service.view(other).promoted_claim_ids) == {claim_a}


def test_dossier_api_is_dm_only_and_round_trips() -> None:
    service = DossierService(MemoryRepository())
    app = create_app(Settings(
        database_url="postgresql://campaign:secret@localhost:5432/campaign",
        run_migrations=False,
    ), dossier=service)
    entity, claim = uuid4(), uuid4()

    async def requests() -> tuple[httpx.Response, httpx.Response, httpx.Response, httpx.Response]:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            forbidden = await client.get(f"/entities/{entity}/dossier?requester_role=party")
            empty = await client.get(f"/entities/{entity}/dossier?requester_role=dm")
            promote = await client.post(
                f"/entities/{entity}/dossier/{claim}/promote?requester_role=dm")
            demote = await client.post(
                f"/entities/{entity}/dossier/{claim}/demote?requester_role=dm")
            return forbidden, empty, promote, demote

    forbidden, empty, promote, demote = asyncio.run(requests())
    assert forbidden.status_code == 403
    assert empty.json()["promoted_claim_ids"] == []
    assert promote.status_code == 200 and promote.json()["action"] == "promote"
    assert demote.status_code == 200 and demote.json()["action"] == "demote"


def test_postgres_dossier_decisions_are_durable() -> None:
    import os

    import pytest

    dsn = os.getenv("CAMPAIGN_TEST_DATABASE_URL")
    if not dsn:
        pytest.skip("integration test requires CAMPAIGN_TEST_DATABASE_URL")
    from dm_assistant_core.adapters.postgres.database import PostgresDatabase
    from dm_assistant_core.adapters.postgres.dossier import PostgresDossierRepository
    from dm_assistant_core.adapters.postgres.migrate import run_migrations

    run_migrations(dsn)
    service = DossierService(PostgresDossierRepository(PostgresDatabase(dsn)))
    entity, claim = uuid4(), uuid4()
    service.promote(entity, claim)
    assert set(service.view(entity).promoted_claim_ids) == {claim}
    service.demote(entity, claim)
    assert service.view(entity).promoted_claim_ids == ()
