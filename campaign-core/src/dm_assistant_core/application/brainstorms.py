"""Durable, non-canonical Brainstorm workflow sessions."""

from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
from typing import Protocol
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from dm_assistant_core.application.direct_capture import DirectInputMention
from dm_assistant_core.application.imports import MarkdownImportService
from dm_assistant_core.application.retrieval import RetrievalService
from dm_assistant_core.domain import (
    ClaimState,
    RequesterRole,
    RequesterVisibility,
    RetrievalQuery,
    RetrievalResult,
    RetrievedEvidence,
    Visibility,
)
from dm_assistant_core.importer import (
    CandidateAuthority,
    ImportCandidate,
    ImportClassification,
    ImportOutcome,
    MarkdownScanBatch,
    ScannedSource,
)


class StartBrainstormCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    title: str = Field(min_length=1, max_length=200)
    idempotency_key: str = Field(min_length=1)


class CaptureBrainstormThoughtCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    text: str = Field(min_length=1, max_length=20_000)
    idempotency_key: str = Field(min_length=1)
    mentions: tuple[DirectInputMention, ...] = ()


class BrainstormPin(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    entity_id: UUID
    canonical_name: str
    entity_kind: str
    position: int = Field(gt=0)
    pinned_at: datetime


class BrainstormEvidencePin(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    record_id: str
    assertion: str
    citation: str
    entity_id: UUID | None = None
    position: int = Field(gt=0)
    pinned_at: datetime


class CloseBrainstormCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    proposal_id: UUID


class BrainstormThought(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    thought_id: UUID
    sequence: int = Field(gt=0)
    text: str
    source_document_id: UUID
    source_revision_id: UUID
    candidate_id: UUID
    captured_at: datetime
    evidence: RetrievalResult
    mentions: tuple[DirectInputMention, ...] = ()


class BrainstormSession(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    session_id: UUID
    title: str
    status: str
    started_at: datetime
    closed_at: datetime | None = None
    proposal_id: UUID | None = None
    thoughts: tuple[BrainstormThought, ...] = ()
    pins: tuple[BrainstormPin, ...] = ()
    evidence_pins: tuple[BrainstormEvidencePin, ...] = ()


class BrainstormRepository(Protocol):
    def start(self, command: StartBrainstormCommand) -> BrainstormSession: ...
    def get(self, session_id: UUID) -> BrainstormSession | None: ...
    def get_open(self) -> BrainstormSession | None: ...
    def add_thought(
        self,
        *,
        session_id: UUID,
        thought_id: UUID,
        text: str,
        source_document_id: UUID,
        source_revision_id: UUID,
        candidate_id: UUID,
        evidence: RetrievalResult,
        mentions: tuple[DirectInputMention, ...],
        idempotency_key: str,
        captured_at: datetime,
    ) -> BrainstormSession: ...
    def pin(self, session_id: UUID, entity_id: UUID) -> BrainstormSession: ...
    def unpin(self, session_id: UUID, entity_id: UUID) -> BrainstormSession: ...
    def pin_evidence(
        self, session_id: UUID, evidence: RetrievedEvidence
    ) -> BrainstormSession: ...
    def unpin_evidence(self, session_id: UUID, record_id: str) -> BrainstormSession: ...
    def close(self, session_id: UUID, command: CloseBrainstormCommand) -> BrainstormSession: ...


class BrainstormError(ValueError):
    """A Brainstorm operation violates session or preservation rules."""


class BrainstormService:
    def __init__(
        self,
        repository: BrainstormRepository,
        imports: MarkdownImportService,
        retrieval: RetrievalService,
    ) -> None:
        self._repository = repository
        self._imports = imports
        self._retrieval = retrieval

    def start(self, command: StartBrainstormCommand) -> BrainstormSession:
        return self._repository.start(command)

    def get(self, session_id: UUID) -> BrainstormSession | None:
        return self._repository.get(session_id)

    def get_open(self) -> BrainstormSession | None:
        return self._repository.get_open()

    def capture(
        self, session_id: UUID, command: CaptureBrainstormThoughtCommand
    ) -> BrainstormSession:
        session = self._repository.get(session_id)
        if session is None:
            raise BrainstormError("brainstorm session does not exist")
        if session.status != "open":
            raise BrainstormError("closed brainstorm cannot accept new thoughts")
        text = command.text
        if not text.strip():
            raise BrainstormError("brainstorm thought cannot be blank")
        thought_id = uuid4()
        captured_at = datetime.now(UTC)
        encoded = text.encode("utf-8")
        mention_payload = []
        for mention in command.mentions:
            token = text[mention.start_offset : mention.end_offset]
            if token != f"@{mention.display_name}":
                raise BrainstormError(f"mention offsets do not match @{mention.display_name}")
            mention_payload.append(mention.model_dump(mode="json"))
        fingerprint = sha256(
            f"direct-input/brainstorm-v1\x00{text}".encode()
        ).hexdigest()
        source = ScannedSource(
            path=f"gm/brainstorming/direct/{session_id}/{thought_id}",
            content_hash=sha256(encoded).hexdigest(),
            content=encoded,
            filesystem_modified_at=captured_at,
            external_id=str(thought_id),
            canonical_name=session.title,
            frontmatter={
                "type": "brainstorm",
                "name": session.title,
                "capture_mode": "direct_input",
                "workflow_session_id": str(session_id),
                "thought_id": str(thought_id),
                "mentions": mention_payload,
            },
            classification=ImportClassification.NONCANON_EVIDENCE,
            proposed_outcome=ImportOutcome.NEW,
            candidates=(
                ImportCandidate(
                    fingerprint=fingerprint,
                    section="Brainstorm thought",
                    assertion_text=text.strip(),
                    state=ClaimState.POSSIBLE,
                    authority=CandidateAuthority.BRAINSTORM,
                    visibility=Visibility.DM_ONLY,
                    start_offset=0,
                    end_offset=len(text),
                    extractor_version="direct-input/brainstorm-v1",
                ),
            ),
            entity_candidates=0,
            warnings=(),
        )
        receipt = self._imports.ingest(
            MarkdownScanBatch(
                root_identifier=f"direct-input:brainstorm:{session_id}",
                snapshot_at=captured_at,
                importer_version="direct-input/brainstorm-v1",
                parser_version="direct-input/brainstorm-v1",
                path_policy_version="direct-input/brainstorm-v1",
                idempotency_key=command.idempotency_key,
                excluded_paths_encountered=(),
                files=(source,),
            )
        )
        outcome = receipt.observation.files[0]
        if (
            outcome.source_document_id is None
            or outcome.source_revision_id is None
            or not outcome.candidate_ids
        ):
            raise RuntimeError("brainstorm capture did not produce reviewable evidence")
        pinned_context = "\n".join(
            [*(pin.canonical_name for pin in session.pins),
             *(pin.assertion for pin in session.evidence_pins)]
        )
        question = f"{text}\nPinned context: {pinned_context}" if pinned_context else text
        evidence = self._retrieval.query(
            RetrievalQuery(
                question=question,
                requester_visibility=RequesterVisibility(role=RequesterRole.DM),
            )
        )
        return self._repository.add_thought(
            session_id=session_id,
            thought_id=thought_id,
            text=text,
            source_document_id=outcome.source_document_id,
            source_revision_id=outcome.source_revision_id,
            candidate_id=outcome.candidate_ids[0],
            evidence=evidence,
            mentions=command.mentions,
            idempotency_key=command.idempotency_key,
            captured_at=captured_at,
        )

    def close(self, session_id: UUID, command: CloseBrainstormCommand) -> BrainstormSession:
        return self._repository.close(session_id, command)

    def pin(self, session_id: UUID, entity_id: UUID) -> BrainstormSession:
        return self._repository.pin(session_id, entity_id)

    def unpin(self, session_id: UUID, entity_id: UUID) -> BrainstormSession:
        return self._repository.unpin(session_id, entity_id)

    def pin_evidence(
        self, session_id: UUID, record_id: str, search_query: str | None = None
    ) -> BrainstormSession:
        session = self._repository.get(session_id)
        if session is None:
            raise BrainstormError("brainstorm session does not exist")
        evidence = next(
            (
                item
                for thought in reversed(session.thoughts)
                for item in thought.evidence.evidence
                if item.record_id == record_id
            ),
            None,
        )
        if search_query:
            result = self._retrieval.query(RetrievalQuery(
                question=search_query,
                requester_visibility=RequesterVisibility(role=RequesterRole.DM),
            ))
            evidence = next((item for item in result.evidence if item.record_id == record_id), None)
        if evidence is None:
            raise BrainstormError("evidence pin is not part of this brainstorm or search results")
        return self._repository.pin_evidence(session_id, evidence)

    def unpin_evidence(self, session_id: UUID, record_id: str) -> BrainstormSession:
        return self._repository.unpin_evidence(session_id, record_id)
