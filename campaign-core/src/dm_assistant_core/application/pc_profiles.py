"""Versioned editable overlays for curated PC documents."""

from typing import Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from dm_assistant_core.domain import RequesterRole, RequesterVisibility


class PCProfile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    document_id: UUID
    source_revision_id: UUID
    version: int = Field(ge=0)
    canonical_name: str = Field(min_length=1)
    player: str | None = None
    race: str | None = None
    sex: str | None = None
    status: str = Field(min_length=1)
    aliases: tuple[str, ...] = ()
    background: str = ""

    @field_validator("player", "race", "sex", mode="before")
    @classmethod
    def empty_is_unrecorded(cls, value: object) -> object:
        return None if isinstance(value, str) and not value.strip() else value


class UpdatePCProfileCommand(PCProfile):
    idempotency_key: str = Field(min_length=1)


class ProfileAliasSync(BaseModel):
    """Identity-alias mutations one profile save applied to its focal entity.

    The profile editor manages the 'profile' namespace only: aliases removed
    from the profile remove that namespace's rows; aliases owned by another
    identity are skipped, never stolen.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)
    entity_id: UUID
    entity_name: str
    applied: tuple[str, ...] = ()
    removed: tuple[str, ...] = ()
    skipped_conflicting: tuple[str, ...] = ()


class PCProfileReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    receipt_id: UUID
    document_id: UUID
    version: int
    idempotent_replay: bool
    alias_sync: ProfileAliasSync | None = None


class PCProfileError(ValueError):
    pass


class PCProfileRepository(Protocol):
    def get(self, document_id: UUID) -> PCProfile | None: ...
    def update(self, command: UpdatePCProfileCommand) -> PCProfileReceipt: ...


class PCProfileService:
    def __init__(self, repository: PCProfileRepository) -> None:
        self._repository = repository

    @staticmethod
    def _dm(requester: RequesterVisibility) -> None:
        if requester.role is not RequesterRole.DM:
            raise PermissionError("character profile editing is DM-only")

    def get(self, document_id: UUID, requester: RequesterVisibility) -> PCProfile | None:
        self._dm(requester)
        return self._repository.get(document_id)

    def update(
        self, command: UpdatePCProfileCommand, requester: RequesterVisibility
    ) -> PCProfileReceipt:
        self._dm(requester)
        return self._repository.update(command)
