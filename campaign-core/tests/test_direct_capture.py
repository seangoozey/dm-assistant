from datetime import date
from types import SimpleNamespace
from uuid import uuid4

from dm_assistant_core.application.direct_capture import (
    DirectInputMention,
    SessionNoteCaptureCommand,
    SessionNoteCaptureService,
)
from dm_assistant_core.domain.chronology import CampaignDate


class RecordingImports:
    def __init__(self) -> None:
        self.batch = None

    def ingest(self, batch):
        self.batch = batch
        return SimpleNamespace(
            observation=SimpleNamespace(
                files=(
                    SimpleNamespace(
                        source_document_id=uuid4(),
                        source_revision_id=uuid4(),
                        candidate_ids=(uuid4(),),
                    ),
                )
            ),
            idempotent_replay=False,
        )


class RecordingClock:
    current = None

    def get_current(self):
        return self.current

    def set_current(self, value):
        self.current = value


def test_session_note_capture_preserves_exact_input_and_review_dimensions() -> None:
    imports = RecordingImports()
    clock = RecordingClock()
    service = SessionNoteCaptureService(imports, clock)  # type: ignore[arg-type]
    text = "@Coreferra became the Herald of Arkin.\nThe table ended here.  "
    coreferra_id = uuid4()

    receipt = service.capture(
        SessionNoteCaptureCommand(
            session_date=date(2026, 6, 20),
            in_game_date=CampaignDate(year=505, month=6, day=20),
            title="Return to the Monastery",
            text=text,
            mentions=(
                DirectInputMention(
                    entity_id=coreferra_id,
                    display_name="Coreferra",
                    start_offset=0,
                    end_offset=10,
                ),
            ),
            idempotency_key="capture-session-note:test:1",
        )
    )

    assert receipt.candidate_id
    assert imports.batch is not None
    source = imports.batch.files[0]
    assert source.content.decode("utf-8") == text
    assert source.frontmatter["capture_mode"] == "direct_input"
    assert source.frontmatter["session_date"] == "2026-06-20"
    assert source.frontmatter["in_game_date"] == {
        "calendar_id": "gregorian-ce",
        "year": 505,
        "month": 6,
        "day": 20,
    }
    assert source.classification.value == "real_play_evidence"
    assert source.frontmatter["mentions"] == [
        {
            "entity_id": str(coreferra_id),
            "display_name": "Coreferra",
            "start_offset": 0,
            "end_offset": 10,
        }
    ]
    assert len(source.candidates) == 2
    candidate = source.candidates[0]
    assert candidate.assertion_text == "Coreferra became the Herald of Arkin."
    assert candidate.start_offset == 0
    assert candidate.end_offset == 38
    assert candidate.state.value == "observed"
    assert candidate.authority.value == "real_play"
    assert candidate.visibility.value == "dm_only"
    assert imports.batch.root_identifier.startswith("direct-input:session-note:")
    assert clock.current == CampaignDate(year=505, month=6, day=20)


def test_session_note_capture_splits_sentences_without_losing_source_offsets() -> None:
    imports = RecordingImports()
    service = SessionNoteCaptureService(imports, RecordingClock())  # type: ignore[arg-type]
    text = "The party made an agreement. Additionally, Aris allowed the carpet to be moved."

    service.capture(
        SessionNoteCaptureCommand(
            session_date=date(2026, 8, 22),
            in_game_date=CampaignDate(year=505, month=7, day=12),
            title="Exile Camp",
            text=text,
            idempotency_key="capture-session-note:test:sentences",
        )
    )

    assert imports.batch is not None
    candidates = imports.batch.files[0].candidates
    assert [candidate.assertion_text for candidate in candidates] == [
        "The party made an agreement.",
        "Additionally, Aris allowed the carpet to be moved.",
    ]
    assert [text[candidate.start_offset : candidate.end_offset] for candidate in candidates] == [
        "The party made an agreement.",
        "Additionally, Aris allowed the carpet to be moved.",
    ]


def test_session_note_correction_reuses_capture_identity_for_a_new_revision() -> None:
    imports = RecordingImports()
    service = SessionNoteCaptureService(imports, RecordingClock())  # type: ignore[arg-type]
    capture_id = uuid4()

    service.capture(
        SessionNoteCaptureCommand(
            session_date=date(2026, 8, 23),
            in_game_date=CampaignDate(year=505, month=7, day=12),
            title="The Goodman Camp",
            text="The party entered the camp.",
            capture_id=capture_id,
            idempotency_key="capture-session-note:test:revision:1",
        )
    )
    first = imports.batch.files[0]

    service.capture(
        SessionNoteCaptureCommand(
            session_date=date(2026, 8, 23),
            in_game_date=CampaignDate(year=505, month=7, day=12),
            title="The Goodman Camp",
            text="The party entered the camp and spoke with Aris.",
            capture_id=capture_id,
            idempotency_key="capture-session-note:test:revision:2",
        )
    )
    corrected = imports.batch.files[0]

    assert first.external_id == corrected.external_id == str(capture_id)
    assert first.path == corrected.path
    assert first.content != corrected.content
