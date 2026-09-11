"""Typed request and response contracts for the OpenRouter chat-completion boundary.

These models are the single typed interface the extraction harness (TKT-0034) and any
future consumer speaks to. A future provider or model change (ADR-0008) is a bounded
modification to the client behind this interface, not a domain change.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ChatMessage(BaseModel):
    """One message in a chat-completion request."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    role: Literal["system", "user", "assistant"]
    content: str = Field(min_length=1)


class ResponseMessage(BaseModel):
    """One message returned by the provider.

    Uses ``extra="ignore"`` so provider-specific fields (reasoning, refusal, etc.)
    are tolerated; only ``role`` and ``content`` are consumed.
    """

    model_config = ConfigDict(extra="ignore", frozen=True)

    role: Literal["system", "user", "assistant"]
    content: str | None = None


class ChatCompletionRequest(BaseModel):
    """The typed request sent to the OpenRouter chat-completion endpoint."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    model: str = Field(min_length=1)
    messages: tuple[ChatMessage, ...] = Field(min_length=1)
    max_tokens: int = Field(default=4096, ge=1)
    # Sampling controls are model-specific. Omit temperature unless a caller has
    # deliberately selected a model that supports it.
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    response_format: dict[str, Any] | None = None
    reasoning: dict[str, Any] | None = None


class ChatCompletionChoice(BaseModel):
    """One completion choice returned by the provider."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    index: int = Field(ge=0)
    message: ResponseMessage
    finish_reason: str | None = None


class ChatCompletionUsage(BaseModel):
    """Token usage accounting for cost bounding."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    prompt_tokens: int = Field(ge=0)
    completion_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)


class ChatCompletionResponse(BaseModel):
    """The typed response validated from the OpenRouter chat-completion endpoint."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    id: str = Field(min_length=1)
    model: str = Field(min_length=1)
    choices: tuple[ChatCompletionChoice, ...] = Field(min_length=1)
    usage: ChatCompletionUsage

    @property
    def content(self) -> str | None:
        """The primary completion's content (may be None if tokens were exhausted)."""
        return self.choices[0].message.content
