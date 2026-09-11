"""Offline unit tests for the OpenRouter provider client (TKT-0033).

Every test uses FixtureTransport so there is no network access. The fixtures are
sanitized synthetic responses, not real provider data.
"""

from __future__ import annotations

import pytest

from dm_assistant_core.adapters.openrouter import (
    DEFAULT_MODEL,
    ChatCompletionRequest,
    ChatMessage,
    FixtureTransport,
    OpenRouterAuthError,
    OpenRouterClient,
    OpenRouterContractError,
    OpenRouterRateLimitError,
    OpenRouterServerError,
)


def _success_body(content: str = "Extracted result.") -> dict:
    return {
        "id": "gen-synthetic-001",
        "model": DEFAULT_MODEL,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }


def _client(responder, **kwargs) -> OpenRouterClient:
    return OpenRouterClient(
        api_key="test-key",
        transport=FixtureTransport(responder),
        max_retries=kwargs.pop("max_retries", 0),
        **kwargs,
    )


class TestClientConstruction:
    def test_missing_api_key_raises(self) -> None:
        with pytest.raises(OpenRouterAuthError):
            OpenRouterClient(api_key="")

    def test_default_model_is_deepseek_chat(self) -> None:
        client = OpenRouterClient(api_key="test-key", transport=FixtureTransport(lambda *_: {}))
        assert client.model == DEFAULT_MODEL
        assert client.model == "deepseek/deepseek-chat"

    def test_custom_model_accepted(self) -> None:
        client = OpenRouterClient(
            api_key="test-key",
            model="other/model",
            transport=FixtureTransport(lambda *_: {}),
        )
        assert client.model == "other/model"


class TestSuccessfulCompletion:
    def test_valid_response_returns_typed_result(self) -> None:
        client = _client(lambda *_: _success_body("The archivist tends the ledger."))
        response = client.quick_complete(system="Extract facts.", user="Some text.")

        assert response.id == "gen-synthetic-001"
        assert response.model == DEFAULT_MODEL
        assert response.content == "The archivist tends the ledger."
        assert response.usage.total_tokens == 15

    def test_complete_uses_provided_request_model(self) -> None:
        captured: dict = {}

        def responder(url: str, headers: dict, json_body: dict) -> dict:
            captured.update(json_body)
            return _success_body()

        client = _client(responder, reasoning_effort="minimal")
        request = ChatCompletionRequest(
            model="openai/gpt-5-nano",
            messages=(ChatMessage(role="user", content="test"),),
        )
        client.complete(request)
        assert captured["model"] == "openai/gpt-5-nano"
        assert captured["max_tokens"] == 4096

    def test_authorization_header_set_from_key(self) -> None:
        captured: dict = {}

        def responder(url: str, headers: dict, json_body: dict) -> dict:
            captured.update(headers)
            return _success_body()

        client = _client(responder)
        client.quick_complete(system="s", user="u")
        assert captured["Authorization"] == "Bearer test-key"

    def test_post_url_targets_chat_completions(self) -> None:
        captured: dict = {}

        def responder(url: str, headers: dict, json_body: dict) -> dict:
            captured["url"] = url
            return _success_body()

        client = _client(responder)
        client.quick_complete(system="s", user="u")
        assert captured["url"].endswith("/chat/completions")

    def test_quick_completion_requests_json_with_minimal_reasoning(self) -> None:
        captured: dict = {}

        def responder(url: str, headers: dict, json_body: dict) -> dict:
            captured.update(json_body)
            return _success_body()

        client = _client(responder, max_tokens=4096, reasoning_effort="minimal")
        client.quick_complete(system="s", user="u")

        assert captured["max_tokens"] == 4096
        assert captured["response_format"] == {"type": "json_object"}
        assert captured["reasoning"] == {"effort": "minimal", "exclude": True}

    def test_deepseek_profile_omits_reasoning_configuration(self) -> None:
        captured: dict = {}

        def responder(url: str, headers: dict, json_body: dict) -> dict:
            captured.update(json_body)
            return _success_body()

        client = _client(responder, model="deepseek/deepseek-chat")
        client.quick_complete(system="s", user="u")

        assert "reasoning" not in captured
        assert "temperature" not in captured

    def test_quick_completion_requests_strict_structured_output(self) -> None:
        captured: dict = {}

        def responder(url: str, headers: dict, json_body: dict) -> dict:
            captured.update(json_body)
            return _success_body()

        schema = {
            "type": "object",
            "properties": {"assertions": {"type": "array", "items": {}}},
            "required": ["assertions"],
            "additionalProperties": False,
        }
        client = _client(responder)
        client.quick_complete(system="s", user="u", response_schema=schema)

        assert captured["response_format"] == {
            "type": "json_schema",
            "json_schema": {
                "name": "candidate_extraction",
                "strict": True,
                "schema": schema,
            },
        }


class TestErrorHandling:
    def test_empty_success_response_retries_then_returns_content(self) -> None:
        calls = {"count": 0}

        def responder(*_args) -> dict:
            calls["count"] += 1
            if calls["count"] == 1:
                body = _success_body()
                body["choices"][0]["message"]["content"] = None
                body["choices"][0]["finish_reason"] = "length"
                body["usage"]["completion_tokens"] = 4096
                return body
            return _success_body('{"assertions": []}')

        client = _client(responder, max_retries=1)
        response = client.quick_complete(system="s", user="u")

        assert calls["count"] == 2
        assert response.content == '{"assertions": []}'

    def test_repeated_empty_response_reports_bounded_diagnostics(self) -> None:
        body = _success_body()
        body["choices"][0]["message"]["content"] = ""
        body["choices"][0]["finish_reason"] = "length"
        body["usage"]["completion_tokens"] = 4096
        client = _client(lambda *_: body, max_retries=1)

        with pytest.raises(
            OpenRouterContractError,
            match=r"finish_reason=length, completion_tokens=4096",
        ):
            client.quick_complete(system="s", user="u")

    def test_truncated_nonempty_response_reports_completion_limit(self) -> None:
        body = _success_body('{"assertions": [{"subject": "cut off')
        body["choices"][0]["finish_reason"] = "length"
        body["usage"]["completion_tokens"] = 4096
        client = _client(lambda *_: body)

        with pytest.raises(
            OpenRouterContractError,
            match=r"truncated.*finish_reason=length, completion_tokens=4096",
        ):
            client.quick_complete(system="s", user="u")

    def test_unauthorized_raises_auth_error(self) -> None:
        client = _client(lambda *_: (401, {"error": "unauthorized"}))
        with pytest.raises(OpenRouterAuthError, match="HTTP 401"):
            client.quick_complete(system="s", user="u")

    def test_forbidden_raises_auth_error(self) -> None:
        client = _client(lambda *_: (403, {"error": "forbidden"}))
        with pytest.raises(OpenRouterAuthError):
            client.quick_complete(system="s", user="u")

    def test_rate_limit_raises_after_retries(self) -> None:
        client = _client(lambda *_: (429, {"error": "rate limit"}), max_retries=1)
        with pytest.raises(OpenRouterRateLimitError):
            client.quick_complete(system="s", user="u")

    def test_server_error_raises_after_retries(self) -> None:
        client = _client(lambda *_: (503, {"error": "unavailable"}), max_retries=1)
        with pytest.raises(OpenRouterServerError):
            client.quick_complete(system="s", user="u")

    def test_unexpected_status_raises_server_error(self) -> None:
        client = _client(lambda *_: (418, {"error": "teapot"}))
        with pytest.raises(OpenRouterServerError, match="HTTP 418: teapot"):
            client.quick_complete(system="s", user="u")

    def test_structured_provider_error_is_reported_without_request_data(self) -> None:
        client = _client(
            lambda *_: (400, {"error": {"message": "Unsupported parameter: temperature"}})
        )
        with pytest.raises(
            OpenRouterServerError,
            match="HTTP 400: Unsupported parameter: temperature",
        ):
            client.quick_complete(system="private system", user="private source")


class TestContractValidation:
    def test_missing_choices_rejected(self) -> None:
        body = {
            "id": "x",
            "model": DEFAULT_MODEL,
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        }
        client = _client(lambda *_: body)
        with pytest.raises(OpenRouterContractError):
            client.quick_complete(system="s", user="u")

    def test_missing_usage_rejected(self) -> None:
        body = {
            "id": "x",
            "model": DEFAULT_MODEL,
            "choices": [{"index": 0, "message": {"role": "assistant", "content": "y"}}],
        }
        client = _client(lambda *_: body)
        with pytest.raises(OpenRouterContractError):
            client.quick_complete(system="s", user="u")

    def test_empty_choices_rejected(self) -> None:
        body = {
            "id": "x",
            "model": DEFAULT_MODEL,
            "choices": [],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        }
        client = _client(lambda *_: body)
        with pytest.raises(OpenRouterContractError):
            client.quick_complete(system="s", user="u")


class TestRetry:
    def test_retries_rate_limit_then_succeeds(self) -> None:
        calls = {"count": 0}

        def responder(url: str, headers: dict, json_body: dict):
            calls["count"] += 1
            if calls["count"] < 2:
                return (429, {"error": "rate limit"})
            return _success_body("recovered")

        client = _client(responder, max_retries=2)
        response = client.quick_complete(system="s", user="u")
        assert response.content == "recovered"
        assert calls["count"] == 2


class TestRequestValidation:
    def test_request_requires_at_least_one_message(self) -> None:
        with pytest.raises(ValueError):
            ChatCompletionRequest(model=DEFAULT_MODEL, messages=())

    def test_message_content_cannot_be_empty(self) -> None:
        with pytest.raises(ValueError):
            ChatMessage(role="user", content="")

    def test_max_tokens_must_be_positive(self) -> None:
        with pytest.raises(ValueError):
            ChatCompletionRequest(
                model=DEFAULT_MODEL,
                messages=(ChatMessage(role="user", content="x"),),
                max_tokens=0,
            )
