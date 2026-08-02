"""Campaign Core HTTP application factory."""

from typing import Annotated
from uuid import UUID

from fastapi import FastAPI, HTTPException, Path, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field

from dm_assistant_core import __version__
from dm_assistant_core.adapters.postgres import (
    PostgresCandidateProposalRepository,
    PostgresChangeSetRepository,
    PostgresDatabase,
    PostgresImportReviewRepository,
    PostgresMarkdownImportRepository,
    PostgresRetrievalRepository,
)
from dm_assistant_core.application import (
    ApproveCandidateProposalCommand,
    CandidateDisposition,
    CandidateDispositionResult,
    CandidateListQuery,
    CandidateProposalApproval,
    CandidateProposalError,
    CandidateProposalForbiddenError,
    CandidateProposalService,
    CandidateProposalVersion,
    ChangeSetApplicationService,
    CreateCandidateProposalCommand,
    DispositionCandidateCommand,
    ImportCandidatePage,
    ImportCandidateReview,
    ImportReviewForbiddenError,
    ImportReviewItemPage,
    ImportReviewService,
    ImportRunDetail,
    ImportRunListQuery,
    ImportRunPage,
    MarkdownImportService,
    ProposalItemDecision,
    RetrievalService,
    ReviewItemListQuery,
    ReviseCandidateProposalCommand,
)
from dm_assistant_core.config import Settings, get_settings
from dm_assistant_core.domain import (
    ApplyChangeSetCommand,
    ChangeSetReceipt,
    ChangeSetRejectedError,
    ClaimState,
    RequesterRole,
    RequesterVisibility,
    RetrievalQuery,
    RetrievalResult,
    Visibility,
)
from dm_assistant_core.domain.change_sets import Sha256
from dm_assistant_core.importer import (
    CandidateAuthority,
    ImportClassification,
    ImportReceipt,
    MarkdownScanBatch,
)
from dm_assistant_core.importer.models import ImportRejectedError


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


class ApplyChangeSetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reviewed_version: int = Field(gt=0)
    approval_id: UUID
    content_hash: Sha256


class ReviseCandidateProposalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: tuple[ProposalItemDecision, ...] = Field(min_length=1)


class ApproveCandidateProposalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reviewed_version: int = Field(gt=0)
    content_hash: Sha256
    item_ids: tuple[UUID, ...] = Field(min_length=1)
    idempotency_key: str = Field(min_length=1)


class DispositionCandidateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    disposition: CandidateDisposition
    reason: str = Field(min_length=1)


def create_app(
    settings: Settings | None = None,
    change_sets: ChangeSetApplicationService | None = None,
    imports: MarkdownImportService | None = None,
    import_reviews: ImportReviewService | None = None,
    retrieval: RetrievalService | None = None,
    candidate_proposals: CandidateProposalService | None = None,
) -> FastAPI:
    """Build the transport layer without importing persistence into the domain."""

    active_settings = settings or get_settings()
    active_change_sets = change_sets or ChangeSetApplicationService(
        PostgresChangeSetRepository(PostgresDatabase(active_settings.database_dsn))
    )
    active_imports = imports or MarkdownImportService(
        PostgresMarkdownImportRepository(PostgresDatabase(active_settings.database_dsn))
    )
    active_import_reviews = import_reviews or ImportReviewService(
        PostgresImportReviewRepository(PostgresDatabase(active_settings.database_dsn))
    )
    active_retrieval = retrieval or RetrievalService(
        PostgresRetrievalRepository(PostgresDatabase(active_settings.database_dsn))
    )
    active_candidate_proposals = candidate_proposals or CandidateProposalService(
        PostgresCandidateProposalRepository(PostgresDatabase(active_settings.database_dsn))
    )
    app = FastAPI(title="DM Assistant Campaign Core", version=__version__)
    if active_settings.allowed_cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(active_settings.allowed_cors_origins),
            allow_credentials=False,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["Content-Type"],
        )
    app.state.settings = active_settings
    app.state.change_sets = active_change_sets
    app.state.imports = active_imports
    app.state.import_reviews = active_import_reviews
    app.state.retrieval = active_retrieval
    app.state.candidate_proposals = active_candidate_proposals

    @app.get("/health", response_model=HealthResponse, tags=["operations"])
    def health() -> HealthResponse:
        return HealthResponse(status="ok", service="campaign-core", version=__version__)

    @app.post(
        "/change-sets/{change_set_id}/apply",
        response_model=ChangeSetReceipt,
        tags=["campaign"],
    )
    def apply_change_set(
        request: ApplyChangeSetRequest,
        change_set_id: Annotated[UUID, Path()],
    ) -> ChangeSetReceipt:
        command = ApplyChangeSetCommand(
            change_set_id=change_set_id,
            reviewed_version=request.reviewed_version,
            approval_id=request.approval_id,
            content_hash=request.content_hash,
        )
        try:
            return active_change_sets.apply(command)
        except ChangeSetRejectedError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.post(
        "/imports/markdown/scan",
        response_model=ImportReceipt,
        tags=["imports"],
    )
    def ingest_markdown_scan(batch: MarkdownScanBatch) -> ImportReceipt:
        try:
            return active_imports.ingest(batch)
        except ImportRejectedError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.get("/imports/runs", response_model=ImportRunPage, tags=["imports"])
    def list_import_runs(
        requester_role: Annotated[RequesterRole, Query()],
        character_id: Annotated[str | None, Query()] = None,
        status: Annotated[str | None, Query()] = None,
        root_identifier: Annotated[str | None, Query()] = None,
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> ImportRunPage:
        requester = _requester(requester_role, character_id)
        try:
            return active_import_reviews.list_runs(
                ImportRunListQuery(
                    requester=requester,
                    status=status,
                    root_identifier=root_identifier,
                    limit=limit,
                    offset=offset,
                )
            )
        except ImportReviewForbiddenError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error

    @app.get("/imports/runs/{run_id}", response_model=ImportRunDetail, tags=["imports"])
    def get_import_run(
        run_id: Annotated[UUID, Path()],
        requester_role: Annotated[RequesterRole, Query()],
        character_id: Annotated[str | None, Query()] = None,
    ) -> ImportRunDetail:
        try:
            result = active_import_reviews.get_run(run_id, _requester(requester_role, character_id))
        except ImportReviewForbiddenError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error
        if result is None:
            raise HTTPException(status_code=404, detail="import run not found")
        return result

    @app.get("/imports/candidates", response_model=ImportCandidatePage, tags=["imports"])
    def list_import_candidates(
        requester_role: Annotated[RequesterRole, Query()],
        character_id: Annotated[str | None, Query()] = None,
        run_id: Annotated[UUID | None, Query()] = None,
        status: Annotated[str | None, Query()] = None,
        review_status: Annotated[str | None, Query()] = None,
        classification: Annotated[ImportClassification | None, Query()] = None,
        state: Annotated[ClaimState | None, Query()] = None,
        authority: Annotated[CandidateAuthority | None, Query()] = None,
        visibility: Annotated[Visibility | None, Query()] = None,
        source: Annotated[str | None, Query()] = None,
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> ImportCandidatePage:
        return active_import_reviews.list_candidates(
            CandidateListQuery(
                requester=_requester(requester_role, character_id),
                run_id=run_id,
                status=status,
                review_status=review_status,
                classification=classification,
                state=state,
                authority=authority,
                visibility=visibility,
                source=source,
                limit=limit,
                offset=offset,
            )
        )

    @app.get(
        "/imports/candidates/{candidate_id}",
        response_model=ImportCandidateReview,
        tags=["imports"],
    )
    def get_import_candidate(
        candidate_id: Annotated[UUID, Path()],
        requester_role: Annotated[RequesterRole, Query()],
        character_id: Annotated[str | None, Query()] = None,
    ) -> ImportCandidateReview:
        result = active_import_reviews.get_candidate(
            candidate_id, _requester(requester_role, character_id)
        )
        if result is None:
            raise HTTPException(status_code=404, detail="import candidate not found")
        return result

    @app.get("/imports/reviews", response_model=ImportReviewItemPage, tags=["imports"])
    def list_import_reviews(
        requester_role: Annotated[RequesterRole, Query()],
        character_id: Annotated[str | None, Query()] = None,
        run_id: Annotated[UUID | None, Query()] = None,
        kind: Annotated[str | None, Query()] = None,
        status: Annotated[str | None, Query()] = None,
        classification: Annotated[ImportClassification | None, Query()] = None,
        state: Annotated[ClaimState | None, Query()] = None,
        authority: Annotated[CandidateAuthority | None, Query()] = None,
        visibility: Annotated[Visibility | None, Query()] = None,
        source: Annotated[str | None, Query()] = None,
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> ImportReviewItemPage:
        try:
            return active_import_reviews.list_reviews(
                ReviewItemListQuery(
                    requester=_requester(requester_role, character_id),
                    run_id=run_id,
                    kind=kind,
                    status=status,
                    classification=classification,
                    state=state,
                    authority=authority,
                    visibility=visibility,
                    source=source,
                    limit=limit,
                    offset=offset,
                )
            )
        except ImportReviewForbiddenError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error

    @app.post(
        "/imports/proposals",
        response_model=CandidateProposalVersion,
        tags=["imports"],
    )
    def create_candidate_proposal(
        request: CreateCandidateProposalCommand,
        requester_role: Annotated[RequesterRole, Query()],
        character_id: Annotated[str | None, Query()] = None,
    ) -> CandidateProposalVersion:
        try:
            return active_candidate_proposals.create(
                request, _requester(requester_role, character_id)
            )
        except CandidateProposalForbiddenError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error
        except CandidateProposalError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.get(
        "/imports/proposals/{proposal_id}",
        response_model=CandidateProposalVersion,
        tags=["imports"],
    )
    def get_candidate_proposal(
        proposal_id: Annotated[UUID, Path()],
        requester_role: Annotated[RequesterRole, Query()],
        character_id: Annotated[str | None, Query()] = None,
    ) -> CandidateProposalVersion:
        try:
            result = active_candidate_proposals.get(
                proposal_id, _requester(requester_role, character_id)
            )
        except CandidateProposalForbiddenError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error
        if result is None:
            raise HTTPException(status_code=404, detail="candidate proposal not found")
        return result

    @app.post(
        "/imports/proposals/{proposal_id}/versions",
        response_model=CandidateProposalVersion,
        tags=["imports"],
    )
    def revise_candidate_proposal(
        request: ReviseCandidateProposalRequest,
        proposal_id: Annotated[UUID, Path()],
        requester_role: Annotated[RequesterRole, Query()],
        character_id: Annotated[str | None, Query()] = None,
    ) -> CandidateProposalVersion:
        try:
            return active_candidate_proposals.revise(
                ReviseCandidateProposalCommand(proposal_id=proposal_id, items=request.items),
                _requester(requester_role, character_id),
            )
        except CandidateProposalForbiddenError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error
        except CandidateProposalError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.post(
        "/imports/proposals/{proposal_id}/approvals",
        response_model=CandidateProposalApproval,
        tags=["imports"],
    )
    def approve_candidate_proposal(
        request: ApproveCandidateProposalRequest,
        proposal_id: Annotated[UUID, Path()],
        requester_role: Annotated[RequesterRole, Query()],
        character_id: Annotated[str | None, Query()] = None,
    ) -> CandidateProposalApproval:
        try:
            return active_candidate_proposals.approve(
                ApproveCandidateProposalCommand(
                    proposal_id=proposal_id,
                    reviewed_version=request.reviewed_version,
                    content_hash=request.content_hash,
                    item_ids=request.item_ids,
                    idempotency_key=request.idempotency_key,
                ),
                _requester(requester_role, character_id),
            )
        except CandidateProposalForbiddenError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error
        except CandidateProposalError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.post(
        "/imports/candidates/{candidate_id}/disposition",
        response_model=CandidateDispositionResult,
        tags=["imports"],
    )
    def disposition_candidate(
        request: DispositionCandidateRequest,
        candidate_id: Annotated[UUID, Path()],
        requester_role: Annotated[RequesterRole, Query()],
        character_id: Annotated[str | None, Query()] = None,
    ) -> CandidateDispositionResult:
        try:
            return active_candidate_proposals.disposition(
                DispositionCandidateCommand(
                    candidate_id=candidate_id,
                    disposition=request.disposition,
                    reason=request.reason,
                ),
                _requester(requester_role, character_id),
            )
        except CandidateProposalForbiddenError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error
        except CandidateProposalError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.post(
        "/retrieval/query",
        response_model=RetrievalResult,
        tags=["retrieval"],
    )
    def retrieve(query: RetrievalQuery) -> RetrievalResult:
        return active_retrieval.query(query)

    return app


def _requester(role: RequesterRole, character_id: str | None) -> RequesterVisibility:
    try:
        return RequesterVisibility(role=role, character_id=character_id)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
