"""Controlled vocabularies for template fields (TKT-0129)."""

import asyncio
from uuid import uuid4

import httpx
import pytest

from dm_assistant_core.api.app import create_app
from dm_assistant_core.application.template_vocabularies import (
    TemplateVocabularyService,
    VocabularyCommand,
)
from dm_assistant_core.config import Settings


class MemoryRepository:
    def __init__(self) -> None:
        self.rows: dict[str, dict[str, bool]] = {}

    def load(self, vocabulary):
        return self.rows.get(vocabulary, {})

    def record(self, receipt, retired):
        self.rows.setdefault(receipt.vocabulary, {})[receipt.value] = retired


def test_seeds_merge_with_overrides_and_sort() -> None:
    service = TemplateVocabularyService(MemoryRepository())
    values = service.values("location_type")
    assert any(v.value == "city-state" and not v.retired for v in values)
    assert values == sorted(values, key=lambda v: v.value.casefold())


def test_add_and_retire_are_receipted() -> None:
    repository = MemoryRepository()
    service = TemplateVocabularyService(repository)
    receipt = service.change("race", VocabularyCommand(action="add", value="goliath"))
    assert receipt.action == "add"
    assert any(v.value == "goliath" and not v.retired for v in service.values("race"))
    retire = service.change("race", VocabularyCommand(action="retire", value="goliath"))
    assert retire.action == "retire"
    assert any(v.value == "goliath" and v.retired for v in service.values("race"))
    # Retired values stay in the list (rendering) but flagged.
    assert repository.load("race") == {"goliath": True}


def test_unknown_vocabulary_and_action_rejected() -> None:
    service = TemplateVocabularyService(MemoryRepository())
    with pytest.raises(ValueError, match="unknown template vocabulary"):
        service.values("roles")  # roles are relations, never a vocabulary
    with pytest.raises(ValueError, match="unknown template vocabulary"):
        service.change("mood", VocabularyCommand(action="add", value="grim"))
    with pytest.raises(ValueError, match="add or retire"):
        service.change("race", VocabularyCommand(action="delete", value="x"))


def test_vocabulary_api_is_dm_only_and_round_trips() -> None:
    service = TemplateVocabularyService(MemoryRepository())
    app = create_app(Settings(
        database_url="postgresql://campaign:secret@localhost:5432/campaign",
        run_migrations=False,
    ), template_vocabularies=service)

    async def requests() -> tuple[httpx.Response, httpx.Response, httpx.Response, httpx.Response]:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            forbidden = await client.get("/template-vocabularies/race?requester_role=party")
            listed = await client.get("/template-vocabularies/race?requester_role=dm")
            added = await client.post(
                "/template-vocabularies/race?requester_role=dm",
                json={"action": "add", "value": "goliath"})
            unknown = await client.get("/template-vocabularies/roles?requester_role=dm")
            return forbidden, listed, added, unknown

    forbidden, listed, added, unknown = asyncio.run(requests())
    assert forbidden.status_code == 403
    assert listed.status_code == 200
    assert any(item["value"] == "human" for item in listed.json())
    assert added.status_code == 200 and added.json()["action"] == "add"
    assert unknown.status_code == 422


def test_postgres_vocabularies_are_durable() -> None:
    import os

    import pytest

    dsn = os.getenv("CAMPAIGN_TEST_DATABASE_URL")
    if not dsn:
        pytest.skip("integration test requires CAMPAIGN_TEST_DATABASE_URL")
    from dm_assistant_core.adapters.postgres.database import PostgresDatabase
    from dm_assistant_core.adapters.postgres.migrate import run_migrations
    from dm_assistant_core.adapters.postgres.template_vocabularies import (
        PostgresTemplateVocabularyRepository,
    )

    run_migrations(dsn)
    service = TemplateVocabularyService(PostgresTemplateVocabularyRepository(PostgresDatabase(dsn)))
    service.change("location_type", VocabularyCommand(action="add", value="sea-realm"))
    assert any(v.value == "sea-realm" for v in service.values("location_type"))
    service.change("location_type", VocabularyCommand(action="retire", value="sea-realm"))
    assert any(v.value == "sea-realm" and v.retired for v in service.values("location_type"))
