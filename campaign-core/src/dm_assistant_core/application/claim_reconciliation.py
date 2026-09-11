"""Reviewed, append-only reconciliation of overlapping canonical claims."""

from enum import StrEnum
from typing import Literal, Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from dm_assistant_core.domain import ClaimState, RequesterRole, RequesterVisibility, Visibility
from dm_assistant_core.domain.change_sets import Sha256


class ReconciliationDecision(StrEnum):
    RETAIN_BOTH = "retain_both"
    DUPLICATE = "duplicate"
    SUPERSEDE = "supersede"


class ClaimEvidenceSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    source_span_id: UUID
    source_path: str
    section_path: str
    start_offset: int
    end_offset: int
    evidence_role: str


class ClaimDateParts(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    year: int
    month: int | None = Field(default=None, ge=1, le=12)
    day: int | None = Field(default=None, ge=1, le=31)

    @model_validator(mode="after")
    def require_month_for_day(self) -> "ClaimDateParts":
        if self.day is not None and self.month is None:
            raise ValueError("campaign date day requires a month")
        return self


class ClaimSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    claim_id: UUID
    assertion_text: str
    state: str
    authority: str
    visibility: str
    recorded_at: str
    condition_text: str | None = None
    effective_from: ClaimDateParts | None = None
    effective_until: ClaimDateParts | None = None
    expected: ClaimDateParts | None = None
    observed: ClaimDateParts | None = None
    source_paths: tuple[str, ...]
    evidence: tuple[ClaimEvidenceSnapshot, ...] = ()
    snapshot_hash: Sha256
    is_current: bool


class ClaimReconciliationReview(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    superseding: ClaimSnapshot
    superseded: ClaimSnapshot


class ClaimOverlap(ClaimReconciliationReview):
    similarity: float = Field(ge=0, le=1)


class ApplyClaimReconciliationCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    superseding_claim_id: UUID
    superseded_claim_id: UUID
    superseding_snapshot_hash: Sha256
    superseded_snapshot_hash: Sha256
    decision: ReconciliationDecision
    reason: str = Field(min_length=1)
    idempotency_key: str = Field(min_length=1)


class ClaimReconciliationReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    receipt_id: UUID
    change_set_id: UUID
    decision: ReconciliationDecision
    idempotent_replay: bool


class CorrectClaimCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    claim_id: UUID
    snapshot_hash: Sha256
    assertion_text: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    idempotency_key: str = Field(min_length=1)


class ClaimReplacementDraft(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    assertion_text: str = Field(min_length=1)
    state: ClaimState
    authority: Literal[
        "real_play", "dm_correction", "explicit_lore", "npc_intention",
        "preparation", "brainstorm", "unclassified", "derived",
    ]
    visibility: Visibility
    condition_text: str | None = None
    effective_from: ClaimDateParts | None = None
    effective_until: ClaimDateParts | None = None
    expected: ClaimDateParts | None = None
    observed: ClaimDateParts | None = None

    @model_validator(mode="after")
    def validate_truth_dimensions(self) -> "ClaimReplacementDraft":
        if self.state is ClaimState.OBSERVED and self.observed is None:
            raise ValueError("observed claims require an observed campaign date")
        if (
            self.effective_from
            and self.effective_until
            and self.effective_until.year < self.effective_from.year
        ):
            raise ValueError("effective-until year cannot precede effective-from year")
        return self


class ReplaceClaimCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    claim_id: UUID
    snapshot_hash: Sha256
    replacements: tuple[ClaimReplacementDraft, ...] = Field(min_length=1)
    reason: str = Field(min_length=1)
    idempotency_key: str = Field(min_length=1)


class ClaimReplacementReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    receipt_id: UUID
    change_set_id: UUID
    original_claim_id: UUID
    replacement_claim_ids: tuple[UUID, ...]
    idempotent_replay: bool


class ClaimCorrectionReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    receipt_id: UUID
    change_set_id: UUID
    original_claim_id: UUID
    replacement_claim_id: UUID
    idempotent_replay: bool


class ClaimReconciliationError(ValueError):
    pass


class ClaimReconciliationRepository(Protocol):
    def get(self, claim_id: UUID) -> ClaimSnapshot: ...
    def discover(self, limit: int) -> tuple[ClaimOverlap, ...]: ...
    def review(self, superseding: UUID, superseded: UUID) -> ClaimReconciliationReview: ...
    def apply(self, command: ApplyClaimReconciliationCommand) -> ClaimReconciliationReceipt: ...
    def correct(self, command: CorrectClaimCommand) -> ClaimCorrectionReceipt: ...
    def replace(self, command: ReplaceClaimCommand) -> ClaimReplacementReceipt: ...


class ClaimReconciliationService:
    def __init__(self, repository: ClaimReconciliationRepository) -> None:
        self._repository = repository

    @staticmethod
    def _dm(requester: RequesterVisibility) -> None:
        if requester.role is not RequesterRole.DM:
            raise PermissionError("claim reconciliation is DM-only")

    def review(
        self, superseding: UUID, superseded: UUID, requester: RequesterVisibility
    ) -> ClaimReconciliationReview:
        self._dm(requester)
        if superseding == superseded:
            raise ClaimReconciliationError("a claim cannot supersede itself")
        return self._repository.review(superseding, superseded)

    def get(self, claim_id: UUID, requester: RequesterVisibility) -> ClaimSnapshot:
        self._dm(requester)
        return self._repository.get(claim_id)

    def discover(
        self, limit: int, requester: RequesterVisibility
    ) -> tuple[ClaimOverlap, ...]:
        self._dm(requester)
        return self._repository.discover(limit)

    def apply(
        self, command: ApplyClaimReconciliationCommand, requester: RequesterVisibility
    ) -> ClaimReconciliationReceipt:
        self._dm(requester)
        if command.superseding_claim_id == command.superseded_claim_id:
            raise ClaimReconciliationError("a claim cannot supersede itself")
        return self._repository.apply(command)

    def correct(
        self, command: CorrectClaimCommand, requester: RequesterVisibility
    ) -> ClaimCorrectionReceipt:
        self._dm(requester)
        return self._repository.correct(command)

    def replace(
        self, command: ReplaceClaimCommand, requester: RequesterVisibility
    ) -> ClaimReplacementReceipt:
        self._dm(requester)
        return self._repository.replace(command)
