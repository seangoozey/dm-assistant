"""Controlled AI configuration behavior."""

import asyncio

import httpx
import pytest

from dm_assistant_core.api.app import create_app
from dm_assistant_core.application.ai_configuration import (
    ActivationReceipt,
    AIConfigurationService,
    EXTRACTION_PURPOSE,
    PROSE_PURPOSE,
)
from dm_assistant_core.config import Settings


class MemoryRepository:
    def __init__(self) -> None:
        self.receipts: list[ActivationReceipt] = []

    def latest_by_purpose(self) -> dict[str, ActivationReceipt]:
        latest: dict[str, ActivationReceipt] = {}
        for receipt in self.receipts:
            latest[receipt.purpose] = receipt
        return latest

    def activate(self, receipt: ActivationReceipt) -> None:
        self.receipts.append(receipt)


def test_deepseek_chat_is_the_default_extraction_profile() -> None:
    snapshot = AIConfigurationService(MemoryRepository()).snapshot()
    assert snapshot.active_profile_by_purpose[EXTRACTION_PURPOSE] == "deepseek-chat"
    extraction = next(p for p in snapshot.purposes if p.key == EXTRACTION_PURPOSE)
    assert extraction.prompt_version and extraction.prompt_text
    assert (
        next(p for p in snapshot.profiles if p.key == "deepseek-chat").model_slug
        == "deepseek/deepseek-chat"
    )


def test_prose_purpose_has_its_first_candidate_model() -> None:
    snapshot = AIConfigurationService(MemoryRepository()).snapshot()
    prose_profiles = [p for p in snapshot.profiles if p.purpose == PROSE_PURPOSE]
    assert [p.key for p in prose_profiles] == ["deepseek-v4-flash"]
    assert prose_profiles[0].selectable
    assert prose_profiles[0].model_slug == "deepseek/deepseek-v4-flash-0731"
    # Listed is not chosen: until prose is activated it has no active profile.
    assert PROSE_PURPOSE not in snapshot.active_profile_by_purpose
    with pytest.raises(ValueError, match="no AI model profile is configured"):
        AIConfigurationService(MemoryRepository()).active_profile(PROSE_PURPOSE)
    service = AIConfigurationService(MemoryRepository())
    receipt = service.activate(PROSE_PURPOSE, "deepseek-v4-flash")
    assert receipt.purpose == PROSE_PURPOSE
    assert service.snapshot().active_profile_by_purpose[PROSE_PURPOSE] == "deepseek-v4-flash"
    # Prose activation must not disturb the extraction path.
    assert service.snapshot().active_profile_by_purpose[EXTRACTION_PURPOSE] == "deepseek-chat"


def test_activation_is_validated_and_durable_per_purpose() -> None:
    repository = MemoryRepository()
    service = AIConfigurationService(repository)
    receipt = service.activate(EXTRACTION_PURPOSE, "deepseek-chat")
    assert receipt.purpose == EXTRACTION_PURPOSE
    assert repository.latest_by_purpose()[EXTRACTION_PURPOSE] == receipt
    snapshot = service.snapshot()
    assert snapshot.last_activation_by_purpose[EXTRACTION_PURPOSE] == receipt
    assert snapshot.active_profile_by_purpose[EXTRACTION_PURPOSE] == "deepseek-chat"


@pytest.mark.parametrize("key", ["arbitrary/provider", "gpt5-nano-evaluated"])
def test_uncontrolled_or_unsuitable_profiles_cannot_be_activated(key: str) -> None:
    with pytest.raises(ValueError, match="non-selectable"):
        AIConfigurationService(MemoryRepository()).activate(EXTRACTION_PURPOSE, key)


def test_extraction_profile_cannot_be_activated_for_prose() -> None:
    with pytest.raises(ValueError, match="non-selectable"):
        AIConfigurationService(MemoryRepository()).activate(PROSE_PURPOSE, "deepseek-chat")


def test_unknown_purpose_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown AI model purpose"):
        AIConfigurationService(MemoryRepository()).activate("graph", "deepseek-chat")


def test_configuration_api_is_dm_only_and_activates_controlled_profile() -> None:
    service = AIConfigurationService(MemoryRepository())
    app = create_app(
        Settings(
            database_url="postgresql://campaign:secret@localhost:5432/campaign",
            run_migrations=False,
        ),
        ai_configuration=service,
    )

    async def requests() -> tuple[httpx.Response, httpx.Response, httpx.Response]:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            forbidden = await client.get("/ai/configuration?requester_role=party")
            snapshot = await client.get("/ai/configuration?requester_role=dm")
            activation = await client.post(
                "/ai/configuration/activate?requester_role=dm",
                json={"profile_key": "deepseek-chat"},
            )
            return forbidden, snapshot, activation

    forbidden, snapshot, activation = asyncio.run(requests())
    assert forbidden.status_code == 403
    body = snapshot.json()
    assert body["active_profile_by_purpose"]["extraction"] == "deepseek-chat"
    assert [purpose["key"] for purpose in body["purposes"]] == ["extraction", "prose", "promotion"]
    assert activation.status_code == 200
    receipt = activation.json()
    assert receipt["profile_key"] == "deepseek-chat"
    assert receipt["purpose"] == "extraction"


def test_postgres_activations_are_per_purpose() -> None:
    import os

    import pytest

    dsn = os.getenv("CAMPAIGN_TEST_DATABASE_URL")
    if not dsn:
        pytest.skip("integration test requires CAMPAIGN_TEST_DATABASE_URL")
    from uuid import uuid4

    from dm_assistant_core.adapters.postgres.ai_configuration import (
        PostgresAIConfigurationRepository,
    )
    from dm_assistant_core.adapters.postgres.database import PostgresDatabase
    from dm_assistant_core.adapters.postgres.migrate import run_migrations

    run_migrations(dsn)
    service = AIConfigurationService(PostgresAIConfigurationRepository(PostgresDatabase(dsn)))
    receipt = service.activate(EXTRACTION_PURPOSE, "deepseek-chat")
    assert receipt.purpose == EXTRACTION_PURPOSE
    snapshot = service.snapshot()
    assert snapshot.active_profile_by_purpose[EXTRACTION_PURPOSE] == "deepseek-chat"
    assert snapshot.last_activation_by_purpose[EXTRACTION_PURPOSE].receipt_id == receipt.receipt_id
    # Pre-0124 rows carry no purpose; the migration defaults them to extraction
    # without inventing receipts for purposes that never activated.
    assert PROSE_PURPOSE not in snapshot.active_profile_by_purpose
    assert uuid4()  # keep import used even if assertions above change
