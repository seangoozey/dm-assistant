"""PostgreSQL persistence for the live session workspace."""

from typing import Any
from uuid import UUID

from psycopg import Connection

from dm_assistant_core.adapters.postgres.database import PostgresDatabase
from dm_assistant_core.application.session_runs import (
    CloseSessionRunCommand,
    EncounterProgress,
    OpenSessionRunCommand,
    SaveSessionRunNoteCommand,
    SessionRun,
    SessionRunNote,
    UpdateEncounterProgressCommand,
    summarize_session_encounters,
)
from dm_assistant_core.domain.chronology import CampaignDate


class PostgresSessionRunRepository:
    def __init__(self, database: PostgresDatabase) -> None:
        self._database = database

    @staticmethod
    def _note(row: tuple[Any, ...]) -> SessionRunNote:
        return SessionRunNote(
            note_id=row[0], run_id=row[1], source_document_id=row[2], source_path=row[3],
            context_kind=row[4], encounter_name=row[5], section_key=row[6],
            section_title=row[7], text=row[8], captured_at=row[9], updated_at=row[10],
        )

    @staticmethod
    def _progress(row: tuple[Any, ...]) -> EncounterProgress:
        return EncounterProgress(
            source_document_id=row[0], source_path=row[1], encounter_name=row[2],
            status=row[3], resume_section_key=row[4], resume_section_title=row[5],
            last_session_run_id=row[6], updated_at=row[7],
        )

    def _run(self, connection: Connection[Any], row: tuple[Any, ...]) -> SessionRun:
        note_rows = connection.execute(
            "SELECT note_id,run_id,source_document_id,source_path,context_kind,encounter_name,"
            "section_key,section_title,note_text,captured_at,updated_at "
            "FROM campaign_session_run_notes "
            "WHERE run_id=%s ORDER BY captured_at,note_id",
            (row[0],),
        ).fetchall()
        in_game_date = None if row[3] is None else CampaignDate(
            calendar_id=row[3], year=row[4], month=row[5], day=row[6]
        )
        notes = tuple(self._note(note) for note in note_rows)
        return SessionRun(
            run_id=row[0], status=row[1], session_date=row[2], in_game_date=in_game_date,
            title=row[7], captured_source_document_id=row[8], capture_id=row[9],
            created_at=row[10], updated_at=row[11], closed_at=row[12],
            notes=notes, encounters=summarize_session_encounters(notes),
        )

    def get_open(self) -> SessionRun | None:
        with self._database.connection() as connection:
            row = connection.execute(
                "SELECT run_id,status,session_date,calendar_id,campaign_year,campaign_month,"
                "campaign_day,title,captured_source_document_id,capture_id,created_at,"
                "updated_at,closed_at "
                "FROM campaign_session_runs WHERE status='open'"
            ).fetchone()
            return None if row is None else self._run(connection, row)

    def open(self, command: OpenSessionRunCommand) -> SessionRun:
        campaign_date = command.in_game_date
        with self._database.connection() as connection:
            row = connection.execute(
                "INSERT INTO campaign_session_runs "
                "(session_date,calendar_id,campaign_year,campaign_month,campaign_day,title) "
                "VALUES (%s,%s,%s,%s,%s,%s) RETURNING "
                "run_id,status,session_date,calendar_id,campaign_year,campaign_month,campaign_day,"
                "title,captured_source_document_id,capture_id,created_at,updated_at,closed_at",
                (
                    command.session_date,
                    campaign_date.calendar_id if campaign_date else None,
                    campaign_date.year if campaign_date else None,
                    campaign_date.month if campaign_date else None,
                    campaign_date.day if campaign_date else None,
                    command.title,
                ),
            ).fetchone()
            assert row is not None
            return self._run(connection, row)

    def save_note(self, run_id: UUID, command: SaveSessionRunNoteCommand) -> SessionRunNote:
        with self._database.connection() as connection:
            row = connection.execute(
                "INSERT INTO campaign_session_run_notes "
                "(note_id,run_id,source_document_id,source_path,context_kind,encounter_name,"
                "section_key,section_title,note_text,captured_at) "
                "SELECT %s,%s,%s,%s,%s,%s,%s,%s,%s,%s WHERE EXISTS "
                "(SELECT 1 FROM campaign_session_runs WHERE run_id=%s AND status='open') "
                "ON CONFLICT (note_id) DO UPDATE SET "
                "source_document_id=excluded.source_document_id,context_kind=excluded.context_kind,"
                "source_path=excluded.source_path,encounter_name=excluded.encounter_name,"
                "section_key=excluded.section_key,section_title=excluded.section_title,"
                "note_text=excluded.note_text,captured_at=excluded.captured_at,updated_at=now() "
                "WHERE campaign_session_run_notes.run_id=excluded.run_id RETURNING "
                "note_id,run_id,source_document_id,source_path,context_kind,encounter_name,"
                "section_key,section_title,note_text,captured_at,updated_at",
                (
                    command.note_id, run_id, command.source_document_id, command.source_path,
                    command.context_kind, command.encounter_name, command.section_key,
                    command.section_title,
                    command.text, command.captured_at, run_id,
                ),
            ).fetchone()
            if row is None:
                raise ValueError("open session run not found")
            connection.execute(
                "UPDATE campaign_session_runs SET updated_at=now() WHERE run_id=%s",
                (run_id,),
            )
            if command.context_kind == "encounter" and command.source_document_id is not None:
                connection.execute(
                    "INSERT INTO campaign_session_run_encounters "
                    "(run_id,source_document_id,source_path,encounter_name,first_activity_at,"
                    "last_activity_at,last_section_key,last_section_title) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s) "
                    "ON CONFLICT (run_id,source_document_id) DO UPDATE SET "
                    "last_activity_at=greatest(campaign_session_run_encounters.last_activity_at,"
                    "excluded.last_activity_at),last_section_key=excluded.last_section_key,"
                    "last_section_title=excluded.last_section_title",
                    (
                        run_id, command.source_document_id, command.source_path,
                        command.encounter_name, command.captured_at, command.captured_at,
                        command.section_key, command.section_title,
                    ),
                )
                connection.execute(
                    "INSERT INTO campaign_encounter_progress "
                    "(source_document_id,source_path,encounter_name,status,last_session_run_id) "
                    "VALUES (%s,%s,%s,'in_progress',%s) "
                    "ON CONFLICT (source_document_id) DO UPDATE SET "
                    "source_path=excluded.source_path,encounter_name=excluded.encounter_name,"
                    "last_session_run_id=excluded.last_session_run_id,updated_at=now(),"
                    "status=CASE WHEN campaign_encounter_progress.status IN "
                    "('completed','abandoned') THEN campaign_encounter_progress.status "
                    "ELSE 'in_progress' END",
                    (
                        command.source_document_id, command.source_path,
                        command.encounter_name, run_id,
                    ),
                )
            return self._note(row)

    def delete_note(self, run_id: UUID, note_id: UUID) -> bool:
        with self._database.connection() as connection:
            row = connection.execute(
                "DELETE FROM campaign_session_run_notes USING campaign_session_runs "
                "WHERE campaign_session_run_notes.note_id=%s "
                "AND campaign_session_run_notes.run_id=%s "
                "AND campaign_session_runs.run_id=%s AND campaign_session_runs.status='open' "
                "RETURNING campaign_session_run_notes.note_id",
                (note_id, run_id, run_id),
            ).fetchone()
            if row is not None:
                connection.execute(
                    "UPDATE campaign_session_runs SET updated_at=now() WHERE run_id=%s",
                    (run_id,),
                )
            return row is not None

    def close(self, run_id: UUID, command: CloseSessionRunCommand) -> SessionRun:
        with self._database.connection() as connection:
            row = connection.execute(
                "UPDATE campaign_session_runs SET status='closed',captured_source_document_id=%s,"
                "capture_id=%s,closed_at=now(),updated_at=now() WHERE run_id=%s AND status='open' "
                "RETURNING run_id,status,session_date,calendar_id,campaign_year,campaign_month,"
                "campaign_day,title,captured_source_document_id,capture_id,created_at,updated_at,closed_at",
                (command.captured_source_document_id, command.capture_id, run_id),
            ).fetchone()
            if row is None:
                raise ValueError("open session run not found")
            return self._run(connection, row)

    def list_encounter_progress(self) -> tuple[EncounterProgress, ...]:
        with self._database.connection() as connection:
            rows = connection.execute(
                "SELECT source_document_id,source_path,encounter_name,status,"
                "resume_section_key,resume_section_title,last_session_run_id,updated_at "
                "FROM campaign_encounter_progress ORDER BY updated_at DESC,encounter_name"
            ).fetchall()
            return tuple(self._progress(row) for row in rows)

    def update_encounter_progress(
        self, command: UpdateEncounterProgressCommand
    ) -> EncounterProgress:
        with self._database.connection() as connection:
            row = connection.execute(
                "INSERT INTO campaign_encounter_progress "
                "(source_document_id,source_path,encounter_name,status,resume_section_key,"
                "resume_section_title,last_session_run_id) VALUES (%s,%s,%s,%s,%s,%s,%s) "
                "ON CONFLICT (source_document_id) DO UPDATE SET "
                "source_path=excluded.source_path,encounter_name=excluded.encounter_name,"
                "status=excluded.status,resume_section_key=excluded.resume_section_key,"
                "resume_section_title=excluded.resume_section_title,"
                "last_session_run_id=coalesce(excluded.last_session_run_id,"
                "campaign_encounter_progress.last_session_run_id),updated_at=now() "
                "RETURNING source_document_id,source_path,encounter_name,status,"
                "resume_section_key,resume_section_title,last_session_run_id,updated_at",
                (
                    command.source_document_id, command.source_path, command.encounter_name,
                    command.status, command.resume_section_key, command.resume_section_title,
                    command.session_run_id,
                ),
            ).fetchone()
            assert row is not None
            if command.session_run_id is not None:
                connection.execute(
                    "INSERT INTO campaign_session_run_encounters "
                    "(run_id,source_document_id,source_path,encounter_name,last_section_key,"
                    "last_section_title) VALUES (%s,%s,%s,%s,%s,%s) "
                    "ON CONFLICT (run_id,source_document_id) DO UPDATE SET "
                    "last_activity_at=now(),last_section_key=excluded.last_section_key,"
                    "last_section_title=excluded.last_section_title",
                    (
                        command.session_run_id, command.source_document_id,
                        command.source_path, command.encounter_name,
                        command.resume_section_key, command.resume_section_title,
                    ),
                )
            return self._progress(row)
