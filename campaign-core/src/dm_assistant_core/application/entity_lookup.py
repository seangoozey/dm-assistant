"""Read-only entity identity lookup for human review workflows."""

from typing import Literal, Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from dm_assistant_core.domain import EntityKind


class EntityIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    entity_id: UUID
    canonical_name: str
    entity_kind: EntityKind
    match_kind: Literal["canonical", "alias", "partial"] = "canonical"
    matched_name: str | None = None


class EntityLookupRepository(Protocol):
    def search(self, name: str, limit: int) -> tuple[EntityIdentity, ...]: ...


class EntityLookupService:
    def __init__(self, repository: EntityLookupRepository) -> None:
        self._repository = repository

    def search(self, name: str, limit: int = 10) -> tuple[EntityIdentity, ...]:
        normalized = name.strip()
        if not normalized:
            return ()
        return self._repository.search(normalized, limit)
