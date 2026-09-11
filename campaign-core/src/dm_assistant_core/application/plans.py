"""Human-controlled first-class plan proposals and reads."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal, Protocol
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    StringConstraints,
    field_validator,
    model_validator,
)

from dm_assistant_core.application.candidate_proposals import (
    ApproveCandidateProposalCommand,
    CandidateProposalApproval,
)
from dm_assistant_core.domain import (
    PlanKind,
    PlanLifecycle,
    RequesterRole,
    RequesterVisibility,
    Visibility,
)
from dm_assistant_core.domain.change_sets import Sha256

NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class CreatePlanCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    mutation_kind: Literal["create_plan"] = "create_plan"
    target_id: UUID
    plan_kind: PlanKind
    canonical_name: NonEmptyText
    summary: NonEmptyText
    objective: NonEmptyText | None = None
    mechanism: NonEmptyText | None = None
    intended_outcome: NonEmptyText | None = None
    visibility: Visibility = Visibility.DM_ONLY
    owner_record_id: UUID | None = None
    player_attribution: NonEmptyText | None = None
    communicated_at: datetime | None = None
    evidence_source_span_ids: tuple[UUID, ...] = ()
    related_plan_ids: tuple[UUID, ...] = ()

    @field_validator("communicated_at")
    @classmethod
    def require_explicit_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("communicated_at requires an explicit timezone")
        return value

    @model_validator(mode="after")
    def enforce_kind_boundary(self) -> CreatePlanCommand:
        if len(set(self.evidence_source_span_ids)) != len(self.evidence_source_span_ids):
            raise ValueError("plan evidence source spans must be unique")
        if len(set(self.related_plan_ids)) != len(self.related_plan_ids):
            raise ValueError("related plans must be unique")
        if self.target_id in self.related_plan_ids:
            raise ValueError("a plan cannot relate to itself")
        if self.plan_kind is PlanKind.CAMPAIGN_DIRECTION:
            if self.owner_record_id is not None:
                raise ValueError("campaign direction has no in-world or PC owner")
            if self.player_attribution is not None or self.communicated_at is not None:
                raise ValueError("campaign direction cannot carry player attribution")
        elif self.plan_kind is PlanKind.IN_WORLD_PLAN:
            if self.owner_record_id is None:
                raise ValueError("an in-world plan requires an NPC or faction owner")
            if self.player_attribution is not None or self.communicated_at is not None:
                raise ValueError("an in-world plan cannot carry player attribution")
        else:
            if self.owner_record_id is None:
                raise ValueError("a player plan requires its PC owner")
            if self.player_attribution is None or self.communicated_at is None:
                raise ValueError("a player plan requires attribution and communication time")
            if not self.evidence_source_span_ids:
                raise ValueError("a player plan requires source evidence")
        return self


class TransitionPlanCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    mutation_kind: Literal["transition_plan"] = "transition_plan"
    plan_id: UUID
    lifecycle: PlanLifecycle
    supporting_claim_ids: tuple[UUID, ...] = ()

    @model_validator(mode="after")
    def require_outcome_evidence(self) -> TransitionPlanCommand:
        if len(set(self.supporting_claim_ids)) != len(self.supporting_claim_ids):
            raise ValueError("supporting claims must be unique")
        if (
            self.lifecycle in {PlanLifecycle.COMPLETED, PlanLifecycle.FAILED}
            and not self.supporting_claim_ids
        ):
            raise ValueError("completed or failed plans require a separate observed claim")
        return self


class PlanProposalItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    item_id: UUID
    mutation_kind: Literal["create_plan", "transition_plan"]
    target_id: UUID
    before: dict[str, Any] | None
    after: dict[str, Any]


class PlanProposalVersion(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    proposal_id: UUID
    workflow_session_id: UUID
    status: str
    version_id: UUID
    version_number: int
    content_hash: Sha256
    created_at: datetime
    item: PlanProposalItem


class PlanRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    record_type: Literal["plan"] = "plan"
    plan_kind: PlanKind
    plan_kind_version: int
    canonical_name: str
    summary: str
    objective: str | None
    mechanism: str | None
    intended_outcome: str | None
    lifecycle: PlanLifecycle
    knowledge_boundary: str
    visibility: Visibility
    owner_record_id: UUID | None
    owner_kind: str | None
    owner_name: str | None
    player_attribution: str | None
    communicated_at: datetime | None
    evidence_source_span_ids: tuple[UUID, ...]
    related_plan_ids: tuple[UUID, ...]
    supporting_claim_ids: tuple[UUID, ...]


class PlanProjectionContext(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source_plan_id: UUID
    source_plan_name: str
    evidence_role: Literal["projection"] = "projection"
    establishes_outcome: Literal[False] = False
    evidence_source_span_ids: tuple[UUID, ...]


class PlanProposalError(ValueError):
    """A plan proposal failed a deterministic domain rule."""


class PlanRepository(Protocol):
    def create(self, command: CreatePlanCommand) -> PlanProposalVersion: ...
    def transition(self, command: TransitionPlanCommand) -> PlanProposalVersion: ...
    def get_proposal(self, proposal_id: UUID) -> PlanProposalVersion | None: ...
    def approve(self, command: ApproveCandidateProposalCommand) -> CandidateProposalApproval: ...
    def get(self, plan_id: UUID) -> PlanRecord | None: ...
    def list(
        self, plan_kind: PlanKind | None, lifecycle: PlanLifecycle | None
    ) -> tuple[PlanRecord, ...]: ...
    def projection_context(self, plan_id: UUID) -> PlanProjectionContext: ...


class PlanService:
    def __init__(self, repository: PlanRepository) -> None:
        self._repository = repository

    @staticmethod
    def _require_dm(requester: RequesterVisibility) -> None:
        if requester.role is not RequesterRole.DM:
            raise PermissionError("plan decisions are DM-only")

    def create(
        self, command: CreatePlanCommand, requester: RequesterVisibility
    ) -> PlanProposalVersion:
        self._require_dm(requester)
        return self._repository.create(command)

    def transition(
        self, command: TransitionPlanCommand, requester: RequesterVisibility
    ) -> PlanProposalVersion:
        self._require_dm(requester)
        return self._repository.transition(command)

    def get_proposal(
        self, proposal_id: UUID, requester: RequesterVisibility
    ) -> PlanProposalVersion | None:
        self._require_dm(requester)
        return self._repository.get_proposal(proposal_id)

    def approve(
        self, command: ApproveCandidateProposalCommand, requester: RequesterVisibility
    ) -> CandidateProposalApproval:
        self._require_dm(requester)
        return self._repository.approve(command)

    def get(self, plan_id: UUID, requester: RequesterVisibility) -> PlanRecord | None:
        self._require_dm(requester)
        return self._repository.get(plan_id)

    def list(
        self,
        requester: RequesterVisibility,
        plan_kind: PlanKind | None = None,
        lifecycle: PlanLifecycle | None = None,
    ) -> tuple[PlanRecord, ...]:
        self._require_dm(requester)
        return self._repository.list(plan_kind, lifecycle)

    def projection_context(
        self, plan_id: UUID, requester: RequesterVisibility
    ) -> PlanProjectionContext:
        self._require_dm(requester)
        return self._repository.projection_context(plan_id)
