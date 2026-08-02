"""Human-controlled candidate dispositions and immutable proposal commands."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Any, Literal, Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from dm_assistant_core.domain import ClaimState, RequesterRole, RequesterVisibility, Visibility
from dm_assistant_core.domain.change_sets import Sha256
from dm_assistant_core.importer import CandidateAuthority

NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class CandidateDisposition(StrEnum):
    DEFERRED = "deferred"
    REJECTED = "rejected"


class CreateEntityDecision(BaseModel):
    """An explicit decision to create one new entity from selected evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    mutation_kind: Literal["create_entity"]
    candidate_id: UUID
    evidence_revision_id: UUID
    target_id: UUID
    entity_type: NonEmptyText
    canonical_name: NonEmptyText


class CreateClaimDecision(BaseModel):
    """An explicit claim target and lifecycle decision; assertion text remains source-bound."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    mutation_kind: Literal["create_claim"]
    candidate_id: UUID
    evidence_revision_id: UUID
    target_id: UUID
    subject_entity_id: UUID
    object_entity_id: UUID | None = None
    predicate: NonEmptyText
    state: ClaimState
    authority: CandidateAuthority
    visibility: Visibility
    confidence: Decimal = Field(ge=0, le=1)
    is_conditional: bool
    predicts_subject_action: bool
    recorded_at: datetime
    effective_from: datetime | None = None
    effective_until: datetime | None = None
    expected_at: datetime | None = None
    observed_at: datetime | None = None
    time_precision: str | None = None

    @field_validator(
        "recorded_at",
        "effective_from",
        "effective_until",
        "expected_at",
        "observed_at",
    )
    @classmethod
    def require_explicit_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("claim times require an explicit timezone")
        return value


ProposalItemDecision = Annotated[
    CreateEntityDecision | CreateClaimDecision, Field(discriminator="mutation_kind")
]


class CreateCandidateProposalCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    items: tuple[ProposalItemDecision, ...] = Field(min_length=1)


class ReviseCandidateProposalCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    proposal_id: UUID
    items: tuple[ProposalItemDecision, ...] = Field(min_length=1)


class ApproveCandidateProposalCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    proposal_id: UUID
    reviewed_version: int = Field(gt=0)
    content_hash: Sha256
    item_ids: tuple[UUID, ...] = Field(min_length=1)
    idempotency_key: NonEmptyText


class DispositionCandidateCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_id: UUID
    disposition: CandidateDisposition
    reason: NonEmptyText


class CandidateDispositionResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    disposition_id: UUID
    candidate_id: UUID
    review_status: CandidateDisposition
    reason: str
    created_at: datetime


class ProposalCandidateBinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_id: UUID
    source_revision_id: UUID
    source_span_id: UUID
    candidate_fingerprint: Sha256


class CandidateProposalItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    item_id: UUID
    sequence: int = Field(gt=0)
    mutation_kind: Literal["create_entity", "create_claim"]
    target_type: Literal["entity", "claim"]
    target_id: UUID
    after: dict[str, Any]
    evidence: ProposalCandidateBinding


class CandidateProposalVersion(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    proposal_id: UUID
    workflow_session_id: UUID
    status: str
    version_id: UUID
    version_number: int = Field(gt=0)
    content_hash: Sha256
    supersedes_version_id: UUID | None
    created_at: datetime
    items: tuple[CandidateProposalItem, ...] = Field(min_length=1)


class CandidateProposalApproval(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    proposal_id: UUID
    proposal_version_id: UUID
    reviewed_version: int = Field(gt=0)
    content_hash: Sha256
    approval_id: UUID
    change_set_id: UUID
    item_ids: tuple[UUID, ...] = Field(min_length=1)
    idempotency_key: str
    approved_at: datetime
    idempotent_replay: bool


class CandidateProposalError(ValueError):
    """A proposal command failed a deterministic safety or state rule."""


class CandidateProposalForbiddenError(PermissionError):
    """Only the DM may make candidate disposition and promotion decisions."""


class CandidateProposalRepository(Protocol):
    def create(self, command: CreateCandidateProposalCommand) -> CandidateProposalVersion: ...

    def revise(self, command: ReviseCandidateProposalCommand) -> CandidateProposalVersion: ...

    def get(self, proposal_id: UUID) -> CandidateProposalVersion | None: ...

    def approve(self, command: ApproveCandidateProposalCommand) -> CandidateProposalApproval: ...

    def disposition(self, command: DispositionCandidateCommand) -> CandidateDispositionResult: ...


class CandidateProposalService:
    def __init__(self, repository: CandidateProposalRepository) -> None:
        self._repository = repository

    @staticmethod
    def _require_dm(requester: RequesterVisibility) -> None:
        if requester.role is not RequesterRole.DM:
            raise CandidateProposalForbiddenError("candidate decisions are DM-only")

    def create(
        self, command: CreateCandidateProposalCommand, requester: RequesterVisibility
    ) -> CandidateProposalVersion:
        self._require_dm(requester)
        return self._repository.create(command)

    def revise(
        self, command: ReviseCandidateProposalCommand, requester: RequesterVisibility
    ) -> CandidateProposalVersion:
        self._require_dm(requester)
        return self._repository.revise(command)

    def get(
        self, proposal_id: UUID, requester: RequesterVisibility
    ) -> CandidateProposalVersion | None:
        self._require_dm(requester)
        return self._repository.get(proposal_id)

    def approve(
        self, command: ApproveCandidateProposalCommand, requester: RequesterVisibility
    ) -> CandidateProposalApproval:
        self._require_dm(requester)
        return self._repository.approve(command)

    def disposition(
        self, command: DispositionCandidateCommand, requester: RequesterVisibility
    ) -> CandidateDispositionResult:
        self._require_dm(requester)
        return self._repository.disposition(command)
