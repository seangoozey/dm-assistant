import os
from datetime import UTC, date, datetime
from uuid import uuid4

import psycopg
import pytest

from dm_assistant_core.adapters.postgres.database import PostgresDatabase
from dm_assistant_core.adapters.postgres.migrate import run_migrations
from dm_assistant_core.adapters.postgres.session_runs import PostgresSessionRunRepository
from dm_assistant_core.application.session_runs import (
    CloseSessionRunCommand,
    OpenSessionRunCommand,
    SaveSessionRunNoteCommand,
    SessionRunService,
    UpdateEncounterProgressCommand,
)

TEST_DSN = os.getenv("CAMPAIGN_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    TEST_DSN is None,
    reason="set CAMPAIGN_TEST_DATABASE_URL to a disposable PostgreSQL database",
)


@pytest.fixture(autouse=True)
def disposable_database() -> None:
    if TEST_DSN is None:
        return
    database_name = psycopg.conninfo.conninfo_to_dict(TEST_DSN).get("dbname", "")
    if not database_name.endswith("_test"):
        raise RuntimeError("integration tests require a database name ending in _test")
    run_migrations(TEST_DSN)
    with psycopg.connect(TEST_DSN) as connection:
        connection.execute(
            "TRUNCATE TABLE campaign_encounter_progress, campaign_session_runs CASCADE"
        )


def test_session_run_persists_general_notes_and_multiple_encounter_contexts() -> None:
    assert TEST_DSN is not None
    road_id, camp_id = uuid4(), uuid4()
    with psycopg.connect(TEST_DSN) as connection:
        connection.execute(
            "INSERT INTO source_documents "
            "(id,source_kind,connector,original_path,first_seen_at) VALUES "
            "(%s,'markdown','test','encounters/road.md',now()),"
            "(%s,'markdown','test','encounters/camp.md',now())",
            (road_id, camp_id),
        )
    service = SessionRunService(PostgresSessionRunRepository(PostgresDatabase(TEST_DSN)))
    run = service.open(OpenSessionRunCommand(session_date=date(2026, 8, 27), title="Mixed play"))
    commands = (
        SaveSessionRunNoteCommand(
            note_id=uuid4(), context_kind="general", text="The party traveled south.",
            captured_at=datetime(2026, 8, 27, 19, 0, tzinfo=UTC),
        ),
        SaveSessionRunNoteCommand(
            note_id=uuid4(), source_document_id=road_id,
            source_path="encounters/road.md", encounter_name="The Road",
            section_key="arrival", section_title="Arrival", text="Bandits attacked.",
            captured_at=datetime(2026, 8, 27, 19, 10, tzinfo=UTC),
        ),
        SaveSessionRunNoteCommand(
            note_id=uuid4(), source_document_id=camp_id,
            source_path="encounters/camp.md", encounter_name="Exile Camp",
            section_key="common-fire", section_title="The Common Fire",
            text="The party reached the camp.",
            captured_at=datetime(2026, 8, 27, 20, 0, tzinfo=UTC),
        ),
    )
    for command in commands:
        service.save_note(run.run_id, command)

    restored = service.get_open()
    assert restored is not None
    assert restored.notes[0].context_kind == "general"
    assert restored.notes[0].encounter_name is None
    assert [encounter.encounter_name for encounter in restored.encounters] == [
        "The Road", "Exile Camp"
    ]
    assert restored.encounters[-1].last_section_title == "The Common Fire"
    assert [item.status for item in service.list_encounter_progress()] == [
        "in_progress", "in_progress"
    ]

    checkpoint = service.update_encounter_progress(
        UpdateEncounterProgressCommand(
            source_document_id=camp_id,
            source_path="encounters/camp.md",
            encounter_name="Exile Camp",
            status="in_progress",
            resume_section_key="common-fire",
            resume_section_title="The Common Fire",
            session_run_id=run.run_id,
        )
    )
    assert checkpoint.resume_section_title == "The Common Fire"
    service.close(
        run.run_id,
        CloseSessionRunCommand(
            captured_source_document_id=uuid4(),
            capture_id=uuid4(),
        ),
    )
    persisted = {item.encounter_name: item for item in service.list_encounter_progress()}
    assert persisted["Exile Camp"].status == "in_progress"
    assert persisted["Exile Camp"].resume_section_title == "The Common Fire"

    next_run = service.open(
        OpenSessionRunCommand(session_date=date(2026, 9, 3), title="Resume camp")
    )
    service.update_encounter_progress(
        UpdateEncounterProgressCommand(
            source_document_id=camp_id,
            source_path="encounters/camp.md",
            encounter_name="Exile Camp",
            status="in_progress",
            resume_section_key="common-fire",
            resume_section_title="The Common Fire",
            session_run_id=next_run.run_id,
        )
    )
    with psycopg.connect(TEST_DSN) as connection:
        count = connection.execute(
            "SELECT count(*) FROM campaign_session_run_encounters "
            "WHERE source_document_id = %s",
            (camp_id,),
        ).fetchone()[0]
    assert count == 2
