"""Controlled AI model registry and durable activation boundary."""

from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict

from dm_assistant_core.domain.extraction import EXTRACTION_SYSTEM_PROMPT


class ModelProfile(BaseModel):
    model_config = ConfigDict(frozen=True)
    key: str
    provider: str
    model_slug: str
    description: str
    reasoning_effort: str | None
    max_tokens: int
    timeout_seconds: float
    retry_limit: int
    selectable: bool = True
    suitability: str


PROFILES = (
    ModelProfile(
        key="deepseek-chat",
        provider="openrouter",
        model_slug="deepseek/deepseek-chat",
        description="Proven non-reasoning extraction profile.",
        reasoning_effort=None,
        max_tokens=8192,
        timeout_seconds=90,
        retry_limit=1,
        suitability="recommended",
    ),
    ModelProfile(
        key="gpt5-nano-evaluated",
        provider="openrouter",
        model_slug="openai/gpt-5-nano",
        description="Retained for audit after repeated representative extraction failures.",
        reasoning_effort="minimal",
        max_tokens=8192,
        timeout_seconds=90,
        retry_limit=1,
        selectable=False,
        suitability="unsuitable",
    ),
)
PROMPT_VERSION = "extraction/8"


class ActivationReceipt(BaseModel):
    model_config = ConfigDict(frozen=True)
    receipt_id: UUID
    profile_key: str
    prompt_version: str
    activated_at: datetime


class AIConfigurationSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)
    profiles: tuple[ModelProfile, ...]
    active_profile_key: str
    prompt_version: str
    prompt_text: str
    last_activation: ActivationReceipt | None = None


class AIConfigurationRepository(Protocol):
    def latest(self) -> ActivationReceipt | None: ...
    def activate(self, receipt: ActivationReceipt) -> None: ...


class AIConfigurationService:
    def __init__(self, repository: AIConfigurationRepository) -> None:
        self._repository = repository

    def snapshot(self) -> AIConfigurationSnapshot:
        latest = self._repository.latest()
        return AIConfigurationSnapshot(
            profiles=PROFILES,
            active_profile_key=latest.profile_key if latest else "deepseek-chat",
            prompt_version=PROMPT_VERSION,
            prompt_text=EXTRACTION_SYSTEM_PROMPT,
            last_activation=latest,
        )

    def active_profile(self) -> ModelProfile:
        key = self.snapshot().active_profile_key
        return next(profile for profile in PROFILES if profile.key == key)

    def activate(self, profile_key: str) -> ActivationReceipt:
        profile = next((item for item in PROFILES if item.key == profile_key), None)
        if profile is None or not profile.selectable:
            raise ValueError("unsupported or non-selectable AI model profile")
        receipt = ActivationReceipt(
            receipt_id=uuid4(),
            profile_key=profile.key,
            prompt_version=PROMPT_VERSION,
            activated_at=datetime.now(UTC),
        )
        self._repository.activate(receipt)
        return receipt
