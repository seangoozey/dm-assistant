from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from dm_assistant_core.application.brainstorms import (
    BrainstormError,
    BrainstormEvidencePin,
    BrainstormPin,
    BrainstormService,
    BrainstormSession,
    BrainstormThought,
    CaptureBrainstormThoughtCommand,
    CloseBrainstormCommand,
    StartBrainstormCommand,
)
from dm_assistant_core.application.direct_capture import DirectInputMention
from dm_assistant_core.application.retrieval import RetrievalService
from dm_assistant_core.domain import (
    ClaimState,
    RetrievalAuthority,
    RetrievalRecord,
    RetrievalRecordKind,
)


class RecordingImports:
    def __init__(self) -> None:
        self.batch = None
        self.document_id = uuid4()
        self.revision_id = uuid4()
        self.candidate_id = uuid4()

    def ingest(self, batch):
        self.batch = batch
        return SimpleNamespace(
            observation=SimpleNamespace(
                files=(
                    SimpleNamespace(
                        source_document_id=self.document_id,
                        source_revision_id=self.revision_id,
                        candidate_ids=(self.candidate_id,),
                    ),
                )
            )
        )


class CanonRepository:
    def __init__(self) -> None:
        self.questions: list[str] = []

    def relevant_records(self, query):
        self.questions.append(query.question)
        return (
            RetrievalRecord(
                record_id="claim-1",
                kind=RetrievalRecordKind.CLAIM,
                assertion="Malygos intends to end mortality on Myrin.",
                state=ClaimState.ESTABLISHED,
                authority=RetrievalAuthority.EXPLICIT_LORE,
                visibility="dm",
                source_id="source-1",
                citation="lore/infinite-twilight#overview",
                accepted=True,
            ),
        )


class MemoryBrainstorms:
    def __init__(self) -> None:
        self.session: BrainstormSession | None = None

    def start(self, command):
        if self.session and self.session.status == "open":
            return self.session
        self.session = BrainstormSession(
            session_id=uuid4(),
            title=command.title,
            status="open",
            started_at=datetime.now(UTC),
        )
        return self.session

    def get(self, session_id):
        return self.session if self.session and self.session.session_id == session_id else None

    def get_open(self):
        return self.session if self.session and self.session.status == "open" else None

    def add_thought(self, **values):
        assert self.session is not None
        thought = BrainstormThought(
            thought_id=values["thought_id"],
            sequence=len(self.session.thoughts) + 1,
            text=values["text"],
            source_document_id=values["source_document_id"],
            source_revision_id=values["source_revision_id"],
            candidate_id=values["candidate_id"],
            captured_at=values["captured_at"],
            evidence=values["evidence"],
            mentions=values["mentions"],
        )
        self.session = self.session.model_copy(
            update={"thoughts": (*self.session.thoughts, thought)}
        )
        return self.session

    def pin(self, session_id, entity_id):
        assert self.session is not None and self.session.session_id == session_id
        pin = BrainstormPin(
            entity_id=entity_id,
            canonical_name="Malygos",
            entity_kind="npc",
            position=len(self.session.pins) + 1,
            pinned_at=datetime.now(UTC),
        )
        self.session = self.session.model_copy(update={"pins": (*self.session.pins, pin)})
        return self.session

    def unpin(self, session_id, entity_id):
        assert self.session is not None and self.session.session_id == session_id
        self.session = self.session.model_copy(
            update={"pins": tuple(pin for pin in self.session.pins if pin.entity_id != entity_id)}
        )
        return self.session

    def pin_evidence(self, session_id, evidence):
        assert self.session is not None and self.session.session_id == session_id
        pin = BrainstormEvidencePin(
            record_id=evidence.record_id,
            assertion=evidence.assertion,
            citation=evidence.citation,
            entity_id=evidence.entity_id,
            position=len(self.session.evidence_pins) + 1,
            pinned_at=datetime.now(UTC),
        )
        self.session = self.session.model_copy(
            update={"evidence_pins": (*self.session.evidence_pins, pin)}
        )
        return self.session

    def unpin_evidence(self, session_id, record_id):
        assert self.session is not None and self.session.session_id == session_id
        self.session = self.session.model_copy(
            update={"evidence_pins": tuple(
                pin for pin in self.session.evidence_pins if pin.record_id != record_id
            )}
        )
        return self.session

    def close(self, session_id, command):
        if not self.session or self.session.session_id != session_id:
            raise BrainstormError("brainstorm session does not exist")
        self.session = self.session.model_copy(
            update={
                "status": "closed",
                "closed_at": datetime.now(UTC),
                "proposal_id": command.proposal_id,
            }
        )
        return self.session


def test_brainstorm_preserves_verbatim_noncanon_input_and_refreshes_grounded_evidence() -> None:
    repository = MemoryBrainstorms()
    imports = RecordingImports()
    service = BrainstormService(
        repository, imports, RetrievalService(CanonRepository())  # type: ignore[arg-type]
    )
    session = service.start(
        StartBrainstormCommand(title="Infinite Twilight", idempotency_key="brainstorm:start:1")
    )
    text = "Malygos might reroute Myrin's lifeforce into a reflecting point.\n"

    updated = service.capture(
        session.session_id,
        CaptureBrainstormThoughtCommand(text=text, idempotency_key="brainstorm:thought:1"),
    )

    assert imports.batch is not None
    source = imports.batch.files[0]
    assert source.content.decode("utf-8") == text
    assert source.classification.value == "noncanon_evidence"
    assert source.frontmatter["workflow_session_id"] == str(session.session_id)
    assert len(source.candidates) == 1
    assert source.candidates[0].state.value == "possible"
    assert source.candidates[0].authority.value == "brainstorm"
    assert updated.thoughts[0].text == text
    assert updated.thoughts[0].candidate_id == imports.candidate_id
    assert [item.assertion for item in updated.thoughts[0].evidence.evidence] == [
        "Malygos intends to end mortality on Myrin."
    ]


def test_brainstorm_close_retains_thoughts_and_binds_exact_proposal() -> None:
    repository = MemoryBrainstorms()
    service = BrainstormService(
        repository, RecordingImports(), RetrievalService(CanonRepository())  # type: ignore[arg-type]
    )
    session = service.start(
        StartBrainstormCommand(title="Coalition", idempotency_key="brainstorm:start:2")
    )
    proposal_id = uuid4()

    closed = service.close(
        session.session_id, CloseBrainstormCommand(proposal_id=proposal_id)
    )

    assert closed.status == "closed"
    assert closed.proposal_id == proposal_id


def test_closed_brainstorm_rejects_new_thoughts() -> None:
    repository = MemoryBrainstorms()
    service = BrainstormService(
        repository, RecordingImports(), RetrievalService(CanonRepository())  # type: ignore[arg-type]
    )
    session = service.start(
        StartBrainstormCommand(title="Closed", idempotency_key="brainstorm:start:3")
    )
    service.close(session.session_id, CloseBrainstormCommand(proposal_id=uuid4()))

    try:
        service.capture(
            session.session_id,
            CaptureBrainstormThoughtCommand(text="Late thought", idempotency_key="late"),
        )
    except BrainstormError as error:
        assert str(error) == "closed brainstorm cannot accept new thoughts"
    else:
        raise AssertionError("closed brainstorm accepted a thought")


def test_brainstorm_mentions_are_preserved_and_pins_supply_retrieval_context() -> None:
    repository = MemoryBrainstorms()
    imports = RecordingImports()
    canon = CanonRepository()
    service = BrainstormService(repository, imports, RetrievalService(canon))  # type: ignore[arg-type]
    session = service.start(
        StartBrainstormCommand(title="Pinned context", idempotency_key="brainstorm:start:4")
    )
    entity_id = uuid4()
    service.pin(session.session_id, entity_id)
    text = "Could @Malygos conceal the archive?"
    mention = DirectInputMention(
        entity_id=entity_id,
        display_name="Malygos",
        start_offset=6,
        end_offset=14,
    )

    updated = service.capture(
        session.session_id,
        CaptureBrainstormThoughtCommand(
            text=text,
            mentions=(mention,),
            idempotency_key="brainstorm:thought:4",
        ),
    )

    assert updated.thoughts[0].mentions == (mention,)
    assert imports.batch.files[0].frontmatter["mentions"][0]["entity_id"] == str(entity_id)
    assert canon.questions == [f"{text}\nPinned context: Malygos"]


def test_brainstorm_rejects_inaccurate_mention_offsets() -> None:
    repository = MemoryBrainstorms()
    service = BrainstormService(
        repository, RecordingImports(), RetrievalService(CanonRepository())  # type: ignore[arg-type]
    )
    session = service.start(
        StartBrainstormCommand(title="Mentions", idempotency_key="brainstorm:start:5")
    )

    try:
        service.capture(
            session.session_id,
            CaptureBrainstormThoughtCommand(
                text="Ask @Malygos",
                mentions=(DirectInputMention(
                    entity_id=uuid4(), display_name="Malygos", start_offset=0, end_offset=8
                ),),
                idempotency_key="brainstorm:thought:5",
            ),
        )
    except BrainstormError as error:
        assert "mention offsets" in str(error)
    else:
        raise AssertionError("brainstorm accepted inaccurate mention offsets")


def test_exact_evidence_pin_is_validated_and_supplies_later_retrieval_context() -> None:
    repository = MemoryBrainstorms()
    imports = RecordingImports()
    canon = CanonRepository()
    service = BrainstormService(repository, imports, RetrievalService(canon))  # type: ignore[arg-type]
    session = service.start(
        StartBrainstormCommand(title="Exact evidence", idempotency_key="brainstorm:start:6")
    )
    captured = service.capture(
        session.session_id,
        CaptureBrainstormThoughtCommand(text="First thought", idempotency_key="thought:6:1"),
    )

    pinned = service.pin_evidence(captured.session_id, "claim-1")
    assert pinned.evidence_pins[0].assertion == "Malygos intends to end mortality on Myrin."
    service.capture(
        session.session_id,
        CaptureBrainstormThoughtCommand(text="Second thought", idempotency_key="thought:6:2"),
    )
    assert canon.questions[-1] == (
        "Second thought\nPinned context: Malygos intends to end mortality on Myrin."
    )

    unpinned = service.unpin_evidence(session.session_id, "claim-1")
    assert unpinned.evidence_pins == ()


def test_search_evidence_can_be_pinned_before_any_thought_and_rejects_unknown_ids() -> None:
    import pytest

    repository = MemoryBrainstorms()
    service = BrainstormService(
        repository, RecordingImports(), RetrievalService(CanonRepository())  # type: ignore[arg-type]
    )
    session = service.start(StartBrainstormCommand(title="Search", idempotency_key="search-pin"))
    pinned = service.pin_evidence(session.session_id, "claim-1", "Malygos")
    assert pinned.evidence_pins[0].entity_id is None
    assert pinned.evidence_pins[0].citation == "lore/infinite-twilight#overview"
    with pytest.raises(BrainstormError, match="search results"):
        service.pin_evidence(session.session_id, "unknown", "Malygos")
