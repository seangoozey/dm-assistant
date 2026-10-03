"""Human-controlled candidate dispositions and immutable proposal commands."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Any, Literal, Protocol
from uuid import UUID

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from dm_assistant_core.domain import (
    ClaimState,
    EntityKind,
    RequesterRole,
    RequesterVisibility,
    Visibility,
    normalize_tags,
)
from dm_assistant_core.domain.change_sets import Sha256
from dm_assistant_core.domain.chronology import CampaignDate
from dm_assistant_core.domain.rules_elements import RulesElementMechanics
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
    entity_kind: EntityKind = Field(validation_alias=AliasChoices("entity_kind", "entity_type"))
    canonical_name: NonEmptyText
    tags: tuple[str, ...] = ()
    rules_element_mechanics: RulesElementMechanics | None = None

    @field_validator("tags")
    @classmethod
    def require_normalized_unique_tags(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return normalize_tags(value)

    @model_validator(mode="after")
    def require_mechanics_for_rules_element(self) -> CreateEntityDecision:
        if self.entity_kind is EntityKind.RULES_ELEMENT and self.rules_element_mechanics is None:
            raise ValueError("a rules_element entity requires rules_element_mechanics")
        if (
            self.entity_kind is not EntityKind.RULES_ELEMENT
            and self.rules_element_mechanics is not None
        ):
            raise ValueError("rules_element_mechanics is valid only for rules_element entities")
        return self


class CreateClaimDecision(BaseModel):
    """An explicit claim target and lifecycle decision bound to source or extraction text."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    mutation_kind: Literal["create_claim"]
    candidate_id: UUID
    candidate_extraction_id: UUID | None = None
    evidence_revision_id: UUID
    target_id: UUID
    subject_entity_id: UUID | None = None
    # TKT-0148 guardrail: the explicit no-owner choice. A subjectless claim
    # only commits WITH this disposition (receipted via claim_owner_dispositions).
    owner_disposition: NonEmptyText | None = None
    object_entity_id: UUID | None = None
    related_entity_ids: tuple[UUID, ...] = ()
    assertion_text: NonEmptyText | None = None
    predicate: NonEmptyText | None = None
    state: ClaimState
    authority: CandidateAuthority
    visibility: Visibility
    confidence: Decimal = Field(ge=0, le=1)
    is_conditional: bool
    predicts_subject_action: bool
    condition_text: NonEmptyText | None = None
    condition_reference_type: Literal["claim", "event", "plan", "entity"] | None = None
    condition_reference_id: UUID | None = None
    recorded_at: datetime
    effective_from: CampaignDate | None = None
    effective_until: CampaignDate | None = None
    expected_at: CampaignDate | None = None
    observed_at: CampaignDate | None = None

    @field_validator("related_entity_ids")
    @classmethod
    def require_distinct_related_entities(cls, value: tuple[UUID, ...]) -> tuple[UUID, ...]:
        if len(set(value)) != len(value):
            raise ValueError("related entity IDs must be distinct")
        return value

    @field_validator("recorded_at")
    @classmethod
    def require_explicit_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("audit recorded_at requires an explicit timezone")
        return value

    @model_validator(mode="after")
    def require_explicit_condition_trigger(self) -> CreateClaimDecision:
        reference_complete = (self.condition_reference_type is None) == (
            self.condition_reference_id is None
        )
        if not reference_complete:
            raise ValueError("condition reference type and ID must be supplied together")
        has_trigger = self.condition_text is not None or self.condition_reference_id is not None
        if self.is_conditional and not has_trigger:
            raise ValueError("conditional claim requires an explicit trigger")
        if not self.is_conditional and has_trigger:
            raise ValueError("non-conditional claim cannot carry a condition trigger")
        if self.state is ClaimState.POSSIBLE and self.is_conditional:
            raise ValueError("possible claims cannot be conditional")
        return self


ProposalItemDecision = Annotated[
    CreateEntityDecision | CreateClaimDecision, Field(discriminator="mutation_kind")
]


class CreateCandidateProposalCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    workflow_session_id: UUID | None = None
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


def assertions_require_conflict_review(
    proposed: str,
    proposed_predicate: str | None,
    existing: str,
    existing_predicate: str | None,
) -> bool:
    """Deterministic near-restatement gate over claim text.

    Narrow by design (ADR-0018): it catches an identical term set or a
    heavily overlapping restatement under the same predicate — it does NOT
    understand semantic contradiction. Shared by proposal validation and the
    Promotion Pipeline's derive pre-check so preview and commit agree.
    """
    import re

    def terms(value: str) -> set[str]:
        return {word for word in re.findall(r"[a-z0-9]+", value.casefold()) if len(word) > 2}

    proposed_terms = terms(proposed)
    existing_terms = terms(existing)
    if proposed_terms == existing_terms:
        return True
    if proposed_predicate is None or existing_predicate is None:
        return False
    if proposed_predicate.casefold().strip() != existing_predicate.casefold().strip():
        return False
    union = proposed_terms | existing_terms
    return bool(union) and len(proposed_terms & existing_terms) / len(union) >= 0.35


class CandidateProposalForbiddenError(PermissionError):
    """Only the DM may make candidate disposition and promotion decisions."""


class CandidateProposalRepository(Protocol):
    def create(self, command: CreateCandidateProposalCommand) -> CandidateProposalVersion: ...

    def revise(self, command: ReviseCandidateProposalCommand) -> CandidateProposalVersion: ...

    def get(self, proposal_id: UUID) -> CandidateProposalVersion | None: ...

    def get_for_candidate(self, candidate_id: UUID) -> CandidateProposalVersion | None: ...

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

    def get_for_candidate(
        self, candidate_id: UUID, requester: RequesterVisibility
    ) -> CandidateProposalVersion | None:
        self._require_dm(requester)
        return self._repository.get_for_candidate(candidate_id)

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
