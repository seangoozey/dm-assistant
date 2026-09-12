"""Campaign Core HTTP application factory."""

from typing import Annotated
from uuid import UUID

from fastapi import FastAPI, HTTPException, Path, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field

from dm_assistant_core import __version__
from dm_assistant_core.adapters.postgres import (
    PostgresArtifactExportRepository,
    PostgresBrainstormRepository,
    PostgresCandidateExtractionRepository,
    PostgresCandidateProposalRepository,
    PostgresChangeSetRepository,
    PostgresClaimReconciliationRepository,
    PostgresDatabase,
    PostgresEntityLookupRepository,
    PostgresEntityMetadataProposalRepository,
    PostgresImportReviewRepository,
    PostgresLibraryEntryRepository,
    PostgresMarkdownImportRepository,
    PostgresPCProfileRepository,
    PostgresPlanRepository,
    PostgresRetrievalRepository,
    PostgresSessionRunRepository,
    PostgresTaxonomyRepository,
)
from dm_assistant_core.adapters.postgres.ai_configuration import PostgresAIConfigurationRepository
from dm_assistant_core.adapters.postgres.campaign_clock import PostgresCampaignClockRepository
from dm_assistant_core.application import (
    ApproveCandidateProposalCommand,
    ArtifactExportError,
    ArtifactExportService,
    BrainstormError,
    BrainstormService,
    BrainstormSession,
    CandidateDisposition,
    CandidateDispositionResult,
    CandidateExtractionError,
    CandidateExtractionResult,
    CandidateExtractionService,
    CandidateListQuery,
    CandidateProposalApproval,
    CandidateProposalError,
    CandidateProposalForbiddenError,
    CandidateProposalService,
    CandidateProposalVersion,
    CaptureBrainstormThoughtCommand,
    ChangeSetApplicationService,
    CloseBrainstormCommand,
    CloseSessionRunCommand,
    CreateCandidateProposalCommand,
    CreatePlanCommand,
    DispositionCandidateCommand,
    DispositionSourceReviewCommand,
    EncounterProgress,
    EntityIdentity,
    EntityLookupService,
    EntityMetadataProposalError,
    EntityMetadataProposalService,
    EntityMetadataProposalVersion,
    ExportedArtifact,
    ImportCandidatePage,
    ImportCandidateReview,
    ImportReviewForbiddenError,
    ImportReviewItemPage,
    ImportReviewService,
    ImportRunDetail,
    ImportRunListQuery,
    ImportRunPage,
    LibraryEntry,
    LibraryEntryService,
    LibraryEntrySummary,
    MarkdownImportService,
    OpenSessionRunCommand,
    PCProfile,
    PCProfileError,
    PCProfileReceipt,
    PCProfileService,
    PlanProjectionContext,
    PlanProposalError,
    PlanProposalVersion,
    PlanRecord,
    PlanService,
    ProposalItemDecision,
    ProposeEntityMetadataCommand,
    RetrievalService,
    ReviewItemListQuery,
    ReviseCandidateProposalCommand,
    SaveSessionRunNoteCommand,
    SessionRun,
    SessionRunNote,
    SessionRunService,
    SourceDocumentContent,
    SourceDocumentListQuery,
    SourceDocumentPage,
    SourceReviewDispositionError,
    SourceReviewDispositionResult,
    StartBrainstormCommand,
    TaxonomyService,
    TaxonomySnapshot,
    TransitionPlanCommand,
    UpdateEncounterProgressCommand,
    UpdatePCProfileCommand,
)
from dm_assistant_core.application.ai_configuration import (
    PROMPT_VERSION,
    ActivationReceipt,
    AIConfigurationService,
    AIConfigurationSnapshot,
    ModelProfile,
)
from dm_assistant_core.application.claim_reconciliation import (
    ApplyClaimReconciliationCommand,
    ClaimCorrectionReceipt,
    ClaimOverlap,
    ClaimReconciliationError,
    ClaimReconciliationReceipt,
    ClaimReconciliationReview,
    ClaimReconciliationService,
    ClaimReplacementReceipt,
    ClaimSnapshot,
    CorrectClaimCommand,
    ReplaceClaimCommand,
)
from dm_assistant_core.application.direct_capture import (
    SessionNoteCaptureCommand,
    SessionNoteCaptureReceipt,
    SessionNoteCaptureService,
)
from dm_assistant_core.config import Settings, get_settings
from dm_assistant_core.domain import (
    ApplyChangeSetCommand,
    ChangeSetReceipt,
    ChangeSetRejectedError,
    ClaimState,
    EntityKind,
    PlanKind,
    PlanLifecycle,
    RequesterRole,
    RequesterVisibility,
    RetrievalQuery,
    RetrievalResult,
    Visibility,
)
from dm_assistant_core.domain.change_sets import Sha256
from dm_assistant_core.domain.chronology import CampaignDate
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


class ProposeEntityMetadataRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entity_kind: EntityKind
    tags: tuple[str, ...] = ()


class UpdatePCProfileRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_revision_id: UUID
    version: int = Field(ge=0)
    canonical_name: str = Field(min_length=1)
    player: str | None = None
    race: str | None = None
    sex: str | None = None
    status: str = Field(min_length=1)
    aliases: tuple[str, ...] = ()
    background: str = ""
    idempotency_key: str = Field(min_length=1)


class DeleteSessionRunNoteResponse(BaseModel):
    note_id: UUID
    deleted: bool = True


def create_app(
    settings: Settings | None = None,
    change_sets: ChangeSetApplicationService | None = None,
    imports: MarkdownImportService | None = None,
    import_reviews: ImportReviewService | None = None,
    retrieval: RetrievalService | None = None,
    candidate_proposals: CandidateProposalService | None = None,
    taxonomy: TaxonomyService | None = None,
    entity_metadata: EntityMetadataProposalService | None = None,
    entity_lookup: EntityLookupService | None = None,
    library_entries: LibraryEntryService | None = None,
    plans: PlanService | None = None,
    artifact_exports: ArtifactExportService | None = None,
    candidate_extraction: CandidateExtractionService | None = None,
    ai_configuration: AIConfigurationService | None = None,
    pc_profiles: PCProfileService | None = None,
    claim_reconciliation: ClaimReconciliationService | None = None,
    session_runs: SessionRunService | None = None,
    brainstorms: BrainstormService | None = None,
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
    if active_settings.graph_pilot_bundle and active_settings.environment == "development":
        from dm_assistant_core.application.graph_pilot import GraphPilotRetrieval
        active_retrieval = GraphPilotRetrieval(
            active_retrieval,
            PostgresRetrievalRepository(PostgresDatabase(active_settings.database_dsn)),
            active_settings.graph_pilot_bundle,
        )
    active_candidate_proposals = candidate_proposals or CandidateProposalService(
        PostgresCandidateProposalRepository(PostgresDatabase(active_settings.database_dsn))
    )
    active_taxonomy = taxonomy or TaxonomyService(
        PostgresTaxonomyRepository(PostgresDatabase(active_settings.database_dsn))
    )
    active_entity_metadata = entity_metadata or EntityMetadataProposalService(
        PostgresEntityMetadataProposalRepository(PostgresDatabase(active_settings.database_dsn))
    )
    active_entity_lookup = entity_lookup or EntityLookupService(
        PostgresEntityLookupRepository(PostgresDatabase(active_settings.database_dsn))
    )
    active_library_entries = library_entries or LibraryEntryService(
        PostgresLibraryEntryRepository(PostgresDatabase(active_settings.database_dsn))
    )
    active_plans = plans or PlanService(
        PostgresPlanRepository(PostgresDatabase(active_settings.database_dsn))
    )
    active_artifact_exports = artifact_exports or ArtifactExportService(
        PostgresArtifactExportRepository(PostgresDatabase(active_settings.database_dsn))
    )
    active_ai_configuration = ai_configuration or AIConfigurationService(
        PostgresAIConfigurationRepository(PostgresDatabase(active_settings.database_dsn))
    )
    active_pc_profiles = pc_profiles or PCProfileService(
        PostgresPCProfileRepository(PostgresDatabase(active_settings.database_dsn))
    )
    active_direct_capture = SessionNoteCaptureService(
        active_imports,
        PostgresCampaignClockRepository(PostgresDatabase(active_settings.database_dsn)),
    )
    active_brainstorms = brainstorms or BrainstormService(
        PostgresBrainstormRepository(PostgresDatabase(active_settings.database_dsn)),
        active_imports,
        active_retrieval,
    )
    active_session_runs = session_runs or SessionRunService(
        PostgresSessionRunRepository(PostgresDatabase(active_settings.database_dsn))
    )
    active_claim_reconciliation = claim_reconciliation or ClaimReconciliationService(
        PostgresClaimReconciliationRepository(PostgresDatabase(active_settings.database_dsn))
    )
    from dm_assistant_core.adapters.postgres.identity_gaps import (
        PostgresIdentityQueueRepository,
    )
    from dm_assistant_core.application.identity_gaps import IdentityQueueError
    active_identity_queue = PostgresIdentityQueueRepository(
        PostgresDatabase(active_settings.database_dsn)
    )
    if candidate_extraction is not None:
        active_candidate_extraction = candidate_extraction
    elif active_settings.openrouter_api_key:
        active_candidate_extraction = _default_candidate_extraction_service(active_settings)
    else:
        active_candidate_extraction = None
    app = FastAPI(title="DM Assistant Campaign Core", version=__version__)
    if active_settings.allowed_cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(active_settings.allowed_cors_origins),
            allow_credentials=False,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["Content-Type"],
        )
    app.state.settings = active_settings
    app.state.change_sets = active_change_sets
    app.state.imports = active_imports
    app.state.import_reviews = active_import_reviews
    app.state.retrieval = active_retrieval
    app.state.candidate_proposals = active_candidate_proposals
    app.state.taxonomy = active_taxonomy
    app.state.entity_metadata = active_entity_metadata
    app.state.plans = active_plans
    app.state.artifact_exports = active_artifact_exports
    app.state.candidate_extraction = active_candidate_extraction
    app.state.ai_configuration = active_ai_configuration
    app.state.pc_profiles = active_pc_profiles
    app.state.session_runs = active_session_runs
    app.state.brainstorms = active_brainstorms
    app.state.identity_queue = active_identity_queue

    @app.get("/health", response_model=HealthResponse, tags=["operations"])
    def health() -> HealthResponse:
        return HealthResponse(status="ok", service="campaign-core", version=__version__)

    @app.get("/ai/configuration", response_model=AIConfigurationSnapshot, tags=["operations"])
    def get_ai_configuration(
        requester_role: Annotated[RequesterRole, Query()] = RequesterRole.DM,
    ) -> AIConfigurationSnapshot:
        if requester_role is not RequesterRole.DM:
            raise HTTPException(status_code=403, detail="AI configuration is DM-only")
        return active_ai_configuration.snapshot()

    class ActivateAIConfiguration(BaseModel):
        profile_key: str

    @app.post("/ai/configuration/activate", response_model=ActivationReceipt, tags=["operations"])
    def activate_ai_configuration(
        command: ActivateAIConfiguration,
        requester_role: Annotated[RequesterRole, Query()] = RequesterRole.DM,
    ) -> ActivationReceipt:
        if requester_role is not RequesterRole.DM:
            raise HTTPException(status_code=403, detail="AI configuration is DM-only")
        try:
            return active_ai_configuration.activate(command.profile_key)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @app.get("/taxonomy", response_model=TaxonomySnapshot, tags=["campaign"])
    def taxonomy_snapshot(
        requester_role: Annotated[RequesterRole, Query()] = RequesterRole.DM,
    ) -> TaxonomySnapshot:
        if requester_role is not RequesterRole.DM:
            raise HTTPException(status_code=403, detail="taxonomy administration is DM-only")
        return active_taxonomy.snapshot()

    @app.post("/plans/proposals", response_model=PlanProposalVersion, tags=["proposals"])
    def create_plan_proposal(
        request: CreatePlanCommand,
        requester_role: Annotated[RequesterRole, Query()] = RequesterRole.DM,
    ) -> PlanProposalVersion:
        try:
            return active_plans.create(request, RequesterVisibility(role=requester_role))
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error
        except PlanProposalError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.post(
        "/plans/{plan_id}/lifecycle-proposals",
        response_model=PlanProposalVersion,
        tags=["proposals"],
    )
    def transition_plan_proposal(
        request: TransitionPlanCommand,
        plan_id: Annotated[UUID, Path()],
        requester_role: Annotated[RequesterRole, Query()] = RequesterRole.DM,
    ) -> PlanProposalVersion:
        if request.plan_id != plan_id:
            raise HTTPException(status_code=409, detail="plan path and command IDs differ")
        try:
            return active_plans.transition(request, RequesterVisibility(role=requester_role))
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error
        except PlanProposalError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.get(
        "/plans/proposals/{proposal_id}",
        response_model=PlanProposalVersion,
        tags=["proposals"],
    )
    def get_plan_proposal(
        proposal_id: Annotated[UUID, Path()],
        requester_role: Annotated[RequesterRole, Query()] = RequesterRole.DM,
    ) -> PlanProposalVersion:
        try:
            result = active_plans.get_proposal(
                proposal_id, RequesterVisibility(role=requester_role)
            )
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error
        if result is None:
            raise HTTPException(status_code=404, detail="plan proposal not found")
        return result

    @app.post(
        "/plans/proposals/{proposal_id}/approvals",
        response_model=CandidateProposalApproval,
        tags=["proposals"],
    )
    def approve_plan_proposal(
        request: ApproveCandidateProposalRequest,
        proposal_id: Annotated[UUID, Path()],
        requester_role: Annotated[RequesterRole, Query()] = RequesterRole.DM,
    ) -> CandidateProposalApproval:
        try:
            return active_plans.approve(
                ApproveCandidateProposalCommand(
                    proposal_id=proposal_id,
                    reviewed_version=request.reviewed_version,
                    content_hash=request.content_hash,
                    item_ids=request.item_ids,
                    idempotency_key=request.idempotency_key,
                ),
                RequesterVisibility(role=requester_role),
            )
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error
        except CandidateProposalError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.get("/entities", response_model=tuple[EntityIdentity, ...], tags=["campaign"])
    def search_entities(
        canonical_name: Annotated[str, Query(min_length=1)],
        limit: Annotated[int, Query(ge=1, le=25)] = 10,
        requester_role: Annotated[RequesterRole, Query()] = RequesterRole.DM,
    ) -> tuple[EntityIdentity, ...]:
        if requester_role is not RequesterRole.DM:
            raise HTTPException(status_code=403, detail="entity identity lookup requires DM access")
        matches = active_entity_lookup.search(canonical_name, limit)
        if not matches:
            # Best-effort demand telemetry for the identity review queue; never
            # blocks or fails the lookup path.
            active_identity_queue.record_demand(canonical_name, "entity_lookup")
        return matches

    @app.get("/library/entries", response_model=tuple[LibraryEntrySummary, ...], tags=["campaign"])
    def list_library_entries(
        requester_role: Annotated[RequesterRole, Query()] = RequesterRole.DM,
    ) -> tuple[LibraryEntrySummary, ...]:
        if requester_role is not RequesterRole.DM:
            raise HTTPException(status_code=403, detail="library entries require DM access")
        return active_library_entries.list()

    @app.get("/library/entries/{entry_id}", response_model=LibraryEntry, tags=["campaign"])
    def get_library_entry(
        entry_id: Annotated[UUID, Path()],
        requester_role: Annotated[RequesterRole, Query()] = RequesterRole.DM,
    ) -> LibraryEntry:
        if requester_role is not RequesterRole.DM:
            raise HTTPException(status_code=403, detail="library entries require DM access")
        result = active_library_entries.get(entry_id)
        if result is None:
            raise HTTPException(status_code=404, detail="library entry not found")
        return result

    @app.get("/plans", response_model=tuple[PlanRecord, ...], tags=["campaign"])
    def list_plans(
        plan_kind: Annotated[PlanKind | None, Query()] = None,
        lifecycle: Annotated[PlanLifecycle | None, Query()] = None,
        requester_role: Annotated[RequesterRole, Query()] = RequesterRole.DM,
    ) -> tuple[PlanRecord, ...]:
        try:
            return active_plans.list(RequesterVisibility(role=requester_role), plan_kind, lifecycle)
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error

    @app.get("/plans/{plan_id}", response_model=PlanRecord, tags=["campaign"])
    def get_plan(
        plan_id: Annotated[UUID, Path()],
        requester_role: Annotated[RequesterRole, Query()] = RequesterRole.DM,
    ) -> PlanRecord:
        try:
            result = active_plans.get(plan_id, RequesterVisibility(role=requester_role))
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error
        if result is None:
            raise HTTPException(status_code=404, detail="plan not found")
        return result

    @app.get(
        "/plans/{plan_id}/projection-context",
        response_model=PlanProjectionContext,
        tags=["retrieval"],
    )
    def get_plan_projection_context(
        plan_id: Annotated[UUID, Path()],
        requester_role: Annotated[RequesterRole, Query()] = RequesterRole.DM,
    ) -> PlanProjectionContext:
        try:
            return active_plans.projection_context(
                plan_id, RequesterVisibility(role=requester_role)
            )
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error
        except PlanProposalError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.post(
        "/entities/{entity_id}/metadata-proposals",
        response_model=EntityMetadataProposalVersion,
        tags=["proposals"],
    )
    def create_entity_metadata_proposal(
        request: ProposeEntityMetadataRequest,
        entity_id: Annotated[UUID, Path()],
        requester_role: Annotated[RequesterRole, Query()] = RequesterRole.DM,
    ) -> EntityMetadataProposalVersion:
        try:
            command = ProposeEntityMetadataCommand(
                entity_id=entity_id,
                entity_kind=request.entity_kind,
                tags=request.tags,
            )
            return active_entity_metadata.create(command, RequesterVisibility(role=requester_role))
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error
        except (EntityMetadataProposalError, ValueError) as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.get(
        "/entities/metadata-proposals/{proposal_id}",
        response_model=EntityMetadataProposalVersion,
        tags=["proposals"],
    )
    def get_entity_metadata_proposal(
        proposal_id: Annotated[UUID, Path()],
        requester_role: Annotated[RequesterRole, Query()] = RequesterRole.DM,
    ) -> EntityMetadataProposalVersion:
        try:
            proposal = active_entity_metadata.get(
                proposal_id, RequesterVisibility(role=requester_role)
            )
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error
        if proposal is None:
            raise HTTPException(status_code=404, detail="entity metadata proposal not found")
        return proposal

    @app.post(
        "/entities/metadata-proposals/{proposal_id}/approvals",
        response_model=CandidateProposalApproval,
        tags=["proposals"],
    )
    def approve_entity_metadata_proposal(
        request: ApproveCandidateProposalRequest,
        proposal_id: Annotated[UUID, Path()],
        requester_role: Annotated[RequesterRole, Query()] = RequesterRole.DM,
    ) -> CandidateProposalApproval:
        try:
            return active_entity_metadata.approve(
                ApproveCandidateProposalCommand(
                    proposal_id=proposal_id,
                    reviewed_version=request.reviewed_version,
                    content_hash=request.content_hash,
                    item_ids=request.item_ids,
                    idempotency_key=request.idempotency_key,
                ),
                RequesterVisibility(role=requester_role),
            )
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error
        except CandidateProposalError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

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

    @app.post(
        "/capture/session-notes",
        response_model=SessionNoteCaptureReceipt,
        tags=["capture"],
    )
    def capture_session_note(command: SessionNoteCaptureCommand) -> SessionNoteCaptureReceipt:
        try:
            return active_direct_capture.capture(command)
        except (ImportRejectedError, ValueError) as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.get("/campaign/current-date", response_model=CampaignDate | None, tags=["campaign"])
    def get_current_campaign_date() -> CampaignDate | None:
        return active_direct_capture.current_date()

    @app.get("/brainstorms/open", response_model=BrainstormSession | None, tags=["brainstorm"])
    def get_open_brainstorm(
        requester_role: Annotated[RequesterRole, Query()] = RequesterRole.DM,
    ) -> BrainstormSession | None:
        if requester_role is not RequesterRole.DM:
            raise HTTPException(status_code=403, detail="brainstorms are DM-only")
        return active_brainstorms.get_open()

    @app.post("/brainstorms", response_model=BrainstormSession, tags=["brainstorm"])
    def start_brainstorm(
        command: StartBrainstormCommand,
        requester_role: Annotated[RequesterRole, Query()] = RequesterRole.DM,
    ) -> BrainstormSession:
        if requester_role is not RequesterRole.DM:
            raise HTTPException(status_code=403, detail="brainstorms are DM-only")
        try:
            return active_brainstorms.start(command)
        except BrainstormError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.get(
        "/brainstorms/{session_id}", response_model=BrainstormSession, tags=["brainstorm"]
    )
    def get_brainstorm(
        session_id: Annotated[UUID, Path()],
        requester_role: Annotated[RequesterRole, Query()] = RequesterRole.DM,
    ) -> BrainstormSession:
        if requester_role is not RequesterRole.DM:
            raise HTTPException(status_code=403, detail="brainstorms are DM-only")
        result = active_brainstorms.get(session_id)
        if result is None:
            raise HTTPException(status_code=404, detail="brainstorm session not found")
        return result

    @app.post(
        "/brainstorms/{session_id}/thoughts",
        response_model=BrainstormSession,
        tags=["brainstorm"],
    )
    def capture_brainstorm_thought(
        session_id: Annotated[UUID, Path()],
        command: CaptureBrainstormThoughtCommand,
        requester_role: Annotated[RequesterRole, Query()] = RequesterRole.DM,
    ) -> BrainstormSession:
        if requester_role is not RequesterRole.DM:
            raise HTTPException(status_code=403, detail="brainstorms are DM-only")
        try:
            return active_brainstorms.capture(session_id, command)
        except (BrainstormError, ImportRejectedError) as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.put(
        "/brainstorms/{session_id}/pins/{entity_id}",
        response_model=BrainstormSession,
        tags=["brainstorm"],
    )
    def pin_brainstorm_entity(
        session_id: Annotated[UUID, Path()],
        entity_id: Annotated[UUID, Path()],
        requester_role: Annotated[RequesterRole, Query()] = RequesterRole.DM,
    ) -> BrainstormSession:
        if requester_role is not RequesterRole.DM:
            raise HTTPException(status_code=403, detail="brainstorms are DM-only")
        try:
            return active_brainstorms.pin(session_id, entity_id)
        except BrainstormError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.delete(
        "/brainstorms/{session_id}/pins/{entity_id}",
        response_model=BrainstormSession,
        tags=["brainstorm"],
    )
    def unpin_brainstorm_entity(
        session_id: Annotated[UUID, Path()],
        entity_id: Annotated[UUID, Path()],
        requester_role: Annotated[RequesterRole, Query()] = RequesterRole.DM,
    ) -> BrainstormSession:
        if requester_role is not RequesterRole.DM:
            raise HTTPException(status_code=403, detail="brainstorms are DM-only")
        try:
            return active_brainstorms.unpin(session_id, entity_id)
        except BrainstormError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.put(
        "/brainstorms/{session_id}/evidence-pins/{record_id}",
        response_model=BrainstormSession,
        tags=["brainstorm"],
    )
    def pin_brainstorm_evidence(
        session_id: Annotated[UUID, Path()],
        record_id: Annotated[str, Path()],
        search_query: Annotated[str | None, Query(max_length=20000)] = None,
        requester_role: Annotated[RequesterRole, Query()] = RequesterRole.DM,
    ) -> BrainstormSession:
        if requester_role is not RequesterRole.DM:
            raise HTTPException(status_code=403, detail="brainstorms are DM-only")
        try:
            return active_brainstorms.pin_evidence(session_id, record_id, search_query)
        except BrainstormError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.delete(
        "/brainstorms/{session_id}/evidence-pins/{record_id}",
        response_model=BrainstormSession,
        tags=["brainstorm"],
    )
    def unpin_brainstorm_evidence(
        session_id: Annotated[UUID, Path()],
        record_id: Annotated[str, Path()],
        requester_role: Annotated[RequesterRole, Query()] = RequesterRole.DM,
    ) -> BrainstormSession:
        if requester_role is not RequesterRole.DM:
            raise HTTPException(status_code=403, detail="brainstorms are DM-only")
        try:
            return active_brainstorms.unpin_evidence(session_id, record_id)
        except BrainstormError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.post(
        "/brainstorms/{session_id}/close",
        response_model=BrainstormSession,
        tags=["brainstorm"],
    )
    def close_brainstorm(
        session_id: Annotated[UUID, Path()],
        command: CloseBrainstormCommand,
        requester_role: Annotated[RequesterRole, Query()] = RequesterRole.DM,
    ) -> BrainstormSession:
        if requester_role is not RequesterRole.DM:
            raise HTTPException(status_code=403, detail="brainstorms are DM-only")
        try:
            return active_brainstorms.close(session_id, command)
        except BrainstormError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.get(
        "/campaign/session-runs/open",
        response_model=SessionRun | None,
        tags=["campaign"],
    )
    def get_open_session_run(
        requester_role: Annotated[RequesterRole, Query()] = RequesterRole.DM,
    ) -> SessionRun | None:
        if requester_role is not RequesterRole.DM:
            raise HTTPException(status_code=403, detail="session runs are DM-only")
        return active_session_runs.get_open()

    @app.post("/campaign/session-runs/open", response_model=SessionRun, tags=["capture"])
    def open_session_run(
        command: OpenSessionRunCommand,
        requester_role: Annotated[RequesterRole, Query()] = RequesterRole.DM,
    ) -> SessionRun:
        if requester_role is not RequesterRole.DM:
            raise HTTPException(status_code=403, detail="session runs are DM-only")
        try:
            return active_session_runs.open(command)
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.put(
        "/campaign/session-runs/{run_id}/notes/{note_id}",
        response_model=SessionRunNote,
        tags=["capture"],
    )
    def save_session_run_note(
        run_id: Annotated[UUID, Path()],
        note_id: Annotated[UUID, Path()],
        command: SaveSessionRunNoteCommand,
        requester_role: Annotated[RequesterRole, Query()] = RequesterRole.DM,
    ) -> SessionRunNote:
        if requester_role is not RequesterRole.DM:
            raise HTTPException(status_code=403, detail="session runs are DM-only")
        if command.note_id != note_id:
            raise HTTPException(status_code=422, detail="note_id must match the request path")
        try:
            return active_session_runs.save_note(run_id, command)
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.delete(
        "/campaign/session-runs/{run_id}/notes/{note_id}",
        response_model=DeleteSessionRunNoteResponse,
        tags=["capture"],
    )
    def delete_session_run_note(
        run_id: Annotated[UUID, Path()],
        note_id: Annotated[UUID, Path()],
        requester_role: Annotated[RequesterRole, Query()] = RequesterRole.DM,
    ) -> DeleteSessionRunNoteResponse:
        if requester_role is not RequesterRole.DM:
            raise HTTPException(status_code=403, detail="session runs are DM-only")
        try:
            active_session_runs.delete_note(run_id, note_id)
        except ValueError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        return DeleteSessionRunNoteResponse(note_id=note_id)

    @app.post(
        "/campaign/session-runs/{run_id}/close",
        response_model=SessionRun,
        tags=["capture"],
    )
    def close_session_run(
        run_id: Annotated[UUID, Path()],
        command: CloseSessionRunCommand,
        requester_role: Annotated[RequesterRole, Query()] = RequesterRole.DM,
    ) -> SessionRun:
        if requester_role is not RequesterRole.DM:
            raise HTTPException(status_code=403, detail="session runs are DM-only")
        try:
            return active_session_runs.close(run_id, command)
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.get(
        "/campaign/encounters/progress",
        response_model=tuple[EncounterProgress, ...],
        tags=["campaign"],
    )
    def list_encounter_progress(
        requester_role: Annotated[RequesterRole, Query()] = RequesterRole.DM,
    ) -> tuple[EncounterProgress, ...]:
        if requester_role is not RequesterRole.DM:
            raise HTTPException(status_code=403, detail="encounter progress is DM-only")
        return active_session_runs.list_encounter_progress()

    @app.put(
        "/campaign/encounters/{document_id}/progress",
        response_model=EncounterProgress,
        tags=["capture"],
    )
    def update_encounter_progress(
        document_id: Annotated[UUID, Path()],
        command: UpdateEncounterProgressCommand,
        requester_role: Annotated[RequesterRole, Query()] = RequesterRole.DM,
    ) -> EncounterProgress:
        if requester_role is not RequesterRole.DM:
            raise HTTPException(status_code=403, detail="encounter progress is DM-only")
        if command.source_document_id != document_id:
            raise HTTPException(
                status_code=422,
                detail="source_document_id must match the request path",
            )
        try:
            return active_session_runs.update_encounter_progress(command)
        except ValueError as error:
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

    @app.get(
        "/imports/source-documents",
        response_model=SourceDocumentPage,
        tags=["imports"],
    )
    def list_source_documents(
        requester_role: Annotated[RequesterRole, Query()],
        character_id: Annotated[str | None, Query()] = None,
        limit: Annotated[int, Query(ge=1, le=500)] = 200,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> SourceDocumentPage:
        try:
            return active_import_reviews.list_source_documents(
                SourceDocumentListQuery(
                    requester=_requester(requester_role, character_id),
                    limit=limit,
                    offset=offset,
                )
            )
        except ImportReviewForbiddenError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error

    @app.get(
        "/imports/source-documents/{document_id}",
        response_model=SourceDocumentContent,
        tags=["imports"],
    )
    def get_source_document(
        document_id: Annotated[UUID, Path()],
        requester_role: Annotated[RequesterRole, Query()],
        character_id: Annotated[str | None, Query()] = None,
    ) -> SourceDocumentContent:
        # DM-only
        try:
            result = active_import_reviews.get_source_document_content(
                document_id, _requester(requester_role, character_id)
            )
        except ImportReviewForbiddenError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error
        if result is None:
            raise HTTPException(status_code=404, detail="source document not found")
        return result

    @app.post(
        "/imports/reviews/{review_id}/disposition",
        response_model=SourceReviewDispositionResult,
        tags=["imports"],
    )
    def disposition_source_review(
        review_id: Annotated[UUID, Path()],
        command: DispositionSourceReviewCommand,
        requester_role: Annotated[RequesterRole, Query()],
        character_id: Annotated[str | None, Query()] = None,
    ) -> SourceReviewDispositionResult:
        if command.review_id != review_id:
            raise HTTPException(status_code=400, detail="review id does not match path")
        try:
            return active_import_reviews.disposition_source_review(
                command, _requester(requester_role, character_id)
            )
        except ImportReviewForbiddenError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error
        except SourceReviewDispositionError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.get(
        "/imports/source-documents/{document_id}/pc-profile",
        response_model=PCProfile | None,
        tags=["imports"],
    )
    def get_pc_profile(
        document_id: Annotated[UUID, Path()],
        requester_role: Annotated[RequesterRole, Query()] = RequesterRole.DM,
    ) -> PCProfile | None:
        try:
            return active_pc_profiles.get(document_id, RequesterVisibility(role=requester_role))
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error

    @app.put(
        "/imports/source-documents/{document_id}/pc-profile",
        response_model=PCProfileReceipt,
        tags=["imports"],
    )
    def update_pc_profile(
        request: UpdatePCProfileRequest,
        document_id: Annotated[UUID, Path()],
        requester_role: Annotated[RequesterRole, Query()] = RequesterRole.DM,
    ) -> PCProfileReceipt:
        try:
            return active_pc_profiles.update(
                UpdatePCProfileCommand(document_id=document_id, **request.model_dump()),
                RequesterVisibility(role=requester_role),
            )
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error
        except (PCProfileError, ValueError) as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    from dm_assistant_core.application.identity_gaps import (  # noqa: E402
        AddAliasDecision,
        CreateEntityDecision,
        IdentityGapQueue,
        IdentityDecisionReceipt,
        SurfaceDecision,
    )

    def _identity_dm(requester_role: RequesterRole) -> None:
        if requester_role is not RequesterRole.DM:
            raise PermissionError("identity review is DM-only")

    @app.get("/identity/gaps", response_model=IdentityGapQueue, tags=["identity"])
    def identity_gaps(
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        requester_role: Annotated[RequesterRole, Query()] = RequesterRole.DM,
    ) -> IdentityGapQueue:
        try:
            _identity_dm(requester_role)
            return active_identity_queue.queue(limit)
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error

    @app.post("/identity/decisions/add-alias",
              response_model=IdentityDecisionReceipt, tags=["identity"])
    def identity_add_alias(
        request: AddAliasDecision,
        requester_role: Annotated[RequesterRole, Query()] = RequesterRole.DM,
    ) -> IdentityDecisionReceipt:
        try:
            _identity_dm(requester_role)
            return active_identity_queue.add_alias(request)
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error
        except IdentityQueueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.post("/identity/decisions/create-entity",
              response_model=IdentityDecisionReceipt, tags=["identity"])
    def identity_create_entity(
        request: CreateEntityDecision,
        requester_role: Annotated[RequesterRole, Query()] = RequesterRole.DM,
    ) -> IdentityDecisionReceipt:
        try:
            _identity_dm(requester_role)
            return active_identity_queue.create_entity(request)
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error
        except IdentityQueueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.post("/identity/decisions/mark-role",
              response_model=IdentityDecisionReceipt, tags=["identity"])
    def identity_mark_role(
        request: SurfaceDecision,
        requester_role: Annotated[RequesterRole, Query()] = RequesterRole.DM,
    ) -> IdentityDecisionReceipt:
        try:
            _identity_dm(requester_role)
            return active_identity_queue.mark_role(request)
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error

    @app.post("/identity/decisions/dismiss",
              response_model=IdentityDecisionReceipt, tags=["identity"])
    def identity_dismiss(
        request: SurfaceDecision,
        requester_role: Annotated[RequesterRole, Query()] = RequesterRole.DM,
    ) -> IdentityDecisionReceipt:
        try:
            _identity_dm(requester_role)
            return active_identity_queue.dismiss(request)
        except PermissionError as error:
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

    @app.get(
        "/imports/candidates/{candidate_id}/proposal",
        response_model=CandidateProposalVersion,
        tags=["imports"],
    )
    def get_candidate_pending_proposal(
        candidate_id: Annotated[UUID, Path()],
        requester_role: Annotated[RequesterRole, Query()],
        character_id: Annotated[str | None, Query()] = None,
    ) -> CandidateProposalVersion:
        result = active_candidate_proposals.get_for_candidate(
            candidate_id, _requester(requester_role, character_id)
        )
        if result is None:
            raise HTTPException(status_code=404, detail="pending candidate proposal not found")
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

    @app.get(
        "/claims/{claim_id}",
        response_model=ClaimSnapshot,
        tags=["claims"],
    )
    def get_claim_snapshot(
        claim_id: Annotated[UUID, Path()],
        requester_role: Annotated[RequesterRole, Query()] = RequesterRole.DM,
    ) -> ClaimSnapshot:
        try:
            return active_claim_reconciliation.get(
                claim_id, RequesterVisibility(role=requester_role)
            )
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error
        except ClaimReconciliationError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @app.get(
        "/claims/reconciliation-candidates",
        response_model=tuple[ClaimOverlap, ...],
        tags=["claims"],
    )
    def discover_claim_reconciliations(
        requester_role: Annotated[RequesterRole, Query()] = RequesterRole.DM,
        limit: Annotated[int, Query(ge=1, le=100)] = 25,
    ) -> tuple[ClaimOverlap, ...]:
        try:
            return active_claim_reconciliation.discover(
                limit, RequesterVisibility(role=requester_role)
            )
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error

    @app.get(
        "/claims/{superseding_claim_id}/reconciliation/{superseded_claim_id}",
        response_model=ClaimReconciliationReview,
        tags=["claims"],
    )
    def review_claim_reconciliation(
        superseding_claim_id: Annotated[UUID, Path()],
        superseded_claim_id: Annotated[UUID, Path()],
        requester_role: Annotated[RequesterRole, Query()] = RequesterRole.DM,
    ) -> ClaimReconciliationReview:
        try:
            return active_claim_reconciliation.review(
                superseding_claim_id,
                superseded_claim_id,
                RequesterVisibility(role=requester_role),
            )
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error
        except ClaimReconciliationError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.post(
        "/claims/reconciliations",
        response_model=ClaimReconciliationReceipt,
        tags=["claims"],
    )
    def apply_claim_reconciliation(
        request: ApplyClaimReconciliationCommand,
        requester_role: Annotated[RequesterRole, Query()] = RequesterRole.DM,
    ) -> ClaimReconciliationReceipt:
        try:
            return active_claim_reconciliation.apply(
                request, RequesterVisibility(role=requester_role)
            )
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error
        except ClaimReconciliationError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.post(
        "/claims/{claim_id}/corrections",
        response_model=ClaimCorrectionReceipt,
        tags=["claims"],
    )
    def correct_claim(
        request: CorrectClaimCommand,
        claim_id: Annotated[UUID, Path()],
        requester_role: Annotated[RequesterRole, Query()] = RequesterRole.DM,
    ) -> ClaimCorrectionReceipt:
        if request.claim_id != claim_id:
            raise HTTPException(
                status_code=409, detail="claim correction target does not match path"
            )
        try:
            return active_claim_reconciliation.correct(
                request, RequesterVisibility(role=requester_role)
            )
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error
        except ClaimReconciliationError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.post(
        "/claims/{claim_id}/replacements",
        response_model=ClaimReplacementReceipt,
        tags=["claims"],
    )
    def replace_claim(
        request: ReplaceClaimCommand,
        claim_id: Annotated[UUID, Path()],
        requester_role: Annotated[RequesterRole, Query()] = RequesterRole.DM,
    ) -> ClaimReplacementReceipt:
        if request.claim_id != claim_id:
            raise HTTPException(
                status_code=409, detail="claim replacement target does not match path"
            )
        try:
            return active_claim_reconciliation.replace(
                request, RequesterVisibility(role=requester_role)
            )
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error
        except ClaimReconciliationError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.post(
        "/entities/{entity_id}/rules-card",
        response_model=ExportedArtifact,
        tags=["artifacts"],
    )
    def export_rules_card(
        entity_id: Annotated[UUID, Path()],
    ) -> ExportedArtifact:
        try:
            return active_artifact_exports.export_rules_card(entity_id)
        except ArtifactExportError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.post(
        "/imports/candidates/{candidate_id}/extraction",
        response_model=CandidateExtractionResult,
        tags=["imports"],
    )
    def extract_candidate(
        candidate_id: Annotated[UUID, Path()],
    ) -> CandidateExtractionResult:
        service = active_candidate_extraction
        if candidate_extraction is None and active_settings.openrouter_api_key:
            service = _default_candidate_extraction_service(
                active_settings, active_ai_configuration.active_profile()
            )
        if service is None:
            raise HTTPException(
                status_code=503,
                detail="candidate extraction is not configured (no AI provider key)",
            )
        try:
            return service.extract(candidate_id)
        except CandidateExtractionError as error:
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


def _default_candidate_extraction_service(
    settings: Settings,
    profile: ModelProfile | None = None,
) -> CandidateExtractionService:
    """Build the candidate extraction service from settings when no override is injected."""
    from dm_assistant_core.adapters.openrouter import OpenRouterClient
    from dm_assistant_core.domain.extraction import ExtractionHarness

    active_model = profile.model_slug if profile else settings.openrouter_model
    client = OpenRouterClient(
        api_key=settings.openrouter_api_key,
        base_url=settings.openrouter_base_url,
        model=active_model,
        max_tokens=profile.max_tokens if profile else settings.openrouter_max_tokens,
        timeout_seconds=profile.timeout_seconds if profile else settings.openrouter_timeout_seconds,
        max_retries=profile.retry_limit if profile else settings.openrouter_max_retries,
        reasoning_effort=profile.reasoning_effort if profile else None,
    )
    harness = ExtractionHarness(client)
    return CandidateExtractionService(
        PostgresCandidateExtractionRepository(PostgresDatabase(settings.database_dsn)),
        harness,
        model_profile_key=profile.key if profile else None,
        model_slug=active_model,
        prompt_version=PROMPT_VERSION if profile else harness.extractor_version,
    )
