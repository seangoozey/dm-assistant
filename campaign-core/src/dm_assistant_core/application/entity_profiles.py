"""Versioned editable profile overlays for file-less identities (TKT-0106).

Mirrors the PC-profile pattern, keyed to the entity rather than a source
document: queue-created identities (Ruh, Far Realm) get the same editable,
receipted metadata NPCs have. Presentational metadata only — canonical truth
stays in entities and claims.
"""

from typing import Protocol
from uuid import UUID

from typing import Literal

from dm_assistant_core.domain.chronology import CampaignDate

from pydantic import BaseModel, ConfigDict, Field, field_validator

from dm_assistant_core.domain import RequesterRole, RequesterVisibility


class EntityProfile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    entity_id: UUID
    version: int = Field(ge=0)
    canonical_name: str = Field(min_length=1)
    status: str | None = None
    location_type: str | None = None
    parent_location: str | None = None
    base_location: str | None = None
    player: str | None = None
    race: str | None = None
    sex: str | None = None
    aliases: tuple[str, ...] = ()
    summary: str = ""
    # Life status is an enumerated canon dimension (TKT-0123), distinct from
    # the free-text organizational status above; anchored to a backing claim.
    life_status: Literal["alive", "dead", "undead", "resurrected", "immortal", "unknown"] | None = None
    life_status_since: CampaignDate | None = None
    life_status_claim_id: UUID | None = None

    @field_validator("status", "location_type", "parent_location", "base_location",
                     "player", "race", "sex", mode="before")
    @classmethod
    def empty_is_unrecorded(cls, value: object) -> object:
        return None if isinstance(value, str) and not value.strip() else value


class UpdateEntityProfileCommand(EntityProfile):
    idempotency_key: str = Field(min_length=1)


class EntityProfileAliasSync(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    entity_name: str
    applied: tuple[str, ...] = ()
    removed: tuple[str, ...] = ()
    skipped_conflicting: tuple[str, ...] = ()


class EntityProfileReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    receipt_id: UUID
    entity_id: UUID
    version: int
    idempotent_replay: bool
    alias_sync: EntityProfileAliasSync | None = None


class EntityProfileError(ValueError):
    pass


class EntityProfileRepository(Protocol):
    def get(self, entity_id: UUID) -> EntityProfile | None: ...

    def update(self, command: UpdateEntityProfileCommand) -> EntityProfileReceipt: ...


class EntityProfileService:
    def __init__(self, repository: EntityProfileRepository) -> None:
        self._repository = repository

    @staticmethod
    def _dm(requester: RequesterVisibility) -> None:
        if requester.role is not RequesterRole.DM:
            raise PermissionError("entity profile editing is DM-only")

    def get(self, entity_id: UUID, requester: RequesterVisibility) -> EntityProfile | None:
        self._dm(requester)
        return self._repository.get(entity_id)

    def update(
        self, command: UpdateEntityProfileCommand, requester: RequesterVisibility
    ) -> EntityProfileReceipt:
        self._dm(requester)
        return self._repository.update(command)
