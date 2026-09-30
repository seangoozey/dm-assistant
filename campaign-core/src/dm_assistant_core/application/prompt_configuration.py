"""Editable, versioned AI prompts (TKT-0126).

Prompts are part of the audited contract: an override sits on top of the
built-in default, saves file receipts, and versions stamp as
``<purpose>/local-<n>`` so drafts and extraction runs record which prompt
produced them. Clearing an override restores the default. Editing changes
text only — the structural contract around each prompt (citations, JSON
shape) is not stored here and cannot be edited away.
"""

from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from dm_assistant_core.application.ai_configuration import (
    EXTRACTION_PURPOSE,
    PROSE_PURPOSE,
    PROMOTION_PURPOSE,
)
from dm_assistant_core.domain.extraction import EXTRACTION_SYSTEM_PROMPT
from dm_assistant_core.application.prose_drafting import PROSE_SYSTEM_PROMPT
from dm_assistant_core.application.promotion_assistant import PROMOTION_SYSTEM_PROMPT

BUILT_IN_PROMPTS = {
    PROSE_PURPOSE: PROSE_SYSTEM_PROMPT,
    EXTRACTION_PURPOSE: EXTRACTION_SYSTEM_PROMPT,
    PROMOTION_PURPOSE: PROMOTION_SYSTEM_PROMPT,
}


class EffectivePrompt(BaseModel):
    model_config = ConfigDict(frozen=True)
    purpose: str
    prompt_text: str
    version_label: str
    overridden: bool
    updated_at: datetime | None = None


class PromptOverrideReceipt(BaseModel):
    model_config = ConfigDict(frozen=True)
    receipt_id: UUID
    purpose: str
    action: str
    version_label: str
    changed_at: datetime


class SetPromptOverride(BaseModel):
    model_config = ConfigDict(frozen=True)
    purpose: str
    prompt_text: str = Field(min_length=1)


class PromptOverrideRepository(Protocol):
    def load(self, purpose: str) -> tuple[str, str, UUID, datetime] | None: ...

    def count_receipts(self, purpose: str) -> int: ...

    def file_receipt(self, receipt: PromptOverrideReceipt, prompt_text: str | None) -> None:
        """Record the change; a non-null prompt_text upserts the override,
        null clears it (a clear receipt is filed even when nothing existed)."""

    def clear(self, purpose: str) -> None: ...


class PromptConfigurationService:
    def __init__(self, repository: PromptOverrideRepository) -> None:
        self._repository = repository

    def effective(self, purpose: str) -> EffectivePrompt:
        if purpose not in BUILT_IN_PROMPTS:
            raise ValueError(f"no editable prompt for purpose '{purpose}'")
        row = self._repository.load(purpose)
        if row is None:
            return EffectivePrompt(
                purpose=purpose,
                prompt_text=BUILT_IN_PROMPTS[purpose],
                version_label=f"{purpose}/default",
                overridden=False,
            )
        text, version, _receipt, updated = row
        return EffectivePrompt(
            purpose=purpose,
            prompt_text=text,
            version_label=version,
            overridden=True,
            updated_at=updated,
        )

    def set_override(self, command: SetPromptOverride) -> PromptOverrideReceipt:
        if command.purpose not in BUILT_IN_PROMPTS:
            raise ValueError(f"no editable prompt for purpose '{command.purpose}'")
        if command.purpose == PROSE_PURPOSE and "Respond as JSON" not in command.prompt_text:
            raise ValueError("the prose prompt must keep its JSON response contract")
        if command.purpose == PROMOTION_PURPOSE and "Respond as JSON" not in command.prompt_text:
            raise ValueError("the promotion prompt must keep its JSON response contract")
        version_label = (
            f"{command.purpose}/local-{self._repository.count_receipts(command.purpose) + 1}"
        )
        receipt = PromptOverrideReceipt(
            receipt_id=uuid4(),
            purpose=command.purpose,
            action="set",
            version_label=version_label,
            changed_at=datetime.now(UTC),
        )
        self._repository.file_receipt(receipt, command.prompt_text)
        return receipt

    def clear_override(self, purpose: str) -> PromptOverrideReceipt:
        if purpose not in BUILT_IN_PROMPTS:
            raise ValueError(f"no editable prompt for purpose '{purpose}'")
        receipt = PromptOverrideReceipt(
            receipt_id=uuid4(),
            purpose=purpose,
            action="clear",
            version_label=f"{purpose}/default",
            changed_at=datetime.now(UTC),
        )
        self._repository.clear(purpose)
        self._repository.file_receipt(receipt, None)
        return receipt
