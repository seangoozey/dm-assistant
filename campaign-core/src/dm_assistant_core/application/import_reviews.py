"""Typed read-only use cases for imported evidence and review queues."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal, Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from dm_assistant_core.domain import ClaimState, RequesterRole, RequesterVisibility, Visibility
from dm_assistant_core.domain.extraction import SubjectResolution
from dm_assistant_core.importer import CandidateAuthority, ImportClassification, ImportReceipt


class ImportReviewForbiddenError(PermissionError):
    """The requester cannot inspect the requested import-review material."""


class SourceReviewDispositionError(ValueError):
    """A source review cannot be dispositioned as requested."""


class DispositionSourceReviewCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    review_id: UUID
    decision: Literal["acknowledged", "content_consumed", "excluded_by_scope"]
    reason: str = Field(min_length=1)


class SourceReviewDispositionResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    disposition_id: UUID
    review_id: UUID
    decision: str
    reason: str
    created_at: datetime


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
    in_game_date: dict[str, Any] | None = None
    mentions: tuple[dict[str, Any], ...] = ()


class CandidateExtractionReview(BaseModel):
    """An AI-extracted claim dimension surfaced for human review."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    extraction_id: UUID
    subject: str = Field(min_length=1)
    subject_resolution: SubjectResolution = SubjectResolution.NAMED_IDENTITY
    predicate: str | None = Field(default=None, min_length=1)
    object_entity: str | None = None
    assertion_text: str = Field(min_length=1)
    supporting_excerpt: str = Field(min_length=1)
    state: ClaimState
    authority: CandidateAuthority
    visibility: Visibility
    confidence: Decimal = Field(ge=0, le=1)
    extractor_version: str = Field(min_length=1)
    source_segment_ids: tuple[str, ...]


class CandidateExtractionSegmentReview(BaseModel):
    """One deterministic source segment and its extraction disposition."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    segment_id: str
    text: str
    start_offset: int
    end_offset: int
    disposition: str
    claim_indexes: tuple[int, ...] = ()


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
    extractions: tuple[CandidateExtractionReview, ...] = ()
    extraction_segments: tuple[CandidateExtractionSegmentReview, ...] = ()


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


class SourceDocumentSummary(BaseModel):
    """A source document with aggregated review/extraction state for the tree view."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    document_id: UUID
    path: str = Field(min_length=1)
    classification: ImportClassification
    candidate_count: int = Field(ge=0)
    extraction_count: int = Field(ge=0)
    open_review_count: int = Field(ge=0)
    missing_source: bool = False
    document_type: str | None = None
    title: str | None = None
    session_date: str | None = None
    capture_mode: str | None = None


ClaimProjection = Literal["real_play", "player_plan", "npc_plan", "dm_plan", "lore_fact"]


class SourceDocumentClaim(BaseModel):
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
    source_excerpt: str | None = None


class SourceDocumentClaimHistory(SourceDocumentClaim):
    superseded_by_claim_id: UUID
    supersession_reason: str


class SourceDocumentContent(BaseModel):
    """The raw text content of a source document for rendering its Markdown."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    document_id: UUID
    path: str = Field(min_length=1)
    source_revision_id: UUID
    content: str
    document_type: str | None = None
    title: str | None = None
    session_date: date | None = None
    in_game_date: dict[str, Any] | None = None
    capture_mode: str | None = None
    capture_id: UUID | None = None
    mentions: tuple[dict[str, Any], ...] = ()
    canonical_claims: tuple[SourceDocumentClaim, ...] = ()
    claim_history: tuple[SourceDocumentClaimHistory, ...] = ()


class SourceDocumentPage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    items: tuple[SourceDocumentSummary, ...]
    total: int = Field(ge=0)
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)


class SourceDocumentListQuery(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    requester: RequesterVisibility
    limit: int = Field(default=200, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


class ImportReviewRepository(Protocol):
    def list_runs(self, query: ImportRunListQuery) -> ImportRunPage: ...

    def get_run(self, run_id: UUID) -> ImportRunDetail | None: ...

    def list_candidates(self, query: CandidateListQuery) -> ImportCandidatePage: ...

    def get_candidate(
        self, candidate_id: UUID, requester: RequesterVisibility
    ) -> ImportCandidateReview | None: ...

    def list_reviews(self, query: ReviewItemListQuery) -> ImportReviewItemPage: ...

    def list_source_documents(self, query: SourceDocumentListQuery) -> SourceDocumentPage: ...

    def get_source_document_content(self, document_id: UUID) -> SourceDocumentContent | None: ...

    def disposition_source_review(
        self, command: DispositionSourceReviewCommand
    ) -> SourceReviewDispositionResult: ...


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

    def list_source_documents(self, query: SourceDocumentListQuery) -> SourceDocumentPage:
        self.require_dm(query.requester)
        return self._repository.list_source_documents(query)

    def get_source_document_content(
        self, document_id: UUID, requester: RequesterVisibility
    ) -> SourceDocumentContent | None:
        self.require_dm(requester)
        return self._repository.get_source_document_content(document_id)

    def disposition_source_review(
        self, command: DispositionSourceReviewCommand, requester: RequesterVisibility
    ) -> SourceReviewDispositionResult:
        self.require_dm(requester)
        return self._repository.disposition_source_review(command)
