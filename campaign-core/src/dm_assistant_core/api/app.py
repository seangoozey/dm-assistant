"""Campaign Core HTTP application factory."""

from typing import Annotated
from uuid import UUID

from fastapi import FastAPI, HTTPException, Path, Query
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

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
from dm_assistant_core.adapters.postgres.prompt_configuration import (
    PostgresPromptOverrideRepository,
)
from dm_assistant_core.adapters.postgres.campaign_clock import PostgresCampaignClockRepository
from dm_assistant_core.adapters.postgres.session_dating import PostgresSessionDatingRepository
from dm_assistant_core.adapters.postgres.life_status import PostgresLifeStatusRepository
from dm_assistant_core.adapters.postgres.conflict_review import PostgresConflictReviewRepository
from dm_assistant_core.adapters.postgres.identity_gaps import PostgresIdentityQueueRepository
from dm_assistant_core.application.entity_descriptions import (
    EntityDescriptionCommand, EntityDescriptionReceipt, EntityDescriptionService)
from dm_assistant_core.application.entity_graph_neighborhood import GraphRelationRow
from dm_assistant_core.application.prompt_configuration import (
    EffectivePrompt,
    PromptConfigurationService,
    PromptOverrideReceipt,
    SetPromptOverride,
)
from dm_assistant_core.application.claim_reattribution import (
    ClaimReattributionService,
    MovedAssertion,
    ReattributeClaim,
    ReattributionReceipt,
)
from dm_assistant_core.adapters.postgres.claim_reattribution import (
    PostgresClaimReattributionRepository,
)
from dm_assistant_core.application.link_audit import (
    LinkAuditResult,
    LinkAuditService,
)
from dm_assistant_core.adapters.postgres.link_audit import PostgresLinkAuditRepository
from dm_assistant_core.application.template_vocabularies import (
    TemplateVocabularyService,
    VocabularyChangeReceipt,
    VocabularyCommand,
    VocabularyValue,
)
from dm_assistant_core.application.dossier import (
    DossierDecisionReceipt,
    DossierService,
    DossierView,
)
from dm_assistant_core.adapters.postgres.dossier import PostgresDossierRepository
from dm_assistant_core.adapters.postgres.template_vocabularies import (
    PostgresTemplateVocabularyRepository,
)
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
    PURPOSES,
    ActivationReceipt,
    AIConfigurationService,
    AIConfigurationSnapshot,
    ModelProfile,
)
from dm_assistant_core.application.prose_drafting import (
    ProseDraftCommand,
    ProseDraftError,
    ProseDraftResult,
    ProseDraftingService,
    ProseHarness,
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
    prose_drafting: ProseDraftingService | None = None,
    prompt_configuration: PromptConfigurationService | None = None,
    dossier: DossierService | None = None,
    template_vocabularies: TemplateVocabularyService | None = None,
    link_audit: LinkAuditService | None = None,
    claim_reattribution: ClaimReattributionService | None = None,
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
    active_clock = PostgresCampaignClockRepository(PostgresDatabase(active_settings.database_dsn))
    active_session_dating = PostgresSessionDatingRepository(PostgresDatabase(active_settings.database_dsn))
    active_conflict_review = PostgresConflictReviewRepository(PostgresDatabase(active_settings.database_dsn))
    class _EntityNameLookup:
        def __init__(self, database) -> None:
            self._database = database

        def get(self, entity_id):
            with self._database.connection() as connection:
                row = connection.execute(
                    "SELECT id, canonical_name FROM entities WHERE id = %s", (entity_id,)).fetchone()
            if row is None:
                return None
            return type("Entity", (), {"entity_id": row[0], "canonical_name": row[1]})()

    active_entity_descriptions = EntityDescriptionService(
        active_imports, _EntityNameLookup(PostgresDatabase(active_settings.database_dsn)))
    active_entity_graph_neighborhood = None
    if active_settings.graph_pilot_bundle and active_settings.environment == "development":
        from dm_assistant_core.application.entity_graph_neighborhood import (
            EntityGraphNeighborhoodService,
        )

        active_entity_graph_neighborhood = EntityGraphNeighborhoodService(
            active_settings.graph_pilot_bundle,
            _EntityNameLookup(PostgresDatabase(active_settings.database_dsn)),
        )
    active_direct_capture = SessionNoteCaptureService(active_imports, active_clock)
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
    from dm_assistant_core.adapters.postgres.entity_profiles import (
        PostgresEntityProfileRepository,
    )
    from dm_assistant_core.adapters.postgres.identity_gaps import (
        PostgresIdentityQueueRepository,
    )
    from dm_assistant_core.application.identity_gaps import IdentityQueueError
    active_identity_queue = PostgresIdentityQueueRepository(
        PostgresDatabase(active_settings.database_dsn)
    )
    from dm_assistant_core.application.entity_profiles import (
        EntityProfileService, UpdateEntityProfileCommand, EntityProfile, EntityProfileReceipt,
    )
    active_entity_profiles = EntityProfileService(
        PostgresEntityProfileRepository(PostgresDatabase(active_settings.database_dsn))
    )
    active_life_status = PostgresLifeStatusRepository(
        PostgresDatabase(active_settings.database_dsn), active_entity_profiles)
    if candidate_extraction is not None:
        active_candidate_extraction = candidate_extraction
    elif active_settings.openrouter_api_key:
        active_candidate_extraction = _default_candidate_extraction_service(active_settings)
    else:
        active_candidate_extraction = None
    # The prose writer builds lazily per request: it needs the ACTIVE prose
    # profile, which can change in Settings at any moment.
    active_prose_drafting = prose_drafting
    active_prompt_configuration = prompt_configuration or PromptConfigurationService(
        PostgresPromptOverrideRepository(PostgresDatabase(active_settings.database_dsn))
    )
    active_dossier = dossier or DossierService(
        PostgresDossierRepository(PostgresDatabase(active_settings.database_dsn))
    )
    active_template_vocabularies = template_vocabularies or TemplateVocabularyService(
        PostgresTemplateVocabularyRepository(PostgresDatabase(active_settings.database_dsn))
    )
    active_link_audit = link_audit or LinkAuditService(
        PostgresLinkAuditRepository(PostgresDatabase(active_settings.database_dsn))
    )
    active_claim_reattribution = claim_reattribution or ClaimReattributionService(
        PostgresClaimReattributionRepository(PostgresDatabase(active_settings.database_dsn))
    )
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
    app.state.prose_drafting = active_prose_drafting
    app.state.dossier = active_dossier
    app.state.pc_profiles = active_pc_profiles
    app.state.session_runs = active_session_runs
    app.state.brainstorms = active_brainstorms
    app.state.identity_queue = active_identity_queue
    app.state.entity_profiles = active_entity_profiles

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

    @app.get(
        "/ai/prompts",
        response_model=list[EffectivePrompt],
        tags=["operations"],
    )
    def get_ai_prompts(
        requester_role: Annotated[RequesterRole, Query()] = RequesterRole.DM,
    ) -> list[EffectivePrompt]:
        if requester_role is not RequesterRole.DM:
            raise HTTPException(status_code=403, detail="AI prompts are DM-only")
        return [active_prompt_configuration.effective(p) for p in ("extraction", "prose")]

    @app.put(
        "/ai/prompts/{purpose}",
        response_model=PromptOverrideReceipt,
        tags=["operations"],
    )
    def set_ai_prompt(
        purpose: str,
        command: SetPromptOverride,
        requester_role: Annotated[RequesterRole, Query()] = RequesterRole.DM,
    ) -> PromptOverrideReceipt:
        if requester_role is not RequesterRole.DM:
            raise HTTPException(status_code=403, detail="AI prompts are DM-only")
        if command.purpose != purpose:
            raise HTTPException(status_code=422, detail="purpose must match the request path")
        try:
            return active_prompt_configuration.set_override(command)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @app.delete(
        "/ai/prompts/{purpose}",
        response_model=PromptOverrideReceipt,
        tags=["operations"],
    )
    def reset_ai_prompt(
        purpose: str,
        requester_role: Annotated[RequesterRole, Query()] = RequesterRole.DM,
    ) -> PromptOverrideReceipt:
        if requester_role is not RequesterRole.DM:
            raise HTTPException(status_code=403, detail="AI prompts are DM-only")
        try:
            return active_prompt_configuration.clear_override(purpose)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    class ActivateAIConfiguration(BaseModel):
        profile_key: str
        # Absent purpose means extraction — the registry's original and only
        # purpose, so existing callers (windmill review bridge) stay valid.
        purpose: str = "extraction"

    @app.post("/ai/configuration/activate", response_model=ActivationReceipt, tags=["operations"])
    def activate_ai_configuration(
        command: ActivateAIConfiguration,
        requester_role: Annotated[RequesterRole, Query()] = RequesterRole.DM,
    ) -> ActivationReceipt:
        if requester_role is not RequesterRole.DM:
            raise HTTPException(status_code=403, detail="AI configuration is DM-only")
        try:
            return active_ai_configuration.activate(command.purpose, command.profile_key)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @app.get(
        "/campaign/link-audit",
        response_model=LinkAuditResult,
        tags=["operations"],
    )
    def campaign_link_audit(
        requester_role: Annotated[RequesterRole, Query()] = RequesterRole.DM,
    ) -> LinkAuditResult:
        """Standing entity/document link audit: wrong-page borrows, zero-affinity
        identities. Computed live, never stored — every fix is a DM decision."""
        if requester_role is not RequesterRole.DM:
            raise HTTPException(status_code=403, detail="link audit is DM-only")
        return active_link_audit.audit()

    @app.get(
        "/entities/{entity_id}/graph-neighborhood",
        tags=["operations"],
        response_model=list[GraphRelationRow],
    )
    def entity_graph_neighborhood(
        entity_id: UUID,
        requester_role: Annotated[RequesterRole, Query()] = RequesterRole.DM,
    ) -> list[GraphRelationRow]:
        """Ranked, capped relation rows for prose gather (TKT-0120 expansion).

        Audited seats first, then derived co-mentions — every row names the
        record class behind it. Discovery aids, never proof.
        """
        if requester_role is not RequesterRole.DM:
            raise HTTPException(status_code=403, detail="graph neighborhood is DM-only")
        if active_entity_graph_neighborhood is None:
            raise HTTPException(
                status_code=409,
                detail="graph neighborhood is not configured (pilot bundle inactive)",
            )
        return active_entity_graph_neighborhood.neighborhood(str(entity_id))

    @app.post(
        "/claims/{claim_id}/reattribute",
        response_model=ReattributionReceipt,
        tags=["operations"],
    )
    def reattribute_claim(
        claim_id: UUID,
        command: ReattributeClaim,
        requester_role: Annotated[RequesterRole, Query()] = RequesterRole.DM,
    ) -> ReattributionReceipt:
        """Move an assertion to a new owning entity (receipted). Provenance
        is untouched; the old owner gains a 'moved to' reference."""
        if requester_role is not RequesterRole.DM:
            raise HTTPException(status_code=403, detail="claim re-attribution is DM-only")
        if command.claim_id != claim_id:
            raise HTTPException(status_code=422, detail="claim_id must match the request path")
        try:
            return active_claim_reattribution.reattribute(command)
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.get(
        "/entities/{entity_id}/moved-assertions",
        response_model=list[MovedAssertion],
        tags=["operations"],
    )
    def entity_moved_assertions(
        entity_id: UUID,
        requester_role: Annotated[RequesterRole, Query()] = RequesterRole.DM,
    ) -> list[MovedAssertion]:
        """Assertions that moved away from this entity — Dossier tiles with
        shortcuts to the new owners."""
        if requester_role is not RequesterRole.DM:
            raise HTTPException(status_code=403, detail="moved assertions are DM-only")
        return active_claim_reattribution.moved_from(entity_id)

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

    class CampaignDateSetting(BaseModel):
        """DM-set current in-game date with an optional reason (TKT-0117)."""

        calendar_id: str = "gregorian-ce"
        year: int
        month: int
        day: int
        reason: str | None = None

        def as_date(self) -> CampaignDate:
            return CampaignDate(calendar_id=self.calendar_id, year=self.year,
                                month=self.month, day=self.day)

    class CampaignClockChangeEntry(BaseModel):
        calendar_id: str
        year: int
        month: int
        day: int
        reason: str | None
        changed_by: str
        changed_at: datetime

    @app.get("/campaign/current-date", response_model=CampaignDate | None, tags=["campaign"])
    def get_current_campaign_date() -> CampaignDate | None:
        return active_direct_capture.current_date()

    # The clock is runtime state, not canonical truth (session capture writes
    # it outside change sets), so it carries its own tag: the architectural
    # boundary test keeps "campaign"-tagged mutations change-set-only.
    @app.put("/campaign/current-date", response_model=CampaignDate, tags=["campaign-clock"])
    def set_current_campaign_date(
        command: CampaignDateSetting,
        requester_role: Annotated[RequesterRole, Query()] = RequesterRole.DM,
    ) -> CampaignDate:
        if requester_role is not RequesterRole.DM:
            raise HTTPException(status_code=403, detail="the campaign clock is DM-only")
        active_clock.set_current(CampaignDate(
            calendar_id=command.calendar_id, year=command.year,
            month=command.month, day=command.day), command.reason)
        return command.as_date()

    @app.post("/entities/{entity_id}/description",
              response_model=EntityDescriptionReceipt, tags=["entity-descriptions"])
    def write_entity_description(
        entity_id: UUID,
        command: EntityDescriptionCommand,
        requester_role: Annotated[RequesterRole, Query()] = RequesterRole.DM,
    ) -> EntityDescriptionReceipt:
        if requester_role is not RequesterRole.DM:
            raise HTTPException(status_code=403, detail="description authoring is DM-only")
        if command.entity_id != entity_id:
            raise HTTPException(status_code=422, detail="entity_id must match the request path")
        try:
            return active_entity_descriptions.write(command)
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.get(
        "/template-vocabularies/{vocabulary}",
        response_model=list[VocabularyValue],
        tags=["operations"],
    )
    def get_template_vocabulary(
        vocabulary: str,
        requester_role: Annotated[RequesterRole, Query()] = RequesterRole.DM,
    ) -> list[VocabularyValue]:
        """Offered values for a template field (receipted, retireable)."""
        if requester_role is not RequesterRole.DM:
            raise HTTPException(status_code=403, detail="template vocabularies are DM-only")
        try:
            return active_template_vocabularies.values(vocabulary)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @app.post(
        "/template-vocabularies/{vocabulary}",
        response_model=VocabularyChangeReceipt,
        tags=["operations"],
    )
    def change_template_vocabulary(
        vocabulary: str,
        command: VocabularyCommand,
        requester_role: Annotated[RequesterRole, Query()] = RequesterRole.DM,
    ) -> VocabularyChangeReceipt:
        if requester_role is not RequesterRole.DM:
            raise HTTPException(status_code=403, detail="template vocabularies are DM-only")
        if command.action not in ("add", "retire"):
            raise HTTPException(status_code=422, detail="action must be add or retire")
        try:
            return active_template_vocabularies.change(vocabulary, command)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @app.get(
        "/entities/{entity_id}/dossier",
        response_model=DossierView,
        tags=["operations"],
    )
    def get_dossier(
        entity_id: UUID,
        requester_role: Annotated[RequesterRole, Query()] = RequesterRole.DM,
    ) -> DossierView:
        """The entry's DM-curated Dossier: promoted claim ids, latest-decision-wins."""
        if requester_role is not RequesterRole.DM:
            raise HTTPException(status_code=403, detail="dossier is DM-only")
        return active_dossier.view(entity_id)

    @app.post(
        "/entities/{entity_id}/dossier/{claim_id}/promote",
        response_model=DossierDecisionReceipt,
        tags=["operations"],
    )
    def promote_to_dossier(
        entity_id: UUID,
        claim_id: UUID,
        requester_role: Annotated[RequesterRole, Query()] = RequesterRole.DM,
    ) -> DossierDecisionReceipt:
        if requester_role is not RequesterRole.DM:
            raise HTTPException(status_code=403, detail="dossier is DM-only")
        return active_dossier.promote(entity_id, claim_id)

    @app.post(
        "/entities/{entity_id}/dossier/{claim_id}/demote",
        response_model=DossierDecisionReceipt,
        tags=["operations"],
    )
    def demote_from_dossier(
        entity_id: UUID,
        claim_id: UUID,
        requester_role: Annotated[RequesterRole, Query()] = RequesterRole.DM,
    ) -> DossierDecisionReceipt:
        if requester_role is not RequesterRole.DM:
            raise HTTPException(status_code=403, detail="dossier is DM-only")
        return active_dossier.demote(entity_id, claim_id)

    class LifeStatusCommand(BaseModel):
        status: str
        since_year: int
        since_month: int
        since_day: int
        claim_id: UUID | None = None  # anchored when detector-confirmed; DM-knowledge sets carry none
        idempotency_key: str = Field(min_length=1)

    @app.get("/campaign/life-status/proposals", tags=["life-status"])
    def life_status_proposals() -> list[dict]:
        return [
            {"entity_id": item.entity_id, "entity_name": item.entity_name,
             "death_claim_id": item.death_claim_id, "death_assertion": item.death_assertion,
             "death_date": item.death_date, "current_status": item.current_status or None}
            for item in active_life_status.proposals()
        ]

    @app.post("/campaign/life-status/{entity_id}", tags=["life-status"])
    def set_life_status(
        entity_id: UUID,
        command: LifeStatusCommand,
        requester_role: Annotated[RequesterRole, Query()] = RequesterRole.DM,
    ) -> dict:
        if requester_role is not RequesterRole.DM:
            raise HTTPException(status_code=403, detail="life status is DM-only")
        try:
            receipt = active_life_status.apply(
                entity_id, command.status, command.since_year, command.since_month,
                command.since_day, command.claim_id, command.idempotency_key)
            return {"receipt_id": str(receipt.receipt_id), "version": receipt.version,
                    "idempotent_replay": receipt.idempotent_replay}
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.get("/campaign/dead-seats", tags=["life-status"])
    def dead_seats() -> list[dict]:
        return [
            {"member_name": seat.member_name, "faction_name": seat.faction_name,
             "role_title": seat.role_title, "is_leadership": seat.is_leadership,
             "life_status_since": seat.life_status_since,
             "member_id": seat.member_id, "faction_id": seat.faction_id}
            for seat in active_life_status.dead_seats()
        ]

    class ConflictDecisionCommand(BaseModel):
        claim_a_id: UUID
        claim_b_id: UUID
        action: str
        reason: str = Field(min_length=1)

    @app.get("/campaign/conflicts", tags=["conflicts"])
    def conflict_queue() -> list[dict]:
        return [
            {"entity_name": pair.entity_name,
             "claim_a_id": pair.claim_a_id, "claim_a_assertion": pair.claim_a_assertion,
             "claim_a_date": pair.claim_a_date,
             "claim_b_id": pair.claim_b_id, "claim_b_assertion": pair.claim_b_assertion,
             "claim_b_date": pair.claim_b_date, "claim_b_authority": pair.claim_b_authority,
             "claim_b_state": pair.claim_b_state}
            for pair in active_conflict_review.queue()
        ]

    @app.post("/campaign/conflicts/decisions", tags=["conflicts"])
    def decide_conflict(
        command: ConflictDecisionCommand,
        requester_role: Annotated[RequesterRole, Query()] = RequesterRole.DM,
    ) -> dict:
        if requester_role is not RequesterRole.DM:
            raise HTTPException(status_code=403, detail="conflict review is DM-only")
        try:
            return active_conflict_review.decide(
                command.claim_a_id, command.claim_b_id, command.action, command.reason)
        except Exception as error:
            from psycopg import errors as psycopg_errors
            if getattr(error, "sqlstate", None) == "P0001":
                raise HTTPException(status_code=409, detail=str(error).splitlines()[0]) from error
            raise

    class SessionDateSetting(BaseModel):
        year: int
        month: int
        day: int
        reason: str | None = None

    @app.get("/campaign/session-dating", tags=["campaign-dating"])
    def session_dating_walk() -> list[dict]:
        return [
            {"document_id": entry.document_id, "path": entry.path, "title": entry.title,
             "session_date": entry.session_date, "year": entry.year, "month": entry.month,
             "day": entry.day, "undated_claims": entry.undated_claims, "dated_by": entry.dated_by}
            for entry in active_session_dating.walk()
        ]

    @app.put("/campaign/session-dating/{document_id}", tags=["campaign-dating"])
    def set_session_document_date(
        document_id: UUID,
        command: SessionDateSetting,
        requester_role: Annotated[RequesterRole, Query()] = RequesterRole.DM,
    ) -> dict:
        if requester_role is not RequesterRole.DM:
            raise HTTPException(status_code=403, detail="session dating is DM-only")
        return active_session_dating.set_date(document_id, command.year, command.month,
                                              command.day, command.reason)

    @app.post("/campaign/claim-dates/inherit", tags=["campaign-dating"])
    def inherit_claim_dates(
        requester_role: Annotated[RequesterRole, Query()] = RequesterRole.DM,
    ) -> dict:
        if requester_role is not RequesterRole.DM:
            raise HTTPException(status_code=403, detail="claim date inheritance is DM-only")
        return active_session_dating.inherit()

    @app.get("/campaign/undated-claims", tags=["campaign-dating"])
    def undated_claims(limit: int = 50) -> list[dict]:
        return [
            {"claim_id": entry.claim_id, "assertion": entry.assertion,
             "entities": list(entry.entities), "conflict_relevant": entry.conflict_relevant}
            for entry in active_session_dating.undated_claims(min(limit, 200))
        ]

    @app.get("/campaign/current-date/history", response_model=list[CampaignClockChangeEntry],
             tags=["campaign"])
    def campaign_date_history(limit: int = 10) -> list[CampaignClockChangeEntry]:
        return [
            CampaignClockChangeEntry(
                calendar_id=change.date.calendar_id, year=change.date.year,
                month=change.date.month, day=change.date.day,
                reason=change.reason, changed_by=change.changed_by,
                changed_at=change.changed_at)
            for change in active_clock.history(min(limit, 50))
        ]

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

    @app.get("/entities/{entity_id}/profile",
             response_model=EntityProfile | None, tags=["identity"])
    def get_entity_profile(
        entity_id: Annotated[UUID, Path()],
        requester_role: Annotated[RequesterRole, Query()] = RequesterRole.DM,
    ) -> EntityProfile | None:
        try:
            return active_entity_profiles.get(
                entity_id, RequesterVisibility(role=requester_role))
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error

    @app.put("/entities/{entity_id}/profile",
             response_model=EntityProfileReceipt, tags=["identity"])
    def update_entity_profile(
        request: UpdateEntityProfileCommand,
        entity_id: Annotated[UUID, Path()],
        requester_role: Annotated[RequesterRole, Query()] = RequesterRole.DM,
    ) -> EntityProfileReceipt:
        try:
            command = request.model_copy(update={"entity_id": entity_id})
            return active_entity_profiles.update(
                command, RequesterVisibility(role=requester_role))
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    from dm_assistant_core.application.identity_gaps import (  # noqa: E402
        AddAliasDecision,
        CreateEntityDecision,
        IdentityGapQueue,
        IdentityDecisionReceipt,
        FactionRoleSummary,
        IdentityDecisionEntry,
        MarkMisspellingDecision,
        RoleDeclarationSummary,
        MembershipDecision,
        RevertDecision,
        RoleDecision,
        RoleDefinitionDecision,
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

    @app.post("/identity/decisions/revert",
              response_model=IdentityDecisionReceipt, tags=["identity"])
    def identity_revert(
        request: RevertDecision,
        requester_role: Annotated[RequesterRole, Query()] = RequesterRole.DM,
    ) -> IdentityDecisionReceipt:
        try:
            _identity_dm(requester_role)
            return active_identity_queue.revert(request)
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error
        except IdentityQueueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.post("/identity/decisions/mark-misspelling",
              response_model=IdentityDecisionReceipt, tags=["identity"])
    def identity_mark_misspelling(
        request: MarkMisspellingDecision,
        requester_role: Annotated[RequesterRole, Query()] = RequesterRole.DM,
    ) -> IdentityDecisionReceipt:
        try:
            _identity_dm(requester_role)
            return active_identity_queue.mark_misspelling(request)
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error
        except IdentityQueueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.post("/identity/decisions/membership",
              response_model=IdentityDecisionReceipt, tags=["identity"])
    def identity_membership(
        request: MembershipDecision,
        requester_role: Annotated[RequesterRole, Query()] = RequesterRole.DM,
    ) -> IdentityDecisionReceipt:
        try:
            _identity_dm(requester_role)
            return active_identity_queue.membership(request)
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error
        except IdentityQueueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.post("/identity/decisions/role",
              response_model=IdentityDecisionReceipt, tags=["identity"])
    def identity_role(
        request: RoleDecision,
        requester_role: Annotated[RequesterRole, Query()] = RequesterRole.DM,
    ) -> IdentityDecisionReceipt:
        try:
            _identity_dm(requester_role)
            return active_identity_queue.role(request)
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error
        except IdentityQueueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.post("/identity/decisions/define-role",
              response_model=IdentityDecisionReceipt, tags=["identity"])
    def identity_define_role(
        request: RoleDefinitionDecision,
        requester_role: Annotated[RequesterRole, Query()] = RequesterRole.DM,
    ) -> IdentityDecisionReceipt:
        try:
            _identity_dm(requester_role)
            return active_identity_queue.define_role(request)
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error
        except IdentityQueueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.get("/identity/roles",
             response_model=list[FactionRoleSummary], tags=["identity"])
    def identity_roles() -> list[FactionRoleSummary]:
        return list(active_identity_queue.roles())

    @app.get("/identity/role-declarations",
             response_model=list[RoleDeclarationSummary], tags=["identity"])
    def identity_role_declarations() -> list[RoleDeclarationSummary]:
        return list(active_identity_queue.role_declarations())

    @app.get("/identity/decisions/recent",
             response_model=list[IdentityDecisionEntry], tags=["identity"])
    def identity_recent_decisions(limit: int = 100) -> list[IdentityDecisionEntry]:
        return list(active_identity_queue.recent_decisions(min(limit, 500)))

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
            effective_extraction_prompt = active_prompt_configuration.effective("extraction")
            service = _default_candidate_extraction_service(
                active_settings, active_ai_configuration.active_profile("extraction"),
                system_prompt=effective_extraction_prompt.prompt_text,
                prompt_version=effective_extraction_prompt.version_label,
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
        "/prose/draft",
        response_model=ProseDraftResult,
        tags=["operations"],
    )
    def draft_prose(
        command: ProseDraftCommand,
        requester_role: Annotated[RequesterRole, Query()] = RequesterRole.DM,
    ) -> ProseDraftResult:
        """Draft prose from selected material with the active prose model.

        Non-mutating: a draft is a machine-drafted suggestion the DM disposes
        of through the normal authoring path — no campaign records change.
        """
        if requester_role is not RequesterRole.DM:
            raise HTTPException(status_code=403, detail="prose drafting is DM-only")
        service = active_prose_drafting
        if service is None:
            try:
                profile = active_ai_configuration.active_profile("prose")
            except ValueError as error:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        "no prose model is active — activate one in Settings "
                        "(AI models) first"
                    ),
                ) from error
            if not active_settings.openrouter_api_key:
                raise HTTPException(
                    status_code=503,
                    detail="prose drafting is not configured (no AI provider key)",
                )
            effective = active_prompt_configuration.effective("prose")
            service = _default_prose_drafting_service(
                active_settings, profile,
                system_prompt=effective.prompt_text, prompt_version=effective.version_label)
        try:
            return service.draft(command)
        except ProseDraftError as error:
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
    *,
    system_prompt: str | None = None,
    prompt_version: str | None = None,
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
    harness = (
        ExtractionHarness(client, system_prompt=system_prompt)
        if system_prompt is not None else ExtractionHarness(client)
    )
    if prompt_version is not None:
        effective_version = prompt_version
    elif profile:
        effective_version = next(
            purpose.prompt_version
            for purpose in PURPOSES
            if purpose.key == profile.purpose and purpose.prompt_version
        )
    else:
        effective_version = harness.extractor_version
    return CandidateExtractionService(
        PostgresCandidateExtractionRepository(PostgresDatabase(settings.database_dsn)),
        harness,
        model_profile_key=profile.key if profile else None,
        model_slug=active_model,
        prompt_version=effective_version,
    )


def _default_prose_drafting_service(
    settings: Settings,
    profile: ModelProfile,
    *,
    system_prompt: str | None = None,
    prompt_version: str | None = None,
) -> ProseDraftingService:
    """Build the prose writer from the active prose profile (per request)."""
    from dm_assistant_core.adapters.openrouter import OpenRouterClient

    client = OpenRouterClient(
        api_key=settings.openrouter_api_key,
        base_url=settings.openrouter_base_url,
        model=profile.model_slug,
        max_tokens=profile.max_tokens,
        timeout_seconds=profile.timeout_seconds,
        max_retries=profile.retry_limit,
        reasoning_effort=profile.reasoning_effort,
    )
    harness = (
        ProseHarness(client, system_prompt=system_prompt)
        if system_prompt is not None else ProseHarness(client)
    )
    return ProseDraftingService(
        harness,
        model_slug=profile.model_slug,
        **({"prompt_version": prompt_version} if prompt_version is not None else {}),
    )
