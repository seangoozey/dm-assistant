import asyncio
from datetime import UTC, date, datetime
from uuid import UUID, uuid4

import httpx

from dm_assistant_core.api.app import create_app
from dm_assistant_core.application.session_runs import (
    CloseSessionRunCommand,
    EncounterProgress,
    OpenSessionRunCommand,
    SaveSessionRunNoteCommand,
    SessionRun,
    SessionRunNote,
    SessionRunService,
    UpdateEncounterProgressCommand,
    summarize_session_encounters,
)
from dm_assistant_core.config import Settings
from dm_assistant_core.domain.chronology import CampaignDate


class MemorySessionRuns:
    def __init__(self) -> None:
        self.current: SessionRun | None = None
        self.progress: dict[UUID, EncounterProgress] = {}

    def get_open(self) -> SessionRun | None:
        if self.current is None or self.current.status != "open":
            return None
        return self.current

    def open(self, command: OpenSessionRunCommand) -> SessionRun:
        now = datetime.now(UTC)
        self.current = SessionRun(
            run_id=uuid4(), status="open", session_date=command.session_date,
            in_game_date=command.in_game_date, title=command.title,
            created_at=now, updated_at=now,
        )
        return self.current

    def save_note(self, run_id: UUID, command: SaveSessionRunNoteCommand) -> SessionRunNote:
        if self.current is None or self.current.run_id != run_id or self.current.status != "open":
            raise ValueError("open session run not found")
        now = datetime.now(UTC)
        note = SessionRunNote(
            run_id=run_id, updated_at=now, **command.model_dump()
        )
        notes = (*[item for item in self.current.notes if item.note_id != note.note_id], note)
        self.current = self.current.model_copy(
            update={
                "notes": tuple(sorted(notes, key=lambda item: item.captured_at)),
                "encounters": summarize_session_encounters(tuple(notes)),
                "updated_at": now,
            }
        )
        return note

    def delete_note(self, run_id: UUID, note_id: UUID) -> bool:
        if self.current is None or self.current.run_id != run_id or self.current.status != "open":
            return False
        notes = tuple(item for item in self.current.notes if item.note_id != note_id)
        if len(notes) == len(self.current.notes):
            return False
        self.current = self.current.model_copy(update={"notes": notes})
        return True

    def close(self, run_id: UUID, command: CloseSessionRunCommand) -> SessionRun:
        if self.current is None or self.current.run_id != run_id or self.current.status != "open":
            raise ValueError("open session run not found")
        self.current = self.current.model_copy(
            update={
                "status": "closed",
                "captured_source_document_id": command.captured_source_document_id,
                "capture_id": command.capture_id,
                "closed_at": datetime.now(UTC),
            }
        )
        return self.current

    def list_encounter_progress(self) -> tuple[EncounterProgress, ...]:
        return tuple(self.progress.values())

    def update_encounter_progress(
        self, command: UpdateEncounterProgressCommand
    ) -> EncounterProgress:
        progress = EncounterProgress(
            source_document_id=command.source_document_id,
            source_path=command.source_path,
            encounter_name=command.encounter_name,
            status=command.status,
            resume_section_key=command.resume_section_key,
            resume_section_title=command.resume_section_title,
            last_session_run_id=command.session_run_id,
            updated_at=datetime.now(UTC),
        )
        self.progress[command.source_document_id] = progress
        return progress


def test_session_run_service_preserves_chronology_and_capture_linkage() -> None:
    repository = MemorySessionRuns()
    service = SessionRunService(repository)
    run = service.open(
        OpenSessionRunCommand(
            session_date=date(2026, 8, 26),
            in_game_date=CampaignDate(year=505, month=7, day=12),
            title="  Exile Camp  ",
        )
    )
    late_id, early_id = uuid4(), uuid4()
    for note_id, minute, text in ((late_id, 2, "Second"), (early_id, 1, "First")):
        service.save_note(
            run.run_id,
            SaveSessionRunNoteCommand(
                note_id=note_id, source_path="encounters/exile-camp-meeting.md",
                encounter_name="Exile Camp Meeting", section_key="common-fire",
                section_title="The Common Fire", text=text,
                captured_at=datetime(2026, 8, 26, 20, minute, tzinfo=UTC),
            ),
        )

    assert run.title == "Exile Camp"
    assert [note.text for note in service.get_open().notes] == ["First", "Second"]  # type: ignore[union-attr]
    source_document_id, capture_id = uuid4(), uuid4()
    closed = service.close(
        run.run_id,
        CloseSessionRunCommand(
            captured_source_document_id=source_document_id,
            capture_id=capture_id,
        ),
    )
    assert closed.status == "closed"
    assert closed.captured_source_document_id == source_document_id
    assert service.get_open() is None


def test_session_run_api_supports_open_save_delete_and_close() -> None:
    repository = MemorySessionRuns()
    settings = Settings(
        database_url="postgresql://campaign:secret@localhost:5432/campaign",
        run_migrations=False,
    )
    app = create_app(settings, session_runs=SessionRunService(repository))
    note_id, encounter_document_id = uuid4(), uuid4()

    async def exercise() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            opened = await client.post(
                "/campaign/session-runs/open?requester_role=dm",
                json={
                    "session_date": "2026-08-26",
                    "in_game_date": {
                        "calendar_id": "gregorian-ce",
                        "year": 505,
                        "month": 7,
                        "day": 12,
                    },
                    "title": "Exile Camp",
                },
            )
            assert opened.status_code == 200, opened.text
            run_id = opened.json()["run_id"]
            saved = await client.put(
                f"/campaign/session-runs/{run_id}/notes/{note_id}?requester_role=dm",
                json={
                    "note_id": str(note_id), "source_path": "encounters/exile-camp-meeting.md",
                    "encounter_name": "Exile Camp Meeting", "section_key": "legwork",
                    "section_title": "Legwork", "text": "The party spoke with Aris.",
                    "captured_at": "2026-08-27T03:00:00Z",
                },
            )
            assert saved.status_code == 200, saved.text
            current = await client.get("/campaign/session-runs/open?requester_role=dm")
            assert current.json()["notes"][0]["text"] == "The party spoke with Aris."
            checkpoint = await client.put(
                f"/campaign/encounters/{encounter_document_id}/progress?requester_role=dm",
                json={
                    "source_document_id": str(encounter_document_id),
                    "source_path": "encounters/exile-camp-meeting.md",
                    "encounter_name": "Exile Camp Meeting",
                    "status": "in_progress",
                    "resume_section_key": "legwork",
                    "resume_section_title": "Legwork",
                    "session_run_id": run_id,
                },
            )
            assert checkpoint.status_code == 200, checkpoint.text
            progress = await client.get(
                "/campaign/encounters/progress?requester_role=dm"
            )
            assert progress.json()[0]["resume_section_title"] == "Legwork"
            deleted = await client.delete(
                f"/campaign/session-runs/{run_id}/notes/{note_id}?requester_role=dm"
            )
            assert deleted.json() == {"note_id": str(note_id), "deleted": True}
            closed = await client.post(
                f"/campaign/session-runs/{run_id}/close?requester_role=dm",
                json={"captured_source_document_id": str(uuid4()), "capture_id": str(uuid4())},
            )
            assert closed.status_code == 200, closed.text
            assert closed.json()["status"] == "closed"

    asyncio.run(exercise())


def test_session_run_keeps_general_notes_separate_and_summarizes_multiple_encounters() -> None:
    repository = MemorySessionRuns()
    service = SessionRunService(repository)
    run = service.open(
        OpenSessionRunCommand(session_date=date(2026, 8, 27), title="Crossing paths")
    )
    notes = (
        SaveSessionRunNoteCommand(
            note_id=uuid4(), context_kind="general", text="The party traveled south.",
            captured_at=datetime(2026, 8, 27, 19, 0, tzinfo=UTC),
        ),
        SaveSessionRunNoteCommand(
            note_id=uuid4(), source_path="encounters/road.md", encounter_name="The Road",
            section_key="arrival", section_title="Arrival", text="Bandits appeared.",
            captured_at=datetime(2026, 8, 27, 19, 5, tzinfo=UTC),
        ),
        SaveSessionRunNoteCommand(
            note_id=uuid4(), source_path="encounters/camp.md", encounter_name="Exile Camp",
            section_key="common-fire", section_title="The Common Fire",
            text="The party reached the fire.",
            captured_at=datetime(2026, 8, 27, 20, 0, tzinfo=UTC),
        ),
    )
    for note in notes:
        service.save_note(run.run_id, note)

    current = service.get_open()
    assert current is not None
    assert [note.text for note in current.notes] == [
        "The party traveled south.", "Bandits appeared.", "The party reached the fire."
    ]
    assert [encounter.encounter_name for encounter in current.encounters] == [
        "The Road", "Exile Camp"
    ]
    assert current.encounters[-1].last_section_title == "The Common Fire"
    assert current.encounters[-1].note_count == 1


def test_encounter_note_requires_context_but_general_note_does_not() -> None:
    service = SessionRunService(MemorySessionRuns())
    run = service.open(OpenSessionRunCommand(session_date=date(2026, 8, 27), title="Context"))
    general = service.save_note(
        run.run_id,
        SaveSessionRunNoteCommand(
            note_id=uuid4(), context_kind="general", text="A general observation.",
            captured_at=datetime(2026, 8, 27, 19, 0, tzinfo=UTC),
        ),
    )
    assert general.encounter_name is None

    try:
        service.save_note(
            run.run_id,
            SaveSessionRunNoteCommand(
                note_id=uuid4(), text="Missing encounter context.",
                captured_at=datetime(2026, 8, 27, 19, 1, tzinfo=UTC),
            ),
        )
    except ValueError as error:
        assert str(error) == "encounter notes require encounter and section context"
    else:
        raise AssertionError("missing encounter context should be rejected")


def test_encounter_checkpoint_and_lifecycle_are_explicit_and_independent_of_session_close() -> None:
    repository = MemorySessionRuns()
    service = SessionRunService(repository)
    run = service.open(OpenSessionRunCommand(session_date=date(2026, 8, 27), title="Camp"))
    document_id = uuid4()
    checkpoint = service.update_encounter_progress(
        UpdateEncounterProgressCommand(
            source_document_id=document_id,
            source_path="encounters/camp.md",
            encounter_name="Exile Camp",
            status="in_progress",
            resume_section_key="common-fire",
            resume_section_title="The Common Fire",
            session_run_id=run.run_id,
        )
    )
    assert checkpoint.status == "in_progress"
    assert checkpoint.resume_section_title == "The Common Fire"

    closed = service.close(
        run.run_id,
        CloseSessionRunCommand(
            captured_source_document_id=uuid4(),
            capture_id=uuid4(),
        ),
    )
    assert closed.status == "closed"
    assert service.list_encounter_progress()[0].status == "in_progress"

    completed = service.update_encounter_progress(
        UpdateEncounterProgressCommand(
            source_document_id=document_id,
            source_path="encounters/camp.md",
            encounter_name="Exile Camp",
            status="completed",
        )
    )
    assert completed.status == "completed"
    assert completed.resume_section_key is None
