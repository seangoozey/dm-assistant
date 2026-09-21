"""Editable, versioned AI prompts (TKT-0126)."""

import asyncio

import httpx
import pytest

from dm_assistant_core.api.app import create_app
from dm_assistant_core.application.prompt_configuration import (
    PromptConfigurationService,
    SetPromptOverride,
)
from dm_assistant_core.config import Settings


class MemoryRepository:
    def __init__(self) -> None:
        self.overrides: dict[str, tuple[str, str, object, object]] = {}
        self.receipts: list[object] = []

    def load(self, purpose):
        return self.overrides.get(purpose)

    def count_receipts(self, purpose):
        return sum(1 for r in self.receipts if getattr(r, "purpose", None) == purpose)

    def file_receipt(self, receipt, prompt_text):
        self.receipts.append(receipt)
        if prompt_text is None:
            self.overrides.pop(receipt.purpose, None)
        else:
            self.overrides[receipt.purpose] = (prompt_text, receipt.version_label, receipt.receipt_id, receipt.changed_at)

    def clear(self, purpose):
        self.overrides.pop(purpose, None)


def test_defaults_are_effective_until_overridden() -> None:
    service = PromptConfigurationService(MemoryRepository())
    effective = service.effective("prose")
    assert effective.overridden is False
    assert effective.version_label == "prose/default"
    assert "not a summarization" in effective.prompt_text


def test_override_versions_stamp_and_persist() -> None:
    repository = MemoryRepository()
    service = PromptConfigurationService(repository)
    receipt = service.set_override(SetPromptOverride(
        purpose="prose", prompt_text="Tighter voice rules. Respond as JSON: {\"draft\": \"...\"}"))
    assert receipt.version_label == "prose/local-1"
    effective = service.effective("prose")
    assert effective.overridden is True
    assert effective.prompt_text.startswith("Tighter voice rules")
    assert effective.version_label == "prose/local-1"
    # A second save increments the local version.
    second = service.set_override(SetPromptOverride(
        purpose="prose", prompt_text="Even tighter. Respond as JSON: {\"draft\": \"...\"}"))
    assert second.version_label == "prose/local-2"


def test_clear_restores_the_default_and_files_an_audit_receipt() -> None:
    repository = MemoryRepository()
    service = PromptConfigurationService(repository)
    service.set_override(SetPromptOverride(
        purpose="extraction", prompt_text="Custom extraction rules. Respond as JSON."))
    receipt = service.clear_override("extraction")
    assert receipt.action == "clear"
    assert service.effective("extraction").overridden is False
    assert service.effective("extraction").prompt_text != "Custom extraction rules."


def test_prose_override_must_keep_the_json_contract() -> None:
    with pytest.raises(ValueError, match="JSON response contract"):
        PromptConfigurationService(MemoryRepository()).set_override(
            SetPromptOverride(purpose="prose", prompt_text="No contract line."))


def test_unknown_purpose_is_rejected() -> None:
    with pytest.raises(ValueError, match="no editable prompt"):
        PromptConfigurationService(MemoryRepository()).effective("graph")
    with pytest.raises(ValueError, match="no editable prompt"):
        PromptConfigurationService(MemoryRepository()).set_override(
            SetPromptOverride(purpose="graph", prompt_text="x"))


def test_prompt_api_is_dm_only_and_edits_through_core() -> None:
    service = PromptConfigurationService(MemoryRepository())
    app = create_app(Settings(
        database_url="postgresql://campaign:secret@localhost:5432/campaign",
        run_migrations=False,
    ), prompt_configuration=service)

    async def requests() -> tuple[httpx.Response, httpx.Response, httpx.Response, httpx.Response]:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            forbidden = await client.get("/ai/prompts?requester_role=party")
            listing = await client.get("/ai/prompts?requester_role=dm")
            edit = await client.put(
                "/ai/prompts/prose?requester_role=dm",
                json={"purpose": "prose", "prompt_text": "Tuned. Respond as JSON: {\"draft\": \"...\"}"},
            )
            reset = await client.delete("/ai/prompts/prose?requester_role=dm")
            return forbidden, listing, edit, reset

    forbidden, listing, edit, reset = asyncio.run(requests())
    assert forbidden.status_code == 403
    body = listing.json()
    assert [item["purpose"] for item in body] == ["extraction", "prose"]
    assert body[1]["version_label"] == "prose/default"
    assert edit.status_code == 200 and edit.json()["version_label"] == "prose/local-1"
    assert reset.status_code == 200 and reset.json()["action"] == "clear"


def test_postgres_overrides_are_durable() -> None:
    import os

    import pytest

    dsn = os.getenv("CAMPAIGN_TEST_DATABASE_URL")
    if not dsn:
        pytest.skip("integration test requires CAMPAIGN_TEST_DATABASE_URL")
    from dm_assistant_core.adapters.postgres.database import PostgresDatabase
    from dm_assistant_core.adapters.postgres.migrate import run_migrations
    from dm_assistant_core.adapters.postgres.prompt_configuration import (
        PostgresPromptOverrideRepository,
    )

    run_migrations(dsn)
    service = PromptConfigurationService(PostgresPromptOverrideRepository(PostgresDatabase(dsn)))
    receipt = service.set_override(SetPromptOverride(
        purpose="prose", prompt_text="Durable rules. Respond as JSON: {\"draft\": \"...\"}"))
    effective = service.effective("prose")
    assert effective.overridden is True
    assert effective.version_label == receipt.version_label
    service.clear_override("prose")
    assert service.effective("prose").overridden is False
