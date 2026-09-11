"""Exact human-controlled entity kind and tag proposals."""

from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from dm_assistant_core.application.candidate_proposals import (
    ApproveCandidateProposalCommand,
    CandidateProposalApproval,
)
from dm_assistant_core.domain import EntityKind, RequesterRole, RequesterVisibility, normalize_tags
from dm_assistant_core.domain.change_sets import Sha256


class ProposeEntityMetadataCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    entity_id: UUID
    entity_kind: EntityKind
    tags: tuple[str, ...] = ()

    @field_validator("tags")
    @classmethod
    def require_normalized_unique_tags(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return normalize_tags(value)


class EntityMetadataProposalItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    item_id: UUID
    target_id: UUID
    before: dict[str, Any]
    after: dict[str, Any]


class EntityMetadataProposalVersion(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    proposal_id: UUID
    workflow_session_id: UUID
    status: str
    version_id: UUID
    version_number: int
    content_hash: Sha256
    created_at: str
    item: EntityMetadataProposalItem


class EntityMetadataProposalError(ValueError):
    """An entity metadata proposal failed a deterministic rule."""


class EntityMetadataProposalRepository(Protocol):
    def create(self, command: ProposeEntityMetadataCommand) -> EntityMetadataProposalVersion: ...

    def get(self, proposal_id: UUID) -> EntityMetadataProposalVersion | None: ...

    def approve(self, command: ApproveCandidateProposalCommand) -> CandidateProposalApproval: ...


class EntityMetadataProposalService:
    def __init__(self, repository: EntityMetadataProposalRepository) -> None:
        self._repository = repository

    @staticmethod
    def _require_dm(requester: RequesterVisibility) -> None:
        if requester.role is not RequesterRole.DM:
            raise PermissionError("entity metadata decisions are DM-only")

    def create(
        self, command: ProposeEntityMetadataCommand, requester: RequesterVisibility
    ) -> EntityMetadataProposalVersion:
        self._require_dm(requester)
        return self._repository.create(command)

    def get(
        self, proposal_id: UUID, requester: RequesterVisibility
    ) -> EntityMetadataProposalVersion | None:
        self._require_dm(requester)
        return self._repository.get(proposal_id)

    def approve(
        self, command: ApproveCandidateProposalCommand, requester: RequesterVisibility
    ) -> CandidateProposalApproval:
        self._require_dm(requester)
        return self._repository.approve(command)
