"""Controlled AI model registry and durable activation boundary.

Profiles are per-purpose: the model that extracts claims is not presumed to
be the model that drafts prose (or, eventually, serves graph work). Each
purpose declares its own prompt and carries its own activation receipts, so
switching the prose writer's model never disturbs the extraction path.
"""

from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict

from dm_assistant_core.domain.extraction import EXTRACTION_SYSTEM_PROMPT

EXTRACTION_PURPOSE = "extraction"
PROSE_PURPOSE = "prose"
PROMOTION_PURPOSE = "promotion"


class PurposeInfo(BaseModel):
    model_config = ConfigDict(frozen=True)
    key: str
    label: str
    description: str
    prompt_version: str | None = None
    prompt_text: str | None = None


class ModelProfile(BaseModel):
    model_config = ConfigDict(frozen=True)
    key: str
    purpose: str
    provider: str
    model_slug: str
    description: str
    reasoning_effort: str | None
    max_tokens: int
    timeout_seconds: float
    retry_limit: int
    selectable: bool = True
    suitability: str


PURPOSES = (
    PurposeInfo(
        key=EXTRACTION_PURPOSE,
        label="Claim extraction",
        description=(
            "Reads reviewed documents and proposes candidate claims. "
            "Precision matters more than voice; non-reasoning profiles hold up."
        ),
        prompt_version="extraction/8",
        prompt_text=EXTRACTION_SYSTEM_PROMPT,
    ),
    PurposeInfo(
        key=PROSE_PURPOSE,
        description=(
            "Drafts evidence-class prose from selected material (TKT-0120: "
            "descriptions, lore synopses). Cheap and fast beats brilliant — "
            "the drafting rules and selected evidence do the quality work."
        ),
        label="Prose writing",
    ),
    PurposeInfo(
        key=PROMOTION_PURPOSE,
        description=(
            "Wand-marked suggestions inside promotion review (TKT-0137): "
            "restatement matching, statement ideas, Link/Consider pre-sort. "
            "Suggestions are never auto-included — the DM's review stays the "
            "decision."
        ),
        label="Promotion assistant",
    ),
)
PROFILES = (
    ModelProfile(
        key="deepseek-chat",
        purpose=EXTRACTION_PURPOSE,
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
        purpose=EXTRACTION_PURPOSE,
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
    ModelProfile(
        key="deepseek-v4-flash",
        purpose=PROSE_PURPOSE,
        provider="openrouter",
        model_slug="deepseek/deepseek-v4-flash-0731",
        description=(
            "Sean's first prose pick (2026-09-16): cheap, fast, non-reasoning "
            "flash tier — the drafting rules and selected evidence carry the "
            "quality, so the model spends its budget on fluency."
        ),
        reasoning_effort=None,
        max_tokens=8192,
        timeout_seconds=90,
        retry_limit=1,
        suitability="candidate",
    ),
    ModelProfile(
        key="deepseek-chat",
        purpose=PROMOTION_PURPOSE,
        provider="openrouter",
        model_slug="deepseek/deepseek-chat",
        description=(
            "The proven extraction model offered for promotion assistance "
            "(TKT-0137): restatement matching is an extraction-shaped task — "
            "precision over voice. Suitability is a candidate until live lore "
            "runs say otherwise."
        ),
        reasoning_effort=None,
        max_tokens=8192,
        timeout_seconds=90,
        retry_limit=1,
        suitability="candidate",
    ),
)
_DEFAULT_PROFILE_BY_PURPOSE = {EXTRACTION_PURPOSE: "deepseek-chat"}


class ActivationReceipt(BaseModel):
    model_config = ConfigDict(frozen=True)
    receipt_id: UUID
    purpose: str
    profile_key: str
    prompt_version: str
    activated_at: datetime


class AIConfigurationSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)
    purposes: tuple[PurposeInfo, ...]
    profiles: tuple[ModelProfile, ...]
    active_profile_by_purpose: dict[str, str]
    last_activation_by_purpose: dict[str, ActivationReceipt]


class AIConfigurationRepository(Protocol):
    def latest_by_purpose(self) -> dict[str, ActivationReceipt]: ...

    def activate(self, receipt: ActivationReceipt) -> None: ...


class AIConfigurationService:
    def __init__(self, repository: AIConfigurationRepository) -> None:
        self._repository = repository

    def snapshot(self) -> AIConfigurationSnapshot:
        latest = self._repository.latest_by_purpose()
        active = dict(_DEFAULT_PROFILE_BY_PURPOSE)
        active.update(
            {purpose: receipt.profile_key for purpose, receipt in latest.items()}
        )
        return AIConfigurationSnapshot(
            purposes=PURPOSES,
            profiles=PROFILES,
            active_profile_by_purpose=active,
            last_activation_by_purpose=latest,
        )

    def active_profile(self, purpose: str = EXTRACTION_PURPOSE) -> ModelProfile:
        key = self.snapshot().active_profile_by_purpose.get(purpose)
        if key is None:
            raise ValueError(f"no AI model profile is configured for purpose '{purpose}'")
        return next(profile for profile in PROFILES if profile.key == key)

    def activate(self, purpose: str, profile_key: str) -> ActivationReceipt:
        if purpose not in {item.key for item in PURPOSES}:
            raise ValueError(f"unknown AI model purpose '{purpose}'")
        purpose_info = next(item for item in PURPOSES if item.key == purpose)
        profile = next(
            (item for item in PROFILES if item.key == profile_key and item.purpose == purpose),
            None,
        )
        if profile is None or not profile.selectable:
            raise ValueError("unsupported or non-selectable AI model profile")
        receipt = ActivationReceipt(
            receipt_id=uuid4(),
            purpose=purpose,
            profile_key=profile.key,
            prompt_version=purpose_info.prompt_version or "unversioned",
            activated_at=datetime.now(UTC),
        )
        self._repository.activate(receipt)
        return receipt
