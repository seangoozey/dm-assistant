"""Durable mutable workspace for one live play session."""

from datetime import UTC, date, datetime
from typing import Literal, Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from dm_assistant_core.domain.chronology import CampaignDate


class SessionRunNote(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    note_id: UUID
    run_id: UUID
    source_document_id: UUID | None = None
    source_path: str
    context_kind: Literal["general", "encounter"] = "encounter"
    encounter_name: str | None = None
    section_key: str | None = None
    section_title: str | None = None
    text: str
    captured_at: datetime
    updated_at: datetime


class SessionRunEncounter(BaseModel):
    """Operational encounter context touched during one session, never proof of occurrence."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    source_document_id: UUID | None = None
    source_path: str
    encounter_name: str
    first_activity_at: datetime
    last_activity_at: datetime
    last_section_key: str | None = None
    last_section_title: str | None = None
    note_count: int = Field(ge=1)


EncounterLifecycle = Literal["not_started", "in_progress", "completed", "abandoned"]


class EncounterProgress(BaseModel):
    """Mutable table-running state; never canonical evidence of an encounter outcome."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    source_document_id: UUID
    source_path: str
    encounter_name: str
    status: EncounterLifecycle
    resume_section_key: str | None = None
    resume_section_title: str | None = None
    last_session_run_id: UUID | None = None
    updated_at: datetime


class UpdateEncounterProgressCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    source_document_id: UUID
    source_path: str = Field(min_length=1)
    encounter_name: str = Field(min_length=1)
    status: EncounterLifecycle
    resume_section_key: str | None = None
    resume_section_title: str | None = None
    session_run_id: UUID | None = None


def summarize_session_encounters(
    notes: tuple[SessionRunNote, ...],
) -> tuple[SessionRunEncounter, ...]:
    grouped: dict[tuple[UUID | None, str, str], list[SessionRunNote]] = {}
    for note in notes:
        if note.context_kind != "encounter" or not note.encounter_name:
            continue
        key = (note.source_document_id, note.source_path, note.encounter_name)
        grouped.setdefault(key, []).append(note)
    summaries: list[SessionRunEncounter] = []
    for (document_id, source_path, encounter_name), encounter_notes in grouped.items():
        ordered = sorted(encounter_notes, key=lambda note: (note.captured_at, str(note.note_id)))
        last = ordered[-1]
        summaries.append(
            SessionRunEncounter(
                source_document_id=document_id,
                source_path=source_path,
                encounter_name=encounter_name,
                first_activity_at=ordered[0].captured_at,
                last_activity_at=last.captured_at,
                last_section_key=last.section_key,
                last_section_title=last.section_title,
                note_count=len(ordered),
            )
        )
    return tuple(sorted(summaries, key=lambda item: (item.first_activity_at, item.encounter_name)))


class SessionRun(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    run_id: UUID
    status: str
    session_date: date
    in_game_date: CampaignDate | None = None
    title: str
    captured_source_document_id: UUID | None = None
    capture_id: UUID | None = None
    created_at: datetime
    updated_at: datetime
    closed_at: datetime | None = None
    notes: tuple[SessionRunNote, ...] = ()
    encounters: tuple[SessionRunEncounter, ...] = ()


class OpenSessionRunCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    session_date: date
    in_game_date: CampaignDate | None = None
    title: str = Field(min_length=1)


class SaveSessionRunNoteCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    note_id: UUID
    source_document_id: UUID | None = None
    source_path: str = ""
    context_kind: Literal["general", "encounter"] = "encounter"
    encounter_name: str | None = None
    section_key: str | None = None
    section_title: str | None = None
    text: str = Field(min_length=1)
    captured_at: datetime


class CloseSessionRunCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    captured_source_document_id: UUID
    capture_id: UUID


class SessionRunRepository(Protocol):
    def get_open(self) -> SessionRun | None: ...
    def open(self, command: OpenSessionRunCommand) -> SessionRun: ...
    def save_note(self, run_id: UUID, command: SaveSessionRunNoteCommand) -> SessionRunNote: ...
    def delete_note(self, run_id: UUID, note_id: UUID) -> bool: ...
    def close(self, run_id: UUID, command: CloseSessionRunCommand) -> SessionRun: ...
    def list_encounter_progress(self) -> tuple[EncounterProgress, ...]: ...
    def update_encounter_progress(
        self, command: UpdateEncounterProgressCommand
    ) -> EncounterProgress: ...


class SessionRunService:
    def __init__(self, repository: SessionRunRepository) -> None:
        self._repository = repository

    def get_open(self) -> SessionRun | None:
        return self._repository.get_open()

    def open(self, command: OpenSessionRunCommand) -> SessionRun:
        existing = self._repository.get_open()
        if existing is not None:
            return existing
        if command.in_game_date is not None and not command.in_game_date.is_complete():
            raise ValueError("an open session requires a complete in-game date when supplied")
        return self._repository.open(command.model_copy(update={"title": command.title.strip()}))

    def save_note(self, run_id: UUID, command: SaveSessionRunNoteCommand) -> SessionRunNote:
        if not command.text.strip():
            raise ValueError("table notes cannot be empty")
        if command.context_kind == "encounter" and not all(
            value and value.strip()
            for value in (command.encounter_name, command.section_key, command.section_title)
        ):
            raise ValueError("encounter notes require encounter and section context")
        captured_at = command.captured_at
        if captured_at.tzinfo is None:
            captured_at = captured_at.replace(tzinfo=UTC)
        return self._repository.save_note(
            run_id,
            command.model_copy(
                update={
                    "text": command.text.strip(),
                    "encounter_name": (
                        command.encounter_name.strip() if command.encounter_name else None
                    ),
                    "section_key": command.section_key.strip() if command.section_key else None,
                    "section_title": (
                        command.section_title.strip() if command.section_title else None
                    ),
                    "captured_at": captured_at,
                }
            ),
        )

    def delete_note(self, run_id: UUID, note_id: UUID) -> None:
        if not self._repository.delete_note(run_id, note_id):
            raise ValueError("open session note not found")

    def close(self, run_id: UUID, command: CloseSessionRunCommand) -> SessionRun:
        return self._repository.close(run_id, command)

    def list_encounter_progress(self) -> tuple[EncounterProgress, ...]:
        return self._repository.list_encounter_progress()

    def update_encounter_progress(
        self, command: UpdateEncounterProgressCommand
    ) -> EncounterProgress:
        section_key = command.resume_section_key.strip() if command.resume_section_key else None
        section_title = (
            command.resume_section_title.strip() if command.resume_section_title else None
        )
        if (section_key is None) != (section_title is None):
            raise ValueError("a resume checkpoint requires both section key and title")
        if command.status != "in_progress":
            section_key = None
            section_title = None
        return self._repository.update_encounter_progress(
            command.model_copy(
                update={
                    "source_path": command.source_path.strip(),
                    "encounter_name": command.encounter_name.strip(),
                    "resume_section_key": section_key,
                    "resume_section_title": section_title,
                }
            )
        )
