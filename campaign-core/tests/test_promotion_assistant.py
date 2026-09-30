"""AI promotion assistant contract (TKT-0137)."""

import asyncio
from json import dumps

import httpx
import pytest

from dm_assistant_core.application.promotion_assistant import (
    PromotionAssistantService,
    PromotionSuggestionCommand,
    PromotionSuggestionError,
    PromotionSuggestionHarness,
    PromotionSuggestionMaterial,
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
    def __init__(self, content: str, prompt_tokens: int = 90, completion_tokens: int = 210) -> None:
        self.content = content

        class _Usage:
            pass
        self.usage = _Usage()
        self.usage.prompt_tokens = prompt_tokens  # type: ignore[attr-defined]
        self.usage.completion_tokens = completion_tokens  # type: ignore[attr-defined]


GOOD_RESPONSE = dumps({
    "restatements": [{"statement": 2, "material": 1}],
    "statements": [
        {"text": "The keeper records every visitor.", "state": "considered", "basis": 2},
    ],
    "links": [{"material": 3, "reason": "the claim is really about the archive"}],
})


def command(**overrides):
    base = dict(
        surface="lore",
        subject="Keeper's Archive",
        subject_kind="location",
        prose="The archive is quiet. The keeper tends the archive.",
        material=(
            PromotionSuggestionMaterial(key="aa1", state="established", text="The keeper tends the vault archive."),
            PromotionSuggestionMaterial(key="bb2", state="considered", text="Someone maintains a visitor ledger."),
            PromotionSuggestionMaterial(key="cc3", state="established", text="The archive holds the lost regalia of Fleurite."),
        ),
        idempotency_key="suggest:test",
    )
    base.update(overrides)
    return PromotionSuggestionCommand(**base)


def service(client: ScriptedClient) -> PromotionAssistantService:
    return PromotionAssistantService(PromotionSuggestionHarness(client), model_slug="deepseek/deepseek-chat")


def test_suggestions_resolve_positional_references_to_keys():
    client = ScriptedClient([GOOD_RESPONSE])
    result = service(client).suggest(command())
    assert result.restatements[0].statement_number == 2
    assert result.restatements[0].statement_text == "The keeper tends the archive."
    assert result.restatements[0].material_key == "aa1"
    assert result.statements[0].basis_key == "bb2"
    assert result.links[0].material_key == "cc3"
    assert result.model_slug == "deepseek/deepseek-chat"
    assert result.prompt_tokens == 90 and result.completion_tokens == 210


def test_the_prompt_carries_numbered_statements_and_states():
    client = ScriptedClient([GOOD_RESPONSE])
    service(client).suggest(command())
    prompt = client.prompts[0]
    assert "1. The archive is quiet." in prompt
    assert "2. The keeper tends the archive." in prompt
    assert "[1] (established) The keeper tends the vault archive." in prompt


def test_empty_prose_skips_the_restatement_pass_without_failing():
    client = ScriptedClient([dumps({"restatements": [], "statements": [], "links": []})])
    result = service(client).suggest(command(prose=""))
    assert result.restatements == ()
    assert "none — the draft description is empty" in client.prompts[0]


def test_out_of_range_statement_number_is_retried_then_accepted():
    bad = dumps({"restatements": [{"statement": 9, "material": 1}], "statements": [], "links": []})
    good = dumps({"restatements": [{"statement": 1, "material": 1}], "statements": [], "links": []})
    client = ScriptedClient([bad, good])
    result = service(client).suggest(command())
    assert result.restatements[0].statement_number == 1
    assert "statement number that does not exist" in client.prompts[1]


def test_out_of_range_basis_is_refused_after_retries():
    bad = dumps({"restatements": [], "statements": [{"text": "x", "state": "established", "basis": 9}], "links": []})
    good = dumps({"restatements": [], "statements": [{"text": "x", "state": "established", "basis": 1}], "links": []})
    client = ScriptedClient([bad, good])
    result = service(client).suggest(command())
    assert result.statements[0].basis_key == "aa1"


def test_unknown_suggested_state_is_refused():
    bad = dumps({
        "restatements": [], "statements": [{"text": "x", "state": "observed", "basis": 1}], "links": [],
    })
    client = ScriptedClient([bad, bad])
    with pytest.raises(PromotionSuggestionError, match="state outside established/considered/prepared"):
        service(client).suggest(command())


def test_non_json_response_is_refused_after_retries():
    client = ScriptedClient(["not json", "still not json"])
    with pytest.raises(PromotionSuggestionError, match="not JSON"):
        service(client).suggest(command())


def test_non_lore_surfaces_are_refused():
    client = ScriptedClient([GOOD_RESPONSE])
    with pytest.raises(PromotionSuggestionError, match="Lore and Description surfaces"):
        service(client).suggest(command(surface="brainstorm"))


def test_suggestion_api_is_dm_only_and_directs_to_settings_without_a_profile():
    from dm_assistant_core.application.ai_configuration import AIConfigurationService

    class MemoryRepository:
        def latest_by_purpose(self):
            return {"extraction": type("R", (), {"profile_key": "deepseek-chat", "purpose": "extraction"})()}

        def activate(self, receipt):
            pass

    app = create_app(Settings(
        database_url="postgresql://campaign:secret@localhost:5432/campaign",
        run_migrations=False,
    ), ai_configuration=AIConfigurationService(MemoryRepository()))

    async def send(role: str) -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post(
                f"/promotion/suggest?requester_role={role}",
                json={
                    "surface": "lore", "subject": "Keeper's Archive", "subject_kind": "location",
                    "material": [{"key": "k1", "text": "Text."}],
                    "idempotency_key": "t",
                },
            )

    assert asyncio.run(send("party")).status_code == 403
    missing_profile = asyncio.run(send("dm"))
    assert missing_profile.status_code == 409
    assert "activate one in Settings" in missing_profile.json()["detail"]


def test_the_promotion_purpose_has_a_selectable_candidate_profile():
    from dm_assistant_core.application.ai_configuration import (
        AIConfigurationService,
        PROMOTION_PURPOSE,
        PROMOTION_PURPOSE as purpose_key,
    )

    class MemoryRepository:
        def latest_by_purpose(self):
            return {}

        def activate(self, receipt):
            pass

    snapshot = AIConfigurationService(MemoryRepository()).snapshot()
    purpose = next(p for p in snapshot.purposes if p.key == purpose_key)
    assert purpose.label == "Promotion assistant"
    profiles = [p for p in snapshot.profiles if p.purpose == PROMOTION_PURPOSE]
    assert [p.key for p in profiles] == ["deepseek-chat"]
    assert profiles[0].selectable
    # No default: the promotion model requires Sean's receipted activation.
    assert PROMOTION_PURPOSE not in snapshot.active_profile_by_purpose


def test_the_description_surface_uses_the_explicit_rows_and_returns_the_system_mirror():
    # The Description surface sends its reviewed :: rows verbatim; the result
    # carries the deterministic mirror (system value) beside the AI's calls —
    # the material for the mirror is a real claim UUID, term-overlap matched.
    material = (
        PromotionSuggestionMaterial(key="aa000000-0000-0000-0000-000000000001",
                                    state="established",
                                    text="The keeper tends the vault archive."),
        PromotionSuggestionMaterial(key="seed:xyz", state="considered",
                                    text="A seed line without a claim UUID is skipped by the mirror."),
    )
    client = ScriptedClient([dumps({
        "restatements": [{"statement": 1, "material": 1}],
        "statements": [], "links": [],
    })])
    result = service(client).suggest(command(
        surface="description",
        prose="",
        statements=("The keeper tends the archive.", "A genuinely new assertion."),
        material=material,
    ))
    # AI restatement (statement 2 → material 1) rides as before…
    assert result.restatements[0].statement_text == "The keeper tends the archive."
    # …and the SYSTEM mirror independently flags the term-overlap row, while
    # the genuinely-new row goes unflagged. Non-UUID keys never participate.
    assert [(r.statement_number, r.material_key) for r in result.system_restatements] == [
        (1, "aa000000-0000-0000-0000-000000000001")
    ]


def test_the_system_mirror_finds_nothing_when_no_row_overlaps():
    client = ScriptedClient([dumps({"restatements": [], "statements": [], "links": []})])
    result = service(client).suggest(command(
        surface="description", prose="",
        statements=("Something wholly unrelated about weather.",),
    ))
    assert result.system_restatements == ()
    assert result.restatements == ()


def test_the_promotion_prompt_is_editable_with_a_json_guard():
    from dm_assistant_core.application.prompt_configuration import (
        PromptConfigurationService,
        SetPromptOverride,
    )

    class MemoryRepository:
        def __init__(self) -> None:
            self.rows: dict[str, tuple[str, str, object, object]] = {}
            self.receipts: list[object] = []

        def load(self, purpose):
            return self.rows.get(purpose)

        def count_receipts(self, purpose):
            return len(self.receipts)

        def file_receipt(self, receipt, prompt_text):
            self.receipts.append(receipt)
            if prompt_text is not None:
                self.rows[receipt.purpose] = (prompt_text, receipt.version_label, receipt, None)

        def clear(self, purpose):
            self.rows.pop(purpose, None)

    repository = MemoryRepository()
    configuration = PromptConfigurationService(repository)
    effective = configuration.effective("promotion")
    assert effective.version_label == "promotion/default"
    assert "Respond as JSON" in effective.prompt_text

    with pytest.raises(ValueError, match="JSON response contract"):
        configuration.set_override(SetPromptOverride(purpose="promotion", prompt_text="Be helpful."))

    receipt = configuration.set_override(SetPromptOverride(
        purpose="promotion", prompt_text="Suggest restatements. Respond as JSON: {}"))
    assert receipt.version_label == "promotion/local-1"
    assert configuration.effective("promotion").overridden
