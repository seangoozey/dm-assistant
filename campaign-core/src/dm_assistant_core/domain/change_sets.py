"""Typed contracts and errors for canonical change-set application."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$", strict=True)]


class ApplyChangeSetCommand(BaseModel):
    """The exact reviewed proposal coordinates required for application."""

    model_config = ConfigDict(frozen=True)

    change_set_id: UUID
    reviewed_version: int = Field(gt=0)
    approval_id: UUID
    content_hash: Sha256


class ChangeSetReceipt(BaseModel):
    """Durable result returned by the first apply and every safe retry."""

    model_config = ConfigDict(frozen=True)

    receipt_id: UUID
    change_set_id: UUID
    outcome: str = Field(min_length=1)
    applied_item_ids: tuple[UUID, ...] = Field(min_length=1)
    issued_at: datetime
    idempotent_replay: bool


class ChangeSetRejectedError(ValueError):
    """The requested application did not match an authorized immutable proposal."""
