"""OpenRouter chat-completion client (ADR-0008, TKT-0033).

This is strictly provider plumbing: a typed HTTP client that sends a chat-completion
request to OpenRouter, validates the response against a typed contract, and enforces
configurable timeout, retry, and cost limits. It contains no domain logic and no
extraction behavior (TKT-0034 builds the harness on top of this).

The client defaults to the selected v1 extraction model ``deepseek/deepseek-chat``.
A future provider or model change is a bounded modification here, not a domain change.

The client is fully testable offline: the ``transport`` seam accepts any callable that
produces a raw response dict, so tests inject recorded fixtures without network access.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

from dm_assistant_core.adapters.openrouter.exceptions import (
    OpenRouterAuthError,
    OpenRouterContractError,
    OpenRouterError,
    OpenRouterRateLimitError,
    OpenRouterServerError,
    OpenRouterTimeoutError,
)
from dm_assistant_core.adapters.openrouter.models import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
)

#: The v1 model pinned by ADR-0008.
DEFAULT_MODEL = "deepseek/deepseek-chat"
#: The v1 OpenRouter base URL.
DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"

#: Retryable HTTP status codes (rate limit and server errors).
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class Transport(Protocol):
    """The seam over the HTTP layer so the client is testable offline."""

    def post(self, url: str, headers: dict[str, str], json: dict[str, Any]) -> Response: ...


class Response(Protocol):
    """A minimal HTTP response surface the client consumes."""

    @property
    def status_code(self) -> int: ...

    def json(self) -> dict[str, Any]: ...


class OpenRouterClient:
    """Typed, cost-bounded, retryable chat-completion client for OpenRouter.

    The client never sees or stores the API key outside of request headers. It enforces
    a per-request token cap and retries rate-limit/server errors up to the configured
    limit with exponential backoff.
    """

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        model: str = DEFAULT_MODEL,
        max_tokens: int = 8192,
        timeout_seconds: float = 60.0,
        max_retries: int = 2,
        reasoning_effort: str | None = None,
        transport: Transport | None = None,
    ) -> None:
        if not api_key:
            raise OpenRouterAuthError("an OpenRouter API key is required")
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._max_tokens = max_tokens
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries
        self._reasoning_effort = reasoning_effort
        self._transport = transport or _HttpxTransport(timeout_seconds)

    @property
    def model(self) -> str:
        return self._model

    def complete(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        """Send a chat-completion request and return the validated typed response."""
        payload = request.model_dump(mode="json", exclude_none=True)
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        url = f"{self._base_url}/chat/completions"
        raw = self._post_with_retry(url, headers, payload)
        return self._validate_response(raw)

    def quick_complete(
        self,
        *,
        system: str,
        user: str,
        response_schema: dict[str, Any] | None = None,
    ) -> ChatCompletionResponse:
        """Convenience for a single system + user turn using the client's defaults."""
        response_format: dict[str, Any]
        if response_schema is None:
            response_format = {"type": "json_object"}
        else:
            response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": "candidate_extraction",
                    "strict": True,
                    "schema": response_schema,
                },
            }
        request = ChatCompletionRequest(
            model=self._model,
            messages=(
                ChatMessage(role="system", content=system),
                ChatMessage(role="user", content=user),
            ),
            max_tokens=self._max_tokens,
            response_format=response_format,
            reasoning=(
                {"effort": self._reasoning_effort, "exclude": True}
                if self._reasoning_effort is not None
                else None
            ),
        )
        return self.complete(request)

    def _post_with_retry(
        self,
        url: str,
        headers: dict[str, str],
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        import time

        last_error: OpenRouterError | None = None
        for attempt in range(self._max_retries + 1):
            try:
                response = self._transport.post(url, headers, payload)
            except TimeoutError as error:
                last_error = OpenRouterTimeoutError(str(error))
                if attempt < self._max_retries:
                    time.sleep(2**attempt * 0.5)
                    continue
                raise last_error from error

            status = response.status_code
            if status == 200:
                raw = response.json()
                empty_detail = self._empty_content_detail(raw)
                if empty_detail is not None:
                    last_error = OpenRouterContractError(empty_detail)
                    if attempt < self._max_retries:
                        time.sleep(2**attempt * 0.5)
                        continue
                    raise last_error
                truncated_detail = self._truncated_content_detail(raw)
                if truncated_detail is not None:
                    raise OpenRouterContractError(truncated_detail)
                return raw
            if status == 401 or status == 403:
                raise OpenRouterAuthError(f"OpenRouter rejected credentials (HTTP {status})")
            if status in _RETRYABLE_STATUS:
                last_error = self._retryable_error(status)
                if attempt < self._max_retries:
                    time.sleep(2**attempt * 0.5)
                    continue
                raise last_error
            detail = self._provider_error_detail(response)
            suffix = f": {detail}" if detail else ""
            raise OpenRouterServerError(f"unexpected OpenRouter status: HTTP {status}{suffix}")
        assert last_error is not None
        raise last_error

    @staticmethod
    def _empty_content_detail(raw: dict[str, Any]) -> str | None:
        choices = raw.get("choices")
        if not isinstance(choices, list) or not choices:
            return None
        choice = choices[0]
        if not isinstance(choice, dict):
            return None
        message = choice.get("message")
        if not isinstance(message, dict):
            return None
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            return None
        finish_reason = choice.get("finish_reason") or "unknown"
        usage = raw.get("usage")
        completion_tokens = usage.get("completion_tokens") if isinstance(usage, dict) else None
        token_detail = str(completion_tokens) if completion_tokens is not None else "unknown"
        return (
            "provider returned empty content "
            f"(finish_reason={finish_reason}, completion_tokens={token_detail})"
        )

    @staticmethod
    def _truncated_content_detail(raw: dict[str, Any]) -> str | None:
        choices = raw.get("choices")
        if not isinstance(choices, list) or not choices:
            return None
        choice = choices[0]
        if not isinstance(choice, dict) or choice.get("finish_reason") != "length":
            return None
        usage = raw.get("usage")
        completion_tokens = usage.get("completion_tokens") if isinstance(usage, dict) else None
        token_detail = str(completion_tokens) if completion_tokens is not None else "unknown"
        return (
            "provider output was truncated by the completion limit "
            f"(finish_reason=length, completion_tokens={token_detail})"
        )

    @staticmethod
    def _retryable_error(status: int) -> OpenRouterError:
        if status == 429:
            return OpenRouterRateLimitError("OpenRouter rate limit exceeded")
        return OpenRouterServerError(f"OpenRouter server error: HTTP {status}")

    @staticmethod
    def _provider_error_detail(response: Response) -> str | None:
        """Return a bounded provider message without echoing request content."""
        try:
            body = response.json()
        except Exception:
            return None
        error = body.get("error")
        message = error.get("message") if isinstance(error, dict) else error
        if not isinstance(message, str) or not message.strip():
            return None
        return " ".join(message.split())[:500]

    @staticmethod
    def _validate_response(raw: dict[str, Any]) -> ChatCompletionResponse:
        try:
            return ChatCompletionResponse.model_validate(raw)
        except Exception as error:
            raise OpenRouterContractError(
                f"OpenRouter response failed contract validation: {error}"
            ) from error


class _HttpxTransport:
    """The production transport using httpx with a real timeout."""

    def __init__(self, timeout_seconds: float) -> None:
        self._timeout = timeout_seconds

    def post(self, url: str, headers: dict[str, str], json: dict[str, Any]) -> Response:
        import httpx

        try:
            response = httpx.post(url, headers=headers, json=json, timeout=self._timeout)
        except httpx.TimeoutException as error:
            raise TimeoutError(str(error)) from error
        return _HttpxResponse(response)


class _HttpxResponse:
    """Adapter wrapping an httpx.Response to satisfy the Response protocol."""

    def __init__(self, response: Any) -> None:
        self._response = response

    @property
    def status_code(self) -> int:
        return int(self._response.status_code)

    def json(self) -> dict[str, Any]:
        return dict(self._response.json())


class FixtureTransport:
    """An offline transport that returns a recorded fixture for testing.

    Accepts a callable that inspects the request and returns either a dict (treated as a
    successful JSON body) or a tuple ``(status_code, body)`` for error responses.
    """

    def __init__(
        self,
        responder: Callable[
            [str, dict[str, str], dict[str, Any]],
            dict[str, Any] | tuple[int, dict[str, Any]],
        ],
    ) -> None:
        self._responder = responder

    def post(self, url: str, headers: dict[str, str], json: dict[str, Any]) -> Response:
        result = self._responder(url, headers, json)
        if isinstance(result, tuple):
            status, body = result
        else:
            status, body = 200, result
        return _FixtureResponse(status, body)


class _FixtureResponse:
    """A response backed by a recorded fixture dict."""

    def __init__(self, status_code: int, body: dict[str, Any]) -> None:
        self._status_code = status_code
        self._body = body

    @property
    def status_code(self) -> int:
        return self._status_code

    def json(self) -> dict[str, Any]:
        return self._body
