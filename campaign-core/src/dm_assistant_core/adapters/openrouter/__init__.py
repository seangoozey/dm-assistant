"""OpenRouter AI provider client (ADR-0008, TKT-0033).

Strictly plumbing: a typed, cost-bounded, retryable chat-completion boundary. No domain
logic or extraction behavior lives here. See ``client.py`` for the single typed interface.
"""

from dm_assistant_core.adapters.openrouter.client import (
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    FixtureTransport,
    OpenRouterClient,
    Response,
    Transport,
)
from dm_assistant_core.adapters.openrouter.exceptions import (
    OpenRouterAuthError,
    OpenRouterContractError,
    OpenRouterError,
    OpenRouterRateLimitError,
    OpenRouterServerError,
    OpenRouterTimeoutError,
)
from dm_assistant_core.adapters.openrouter.models import (
    ChatCompletionChoice,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionUsage,
    ChatMessage,
    ResponseMessage,
)

__all__ = [
    "DEFAULT_BASE_URL",
    "DEFAULT_MODEL",
    "ChatCompletionChoice",
    "ChatCompletionRequest",
    "ChatCompletionResponse",
    "ChatCompletionUsage",
    "ChatMessage",
    "FixtureTransport",
    "OpenRouterAuthError",
    "OpenRouterClient",
    "OpenRouterContractError",
    "OpenRouterError",
    "OpenRouterRateLimitError",
    "OpenRouterServerError",
    "OpenRouterTimeoutError",
    "Response",
    "ResponseMessage",
    "Transport",
]
