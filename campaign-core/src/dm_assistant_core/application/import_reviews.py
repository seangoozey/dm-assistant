"""Typed read-only use cases for imported evidence and review queues."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from dm_assistant_core.domain import ClaimState, RequesterRole, RequesterVisibility, Visibility
from dm_assistant_core.importer import CandidateAuthority, ImportClassification, ImportReceipt


class ImportReviewForbiddenError(PermissionError):
    """The requester cannot inspect the requested import-review material."""


class ImportRunListQuery(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    requester: RequesterVisibility
    status: str | None = None
    root_identifier: str | None = None
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class ImportRunSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    import_run_id: UUID
    root_identifier: str
    snapshot_at: datetime
    importer_version: str
    parser_version: str
    path_policy_version: str
    status: str
    admitted_file_count: int
    excluded_path_count: int
    candidate_count: int
    review_count: int
    outcome_counts: dict[str, int]
    warning_counts: dict[str, int]


class ImportRunPage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    items: tuple[ImportRunSummary, ...]
    total: int = Field(ge=0)
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)


class ImportRunDetail(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    summary: ImportRunSummary
    receipt: ImportReceipt


class CandidateListQuery(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    requester: RequesterVisibility
    run_id: UUID | None = None
    status: str | None = None
    review_status: str | None = None
    classification: ImportClassification | None = None
    state: ClaimState | None = None
    authority: CandidateAuthority | None = None
    visibility: Visibility | None = None
    source: str | None = None
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class CandidateEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source_revision_id: UUID
    source_path: str
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    classification: ImportClassification
    section: str
    start_offset: int = Field(ge=0)
    end_offset: int = Field(ge=0)
    excerpt: str


class ImportCandidateReview(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_id: UUID
    source_document_id: UUID
    first_seen_import_run_id: UUID
    assertion_text: str
    state: ClaimState
    authority: CandidateAuthority
    visibility: Visibility
    conditional: bool
    predicts_subject_action: bool
    evidence_only: bool
    status: str
    review_status: str = "pending"
    extractor_version: str
    created_at: datetime
    updated_at: datetime
    evidence: tuple[CandidateEvidence, ...]


class ImportCandidatePage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    items: tuple[ImportCandidateReview, ...]
    total: int = Field(ge=0)
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)


class ReviewItemListQuery(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    requester: RequesterVisibility
    run_id: UUID | None = None
    kind: str | None = None
    status: str | None = None
    classification: ImportClassification | None = None
    state: ClaimState | None = None
    authority: CandidateAuthority | None = None
    visibility: Visibility | None = None
    source: str | None = None
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class ImportReviewItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    review_id: UUID
    kind: str
    status: str
    subject_type: str
    subject_id: UUID
    details: dict[str, Any]
    opened_by_import_run_id: UUID
    created_at: datetime
    updated_at: datetime
    source_path: str | None = None
    classification: str | None = None


class ImportReviewItemPage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    items: tuple[ImportReviewItem, ...]
    total: int = Field(ge=0)
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)


class ImportReviewRepository(Protocol):
    def list_runs(self, query: ImportRunListQuery) -> ImportRunPage: ...

    def get_run(self, run_id: UUID) -> ImportRunDetail | None: ...

    def list_candidates(self, query: CandidateListQuery) -> ImportCandidatePage: ...

    def get_candidate(
        self, candidate_id: UUID, requester: RequesterVisibility
    ) -> ImportCandidateReview | None: ...

    def list_reviews(self, query: ReviewItemListQuery) -> ImportReviewItemPage: ...


class ImportReviewService:
    def __init__(self, repository: ImportReviewRepository) -> None:
        self._repository = repository

    @staticmethod
    def require_dm(requester: RequesterVisibility) -> None:
        if requester.role is not RequesterRole.DM:
            raise ImportReviewForbiddenError("import receipts and review items are DM-only")

    def list_runs(self, query: ImportRunListQuery) -> ImportRunPage:
        self.require_dm(query.requester)
        return self._repository.list_runs(query)

    def get_run(self, run_id: UUID, requester: RequesterVisibility) -> ImportRunDetail | None:
        self.require_dm(requester)
        return self._repository.get_run(run_id)

    def list_candidates(self, query: CandidateListQuery) -> ImportCandidatePage:
        return self._repository.list_candidates(query)

    def get_candidate(
        self, candidate_id: UUID, requester: RequesterVisibility
    ) -> ImportCandidateReview | None:
        return self._repository.get_candidate(candidate_id, requester)

    def list_reviews(self, query: ReviewItemListQuery) -> ImportReviewItemPage:
        self.require_dm(query.requester)
        return self._repository.list_reviews(query)
