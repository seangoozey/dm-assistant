"""AI prose drafting contract (TKT-0120)."""

import asyncio
from json import dumps

import httpx
import pytest

from dm_assistant_core.application.prose_drafting import (
    ProseDraftCommand,
    ProseDraftError,
    ProseDraftingService,
    ProseHarness,
    ProseMaterialItem,
)
from dm_assistant_core.api.app import create_app
from dm_assistant_core.config import Settings


class ScriptedClient:
    """Provider fixture returning queued responses, recording prompts."""

    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self.prompts: list[str] = []

    def quick_complete(self, *, system: str, user: str, response_schema=None):
        self.prompts.append(user)
        return ScriptedResponse(self._responses.pop(0))


class ScriptedResponse:
    def __init__(self, content: str, prompt_tokens: int = 120, completion_tokens: int = 340) -> None:
        self.content = content
        class _Usage:
            pass
        self.usage = _Usage()
        self.usage.prompt_tokens = prompt_tokens  # type: ignore[attr-defined]
        self.usage.completion_tokens = completion_tokens  # type: ignore[attr-defined]


def command(**overrides):
    base = dict(
        subject="Fleurite",
        subject_kind="location",
        material=(
            ProseMaterialItem(key="claim:aaa1", kind="claim", state="established",
                              text="Fleurite is a region and city-state within Illisan."),
            ProseMaterialItem(key="claim:bbb2", kind="claim", state="prepared",
                              text="Provide a runnable operations sheet for a dungeon incursion."),
            ProseMaterialItem(key="relation:ccc3", kind="relation",
                              text="Ruh is a member of the White Cloaks."),
        ),
        idempotency_key="prose:test",
    )
    base.update(overrides)
    return ProseDraftCommand(**base)


def test_draft_returns_validated_citations_in_first_use_order():
    client = ScriptedClient([dumps({"draft": "Fleurite is a city-state within Illisan [1]. Ruh serves among the White Cloaks [3][1]."})])
    result = ProseDraftingService(ProseHarness(client), model_slug="deepseek/deepseek-v4-flash-0731").draft(command())
    assert result.cited_keys == ("claim:aaa1", "relation:ccc3")
    assert result.model_slug == "deepseek/deepseek-v4-flash-0731"
    assert result.prompt_tokens == 120 and result.completion_tokens == 340


def test_material_carries_truth_states_so_prep_stays_visible_to_the_model():
    client = ScriptedClient([dumps({"draft": "Text [1]."})])
    ProseDraftingService(ProseHarness(client), model_slug="m").draft(command())
    assert "(established) Fleurite is a region" in client.prompts[0]
    assert "(prepared) Provide a runnable operations sheet" in client.prompts[0]


def test_out_of_range_citation_is_retried_then_accepted():
    bad = dumps({"draft": "Fleurite is mighty [9]."})
    good = dumps({"draft": "Fleurite is a city-state within Illisan [1]."}) 
    client = ScriptedClient([bad, good])
    result = ProseDraftingService(ProseHarness(client), model_slug="m").draft(command())
    assert result.cited_keys == ("claim:aaa1",)
    assert "cited material numbers that do not exist: [9]" in client.prompts[1]


def test_uncited_draft_is_refused_after_retries():
    client = ScriptedClient([dumps({"draft": "Fleurite is a city-state."}), dumps({"draft": "Still no citations."})])
    with pytest.raises(ProseDraftError, match="cited no material"):
        ProseDraftingService(ProseHarness(client), model_slug="m").draft(command())


def test_non_json_response_is_refused_after_retries():
    client = ScriptedClient(["not json at all", "still not json"])
    with pytest.raises(ProseDraftError, match="not JSON"):
        ProseDraftingService(ProseHarness(client), model_slug="m").draft(command())


def test_provider_faults_surface_as_readable_draft_failures():
    class FailingClient:
        def quick_complete(self, *, system, user, response_schema=None):
            raise TimeoutError("a request exceeded the configured timeout after all retries")

    with pytest.raises(ProseDraftError, match="prose provider failed.*exceeded the configured timeout"):
        ProseDraftingService(ProseHarness(FailingClient()), model_slug="m").draft(command())


def test_prose_api_is_dm_only_and_reports_the_active_profile_gap():
    app = create_app(Settings(
        database_url="postgresql://campaign:secret@localhost:5432/campaign",
        run_migrations=False,
    ))

    async def requests() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post(
                "/prose/draft?requester_role=party",
                json={"subject": "Fleurite", "subject_kind": "location",
                      "material": [{"key": "k1", "kind": "claim", "text": "Text."}],
                      "idempotency_key": "t"},
            )

    assert asyncio.run(requests()).status_code == 403


def test_prose_api_without_active_profile_directs_to_settings():
    from dm_assistant_core.application.ai_configuration import AIConfigurationService

    class MemoryRepository:
        def latest_by_purpose(self):
            return {"extraction": type("R", (), {"profile_key": "deepseek-chat", "purpose": "extraction"})()}

        def activate(self, receipt):
            pass

    app = create_app(Settings(
        database_url="postgresql://campaign:secret@localhost:5432/campaign",
        run_migrations=False,
        openrouter_api_key="sk-test",
    ), ai_configuration=AIConfigurationService(MemoryRepository()))

    async def requests() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post(
                "/prose/draft?requester_role=dm",
                json={"subject": "Fleurite", "subject_kind": "location",
                      "material": [{"key": "k1", "kind": "claim", "text": "Text."}],
                      "idempotency_key": "t"},
            )

    response = asyncio.run(requests())
    assert response.status_code == 409
    assert "activate one in Settings" in response.json()["detail"]
