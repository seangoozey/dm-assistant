import asyncio
from datetime import UTC, datetime
from uuid import UUID

import httpx

from dm_assistant_core.api.app import create_app
from dm_assistant_core.application import (
    ApproveCandidateProposalCommand,
    CandidateDisposition,
    CandidateDispositionResult,
    CandidateProposalApproval,
    CandidateProposalError,
    CandidateProposalItem,
    CandidateProposalService,
    CandidateProposalVersion,
    CreateCandidateProposalCommand,
    DispositionCandidateCommand,
    ProposalCandidateBinding,
    ReviseCandidateProposalCommand,
)
from dm_assistant_core.config import Settings

PROPOSAL_ID = UUID("10000000-0000-0000-0000-000000000001")
WORKFLOW_ID = UUID("20000000-0000-0000-0000-000000000001")
VERSION_ID = UUID("30000000-0000-0000-0000-000000000001")
ITEM_ID = UUID("40000000-0000-0000-0000-000000000001")
CANDIDATE_ID = UUID("50000000-0000-0000-0000-000000000001")
REVISION_ID = UUID("60000000-0000-0000-0000-000000000001")
SPAN_ID = UUID("70000000-0000-0000-0000-000000000001")
TARGET_ID = UUID("80000000-0000-0000-0000-000000000001")
APPROVAL_ID = UUID("90000000-0000-0000-0000-000000000001")
CHANGE_SET_ID = UUID("a0000000-0000-0000-0000-000000000001")
DISPOSITION_ID = UUID("b0000000-0000-0000-0000-000000000001")
CONTENT_HASH = "a" * 64
NOW = datetime(2026, 8, 1, 12, tzinfo=UTC)


def version() -> CandidateProposalVersion:
    return CandidateProposalVersion(
        proposal_id=PROPOSAL_ID,
        workflow_session_id=WORKFLOW_ID,
        status="pending",
        version_id=VERSION_ID,
        version_number=1,
        content_hash=CONTENT_HASH,
        supersedes_version_id=None,
        created_at=NOW,
        items=(
            CandidateProposalItem(
                item_id=ITEM_ID,
                sequence=1,
                mutation_kind="create_entity",
                target_type="entity",
                target_id=TARGET_ID,
                after={
                    "id": str(TARGET_ID),
                    "entity_type": "npc",
                    "canonical_name": "Sanitized Keeper",
                },
                evidence=ProposalCandidateBinding(
                    candidate_id=CANDIDATE_ID,
                    source_revision_id=REVISION_ID,
                    source_span_id=SPAN_ID,
                    candidate_fingerprint="b" * 64,
                ),
            ),
        ),
    )


class RecordingRepository:
    def __init__(self, *, reject: bool = False) -> None:
        self.reject = reject
        self.created: CreateCandidateProposalCommand | None = None
        self.revised: ReviseCandidateProposalCommand | None = None
        self.approved: ApproveCandidateProposalCommand | None = None
        self.dispositioned: DispositionCandidateCommand | None = None

    def create(self, command: CreateCandidateProposalCommand) -> CandidateProposalVersion:
        self.created = command
        if self.reject:
            raise CandidateProposalError("candidate is not promotable")
        return version()

    def revise(self, command: ReviseCandidateProposalCommand) -> CandidateProposalVersion:
        self.revised = command
        return version().model_copy(update={"version_number": 2})

    def get(self, proposal_id: UUID) -> CandidateProposalVersion | None:
        return version() if proposal_id == PROPOSAL_ID else None

    def approve(self, command: ApproveCandidateProposalCommand) -> CandidateProposalApproval:
        self.approved = command
        return CandidateProposalApproval(
            proposal_id=PROPOSAL_ID,
            proposal_version_id=VERSION_ID,
            reviewed_version=1,
            content_hash=CONTENT_HASH,
            approval_id=APPROVAL_ID,
            change_set_id=CHANGE_SET_ID,
            item_ids=(ITEM_ID,),
            idempotency_key="api-test",
            approved_at=NOW,
            idempotent_replay=False,
        )

    def disposition(self, command: DispositionCandidateCommand) -> CandidateDispositionResult:
        self.dispositioned = command
        return CandidateDispositionResult(
            disposition_id=DISPOSITION_ID,
            candidate_id=CANDIDATE_ID,
            review_status=command.disposition,
            reason=command.reason,
            created_at=NOW,
        )


def settings() -> Settings:
    return Settings(
        database_url="postgresql://campaign:secret@localhost:5432/campaign",
        run_migrations=False,
    )


def item_body() -> dict[str, str]:
    return {
        "mutation_kind": "create_entity",
        "candidate_id": str(CANDIDATE_ID),
        "evidence_revision_id": str(REVISION_ID),
        "target_id": str(TARGET_ID),
        "entity_type": "npc",
        "canonical_name": "Sanitized Keeper",
    }


def test_candidate_commands_bind_exact_human_selection() -> None:
    repository = RecordingRepository()
    app = create_app(settings(), candidate_proposals=CandidateProposalService(repository))

    async def exercise() -> tuple[httpx.Response, ...]:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            created = await client.post(
                "/imports/proposals?requester_role=dm", json={"items": [item_body()]}
            )
            revised = await client.post(
                f"/imports/proposals/{PROPOSAL_ID}/versions?requester_role=dm",
                json={"items": [item_body()]},
            )
            approved = await client.post(
                f"/imports/proposals/{PROPOSAL_ID}/approvals?requester_role=dm",
                json={
                    "reviewed_version": 1,
                    "content_hash": CONTENT_HASH,
                    "item_ids": [str(ITEM_ID)],
                    "idempotency_key": "api-test",
                },
            )
            dispositioned = await client.post(
                f"/imports/candidates/{CANDIDATE_ID}/disposition?requester_role=dm",
                json={"disposition": "deferred", "reason": "Needs identity review"},
            )
            return created, revised, approved, dispositioned

    created, revised, approved, dispositioned = asyncio.run(exercise())
    assert {created.status_code, revised.status_code, approved.status_code} == {200}
    assert dispositioned.status_code == 200
    assert repository.created is not None
    assert repository.created.items[0].candidate_id == CANDIDATE_ID
    assert repository.revised == ReviseCandidateProposalCommand(
        proposal_id=PROPOSAL_ID, items=repository.created.items
    )
    assert repository.approved == ApproveCandidateProposalCommand(
        proposal_id=PROPOSAL_ID,
        reviewed_version=1,
        content_hash=CONTENT_HASH,
        item_ids=(ITEM_ID,),
        idempotency_key="api-test",
    )
    assert repository.dispositioned == DispositionCandidateCommand(
        candidate_id=CANDIDATE_ID,
        disposition=CandidateDisposition.DEFERRED,
        reason="Needs identity review",
    )


def test_candidate_commands_are_dm_only_and_fail_closed() -> None:
    repository = RecordingRepository(reject=True)
    app = create_app(settings(), candidate_proposals=CandidateProposalService(repository))

    async def exercise() -> tuple[httpx.Response, httpx.Response, httpx.Response]:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            forbidden = await client.post(
                "/imports/proposals?requester_role=party", json={"items": [item_body()]}
            )
            rejected = await client.post(
                "/imports/proposals?requester_role=dm", json={"items": [item_body()]}
            )
            missing = await client.get(
                "/imports/proposals/ffffffff-ffff-ffff-ffff-ffffffffffff?requester_role=dm"
            )
            return forbidden, rejected, missing

    forbidden, rejected, missing = asyncio.run(exercise())
    assert forbidden.status_code == 403
    assert rejected.status_code == 409
    assert missing.status_code == 404
