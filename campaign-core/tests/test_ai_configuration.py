"""Controlled AI configuration behavior."""

import asyncio

import httpx
import pytest

from dm_assistant_core.api.app import create_app
from dm_assistant_core.application.ai_configuration import ActivationReceipt, AIConfigurationService
from dm_assistant_core.config import Settings


class MemoryRepository:
    def __init__(self) -> None:
        self.receipts: list[ActivationReceipt] = []

    def latest(self) -> ActivationReceipt | None:
        return self.receipts[-1] if self.receipts else None

    def activate(self, receipt: ActivationReceipt) -> None:
        self.receipts.append(receipt)


def test_deepseek_chat_is_the_default_profile() -> None:
    snapshot = AIConfigurationService(MemoryRepository()).snapshot()
    assert snapshot.active_profile_key == "deepseek-chat"
    assert snapshot.prompt_version and snapshot.prompt_text
    assert (
        next(p for p in snapshot.profiles if p.key == "deepseek-chat").model_slug
        == "deepseek/deepseek-chat"
    )


def test_activation_is_validated_and_durable() -> None:
    repository = MemoryRepository()
    service = AIConfigurationService(repository)
    receipt = service.activate("deepseek-chat")
    assert repository.latest() == receipt
    assert service.snapshot().last_activation == receipt


@pytest.mark.parametrize("key", ["arbitrary/provider", "gpt5-nano-evaluated"])
def test_uncontrolled_or_unsuitable_profiles_cannot_be_activated(key: str) -> None:
    with pytest.raises(ValueError, match="non-selectable"):
        AIConfigurationService(MemoryRepository()).activate(key)


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
    assert snapshot.json()["active_profile_key"] == "deepseek-chat"
    assert activation.status_code == 200
    assert activation.json()["profile_key"] == "deepseek-chat"
