"""Canonical, source-agnostic read model for campaign library entries."""

from datetime import datetime
from typing import Literal, Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from dm_assistant_core.domain import EntityKind

ClaimProjection = Literal["real_play", "player_plan", "npc_plan", "dm_plan", "lore_fact"]


class LibraryEntryMember(BaseModel):
    """One faction roster seat: the member identity and the role they hold.

    Only explicit roster rows appear here; the derived co-mention list is
    `related` (display context, never a roster — nothing to remove or seat).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)
    member_id: UUID
    name: str
    role_title: str | None = None
    is_leadership: bool = False


class LibraryEntryRole(BaseModel):
    """A faction's role definition; empty holders means a vacant seat."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    name: str
    is_leadership: bool = False
    holder_names: tuple[str, ...] = ()


class LibraryEntrySummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    entry_id: UUID
    canonical_name: str
    entity_kind: EntityKind
    aliases: tuple[str, ...] = ()
    misspellings: tuple[str, ...] = ()
    members: tuple[LibraryEntryMember, ...] = ()
    related: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    current_claim_count: int = 0
    source_count: int = 0


class LibraryEntrySource(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    document_id: UUID
    path: str


class LibraryEntryClaim(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    claim_id: UUID
    assertion_text: str
    state: str
    authority: str
    visibility: str
    conditional: bool
    condition_text: str | None = None
    recorded_at: datetime
    projection: ClaimProjection
    sources: tuple[LibraryEntrySource, ...] = ()


class LibraryEntryClaimHistory(LibraryEntryClaim):
    superseded_by_claim_id: UUID
    supersession_reason: str


class LibraryEntry(LibraryEntrySummary):
    claims: tuple[LibraryEntryClaim, ...] = ()
    claim_history: tuple[LibraryEntryClaimHistory, ...] = ()
    sources: tuple[LibraryEntrySource, ...] = ()
    roles: tuple[LibraryEntryRole, ...] = ()


class LibraryEntryRepository(Protocol):
    def list(self) -> tuple[LibraryEntrySummary, ...]: ...
    def get(self, entry_id: UUID) -> LibraryEntry | None: ...


class LibraryEntryService:
    def __init__(self, repository: LibraryEntryRepository) -> None:
        self._repository = repository

    def list(self) -> tuple[LibraryEntrySummary, ...]:
        return self._repository.list()

    def get(self, entry_id: UUID) -> LibraryEntry | None:
        return self._repository.get(entry_id)
