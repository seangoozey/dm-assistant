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


def test_campaign_clock_set_and_history_through_api():
    import os
    import pytest

    dsn = os.getenv("CAMPAIGN_TEST_DATABASE_URL")
    if not dsn:
        pytest.skip("integration test requires CAMPAIGN_TEST_DATABASE_URL")
    from dm_assistant_core.api.app import create_app
    from dm_assistant_core.config import Settings
    import asyncio

    import httpx

    from dm_assistant_core.adapters.postgres.migrate import run_migrations

    run_migrations(dsn)
    app = create_app(Settings(database_url=dsn, run_migrations=False))

    async def run() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            set_response = await client.put("/campaign/current-date?requester_role=dm", json={
                "calendar_id": "gregorian-ce", "year": 505, "month": 11, "day": 27,
                "reason": "TKT-0117 test"})
            assert set_response.status_code == 200
            assert set_response.json()["year"] == 505

            current = (await client.get("/campaign/current-date")).json()
            assert (current["year"], current["month"], current["day"]) == (505, 11, 27)

            history = (await client.get("/campaign/current-date/history?limit=3")).json()
            assert history[0]["year"] == 505 and history[0]["reason"] == "TKT-0117 test"

            forbidden = await client.put("/campaign/current-date?requester_role=party", json={
                "calendar_id": "gregorian-ce", "year": 506, "month": 1, "day": 1})
            assert forbidden.status_code == 403

    asyncio.run(run())


def test_session_dating_walk_and_inheritance():
    import os
    import pytest

    dsn = os.getenv("CAMPAIGN_TEST_DATABASE_URL")
    if not dsn:
        pytest.skip("integration test requires CAMPAIGN_TEST_DATABASE_URL")
    from dm_assistant_core.adapters.postgres.database import PostgresDatabase
    from dm_assistant_core.adapters.postgres.migrate import run_migrations
    from dm_assistant_core.adapters.postgres.session_dating import PostgresSessionDatingRepository
    from uuid import uuid4
    from hashlib import sha256

    run_migrations(dsn)
    repo = PostgresSessionDatingRepository(PostgresDatabase(dsn))

    import psycopg
    doc_id, rev_id, span_id, claim_id, workflow_id, change_set_id = (uuid4() for _ in range(6))
    text = "The council met under a rainless sky."
    with psycopg.connect(dsn) as connection:
        connection.execute(
            "INSERT INTO source_documents (id, source_kind, connector, original_path, first_seen_at) "
            "VALUES (%s, 'markdown', 'markdown', 'sessions/notes/2024 05 11.md', now())", (doc_id,))
        connection.execute(
            "INSERT INTO source_revisions (id, source_document_id, content_hash, raw_content, "
            "importer_version, captured_at, frontmatter_json) VALUES (%s, %s, %s, %s, 'test', now(), %s::jsonb)",
            (rev_id, doc_id, sha256(text.encode()).hexdigest(), text.encode(),
             '{"name": "2024 05 11"}'))
        connection.execute(
            "INSERT INTO source_document_paths (source_document_id, connector, normalized_path, "
            "first_seen_at, last_seen_at, is_current) VALUES (%s, 'markdown', %s, now(), now(), true)",
            (doc_id, "sessions/notes/2024 05 11.md"))
        connection.execute(
            "INSERT INTO workflow_sessions (id, kind, started_at) VALUES (%s, 'lore_entry', now())", (workflow_id,))
        connection.execute(
            "INSERT INTO change_sets (id, idempotency_key, workflow_session_id, status, requested_at, applied_at) "
            "VALUES (%s, %s, %s, 'applied', now(), now())", (change_set_id, f"seed:{change_set_id}", workflow_id))
        entity_id = uuid4()
        connection.execute(
            "INSERT INTO entities (id, entity_type, canonical_name, created_by_change_set_id, created_at, updated_at) "
            "VALUES (%s, 'npc', 'Sable', %s, now(), now())", (entity_id, change_set_id))
        connection.execute(
            "INSERT INTO claims (id, subject_entity_id, assertion_text, state, authority, confidence, visibility, "
            "recorded_at, created_at, updated_at) VALUES (%s, %s, %s, 'established', 'explicit_lore', 1.0, "
            "'dm_only', now(), now(), now())", (claim_id, entity_id, text))
        connection.execute(
            "INSERT INTO source_spans (id, source_revision_id, start_offset, end_offset, excerpt_hash) "
            "VALUES (%s, %s, 0, %s, %s)", (span_id, rev_id, len(text), sha256(text.encode()).hexdigest()))
        connection.execute(
            "INSERT INTO claim_evidence (claim_id, source_span_id, evidence_role) VALUES (%s, %s, 'support')",
            (claim_id, span_id))

    # Walk lists the note undated with its waiting claim.
    walk = repo.walk()
    entry = next(item for item in walk if item.document_id == str(doc_id))
    assert entry.undated_claims == 1 and entry.year is None and entry.dated_by is None

    # Setting the date stamps the claim through provenance, idempotently.
    result = repo.set_date(doc_id, 504, 3, 2, "reconstructed")
    assert result["claims_stamped"] == 1
    result_again = repo.set_date(doc_id, 504, 3, 3, "corrected")
    assert result_again["claims_stamped"] == 0  # already dated: never overwritten

    import psycopg as psycopg2
    with psycopg2.connect(dsn) as connection:
        stamped = connection.execute(
            "SELECT effective_from_year, effective_from_month, effective_from_day FROM claims WHERE id = %s",
            (claim_id,)).fetchone()
    assert stamped == (504, 3, 2)  # first stamp survives the correction

    walk = repo.walk()
    entry = next(item for item in walk if item.document_id == str(doc_id))
    assert entry.year == 504 and entry.dated_by == "dm"

    # Residue: the claim is now dated, so it leaves the undaged queue.
    assert all(item.claim_id != str(claim_id) for item in repo.undated_claims())
    bulk = repo.inherit()
    assert bulk["overlay_dated_documents"] >= 1


def test_conflict_review_queue_and_decisions():
    import os
    import pytest

    dsn = os.getenv("CAMPAIGN_TEST_DATABASE_URL")
    if not dsn:
        pytest.skip("integration test requires CAMPAIGN_TEST_DATABASE_URL")
    from uuid import uuid4
    from hashlib import sha256
    from dm_assistant_core.adapters.postgres.conflict_review import PostgresConflictReviewRepository
    from dm_assistant_core.adapters.postgres.database import PostgresDatabase
    from dm_assistant_core.adapters.postgres.migrate import run_migrations
    import psycopg

    run_migrations(dsn)
    repo = PostgresConflictReviewRepository(PostgresDatabase(dsn))

    entity, workflow, change_set = uuid4(), uuid4(), uuid4()
    death_claim, later_claim, span, rev, doc = uuid4(), uuid4(), uuid4(), uuid4(), uuid4()
    text = "camp log"
    with psycopg.connect(dsn) as connection:
        for statement, params in [
            ("INSERT INTO workflow_sessions (id, kind, started_at) VALUES (%s, 'lore_entry', now())", (workflow,)),
            ("INSERT INTO change_sets (id, idempotency_key, workflow_session_id, status, requested_at, applied_at) VALUES (%s, %s, %s, 'applied', now(), now())", (change_set, f"seed:{change_set}", workflow)),
            ("INSERT INTO entities (id, entity_type, canonical_name, created_by_change_set_id, created_at, updated_at) VALUES (%s, 'npc', 'Sable', %s, now(), now())", (entity, change_set)),
            ("INSERT INTO source_documents (id, source_kind, connector, original_path, first_seen_at) VALUES (%s, 'markdown', 'markdown', 'sessions/notes/x.md', now())", (doc,)),
            ("INSERT INTO source_document_paths (source_document_id, connector, normalized_path, first_seen_at, last_seen_at, is_current) VALUES (%s, 'markdown', 'sessions/notes/x.md', now(), now(), true)", (doc,)),
            ("INSERT INTO source_revisions (id, source_document_id, content_hash, raw_content, importer_version, captured_at) VALUES (%s, %s, %s, %s, 'test', now())", (rev, doc, sha256(text.encode()).hexdigest(), text.encode())),
            ("INSERT INTO source_spans (id, source_revision_id, start_offset, end_offset, excerpt_hash) VALUES (%s, %s, 0, %s, %s)", (span, rev, len(text), sha256(text.encode()).hexdigest())),
            ("INSERT INTO claims (id, subject_entity_id, assertion_text, state, authority, confidence, visibility, recorded_at, created_at, updated_at, effective_from_year, effective_from_month, effective_from_day, observed_year) VALUES (%s, NULL, %s, 'observed', 'real_play', 1.0, 'dm_only', now(), now(), now(), 505, 11, 5, 505)", (death_claim, "On 505-11-05, Sable died at the gates.")),
            ("INSERT INTO claim_evidence (claim_id, source_span_id, evidence_role) VALUES (%s, %s, 'support')", (death_claim, span)),
            ("INSERT INTO claim_related_entities (claim_id, entity_id, relation_kind) VALUES (%s, %s, 'derived_mention')", (death_claim, entity)),
            ("INSERT INTO claims (id, subject_entity_id, assertion_text, state, authority, confidence, visibility, recorded_at, created_at, updated_at, effective_from_year, effective_from_month, effective_from_day) VALUES (%s, %s, %s, 'established', 'explicit_lore', 1.0, 'dm_only', now(), now(), now(), 505, 11, 10)", (later_claim, entity, "Sable still runs the counter at the camp.")),
        ]:
            connection.execute(statement, params)

    # Detection: the pair surfaces with dates and authority.
    queue = repo.queue()
    pair = next(item for item in queue if item.claim_a_id == str(death_claim) and item.claim_b_id == str(later_claim))
    assert pair.entity_name == "Sable" and pair.claim_a_date == "505-11-05"
    assert pair.claim_b_date == "505-11-10" and pair.claim_b_authority == "explicit_lore"

    # Dismiss: reviewed, kept both; the pair leaves the queue.
    result = repo.decide(death_claim, later_claim, "dismiss", "past-tense recounting")
    assert result["idempotent_replay"] is False
    assert all(not (item.claim_a_id == str(death_claim) and item.claim_b_id == str(later_claim)) for item in repo.queue())
    replay = repo.decide(death_claim, later_claim, "dismiss", "again")
    assert replay["idempotent_replay"] is True

    # A second, genuinely operative pair retires through the audited path.
    operative = uuid4()
    with psycopg.connect(dsn) as connection:
        connection.execute(
            "INSERT INTO claims (id, subject_entity_id, assertion_text, state, authority, confidence, visibility, recorded_at, created_at, updated_at, effective_from_year, effective_from_month, effective_from_day) "
            "VALUES (%s, %s, 'Sable greets visitors at the gates today.', 'established', 'explicit_lore', 1.0, 'dm_only', now(), now(), now(), 505, 11, 12)", (operative, entity))
    pair2 = next(item for item in repo.queue() if item.claim_b_id == str(operative))
    result = repo.decide(death_claim, operative, "supersede", "contradicts observed death")
    assert result["change_set_id"]
    with psycopg.connect(dsn) as connection:
        superseded = connection.execute(
            "SELECT reason FROM claim_supersessions WHERE superseded_claim_id = %s", (operative,)).fetchone()
    assert superseded and "contradicts observed death" in superseded[0]
    assert all(item.claim_b_id != str(operative) for item in repo.queue())


def test_entity_description_filed_as_evidence_document():
    import os
    import pytest

    dsn = os.getenv("CAMPAIGN_TEST_DATABASE_URL")
    if not dsn:
        pytest.skip("integration test requires CAMPAIGN_TEST_DATABASE_URL")
    from uuid import uuid4
    from dm_assistant_core.adapters.postgres.database import PostgresDatabase
    from dm_assistant_core.adapters.postgres.migrate import run_migrations
    from dm_assistant_core.application.entity_descriptions import (
        EntityDescriptionCommand, EntityDescriptionService)
    import psycopg

    run_migrations(dsn)
    entity, workflow, change_set = uuid4(), uuid4(), uuid4()
    claim = uuid4()
    with psycopg.connect(dsn) as connection:
        connection.execute("INSERT INTO workflow_sessions (id, kind, started_at) VALUES (%s, 'lore_entry', now())", (workflow,))
        connection.execute("INSERT INTO change_sets (id, idempotency_key, workflow_session_id, status, requested_at, applied_at) VALUES (%s, %s, %s, 'applied', now(), now())", (change_set, f"seed:{change_set}", workflow))
        connection.execute("INSERT INTO entities (id, entity_type, canonical_name, created_by_change_set_id, created_at, updated_at) VALUES (%s, 'npc', 'Ruh', %s, now(), now())", (entity, change_set))

    from dm_assistant_core.application.imports import MarkdownImportService  # real ingest path
    from dm_assistant_core.adapters.postgres.imports import PostgresMarkdownImportRepository
    service = EntityDescriptionService(MarkdownImportService(PostgresMarkdownImportRepository(PostgresDatabase(dsn))),
                                       _NameLookup(PostgresDatabase(dsn), entity))
    receipt = service.write(EntityDescriptionCommand(
        entity_id=entity, text="Ruh is a quiet presence at the camp's edge.\n\n## Background\n\nKept watch after the fall.",
        referenced_claim_ids=(claim,), idempotency_key="desc-1"))
    assert receipt.path == "entities/ruh.md"

    with psycopg.connect(dsn) as connection:
        doc = connection.execute(
            "SELECT sd.connector, sdp.normalized_path, sr.frontmatter_json->>'entity_id', "
            "(sr.frontmatter_json->'referenced_claims')::text "
            "FROM source_documents sd JOIN source_document_paths sdp ON sdp.source_document_id = sd.id "
            "JOIN source_revisions sr ON sr.id = (SELECT id FROM source_revisions WHERE source_document_id = sd.id ORDER BY captured_at DESC LIMIT 1) "
            "WHERE sd.id = %s", (receipt.document_id,)).fetchone()
    assert "direct-input:entity-description" in doc[0]
    assert doc[1] == "entities/ruh.md"
    assert doc[2] == str(entity)
    assert str(claim) in doc[3]

    replay = service.write(EntityDescriptionCommand(
        entity_id=entity, text="again", idempotency_key="desc-1"))
    assert replay.idempotent_replay is True


class _NameLookup:
    def __init__(self, database, entity_id) -> None:
        self._database = database
        self._entity_id = entity_id

    def get(self, entity_id):
        with self._database.connection() as connection:
            row = connection.execute(
                "SELECT id, canonical_name FROM entities WHERE id = %s", (entity_id,)).fetchone()
        if row is None:
            return None
        return type("Entity", (), {"entity_id": row[0], "canonical_name": row[1]})()


def test_life_status_backfill_and_dead_seats():
    import os
    import pytest

    dsn = os.getenv("CAMPAIGN_TEST_DATABASE_URL")
    if not dsn:
        pytest.skip("integration test requires CAMPAIGN_TEST_DATABASE_URL")
    from uuid import uuid4
    from dm_assistant_core.adapters.postgres.database import PostgresDatabase
    from dm_assistant_core.adapters.postgres.entity_profiles import (
        PostgresEntityProfileRepository)
    from dm_assistant_core.adapters.postgres.life_status import PostgresLifeStatusRepository
    from dm_assistant_core.adapters.postgres.migrate import run_migrations
    from dm_assistant_core.application.entity_profiles import EntityProfileService
    import psycopg

    run_migrations(dsn)
    profiles = EntityProfileService(PostgresEntityProfileRepository(PostgresDatabase(dsn)))
    repo = PostgresLifeStatusRepository(PostgresDatabase(dsn), profiles)

    faction, member, claim = uuid4(), uuid4(), uuid4()
    workflow, change_set = uuid4(), uuid4()
    with psycopg.connect(dsn) as connection:
        for statement, params in [
            ("INSERT INTO workflow_sessions (id, kind, started_at) VALUES (%s, 'lore_entry', now())", (workflow,)),
            ("INSERT INTO change_sets (id, idempotency_key, workflow_session_id, status, requested_at, applied_at) VALUES (%s, %s, %s, 'applied', now(), now())", (change_set, f"seed:{change_set}", workflow)),
            ("INSERT INTO entities (id, entity_type, canonical_name, created_by_change_set_id, created_at, updated_at) VALUES (%s, 'faction', 'Dawn Wardens', %s, now(), now())", (faction, change_set)),
            ("INSERT INTO entities (id, entity_type, canonical_name, created_by_change_set_id, created_at, updated_at) VALUES (%s, 'npc', 'Sable', %s, now(), now())", (member, change_set)),
            ("INSERT INTO claims (id, subject_entity_id, assertion_text, state, authority, confidence, visibility, recorded_at, created_at, updated_at, effective_from_year, effective_from_month, effective_from_day, observed_year) VALUES (%s, NULL, 'On 505-11-05, Sable died at the gates.', 'observed', 'real_play', 1.0, 'dm_only', now(), now(), now(), 505, 11, 5, 505)", (claim,)),
            ("INSERT INTO claim_related_entities (claim_id, entity_id, relation_kind) VALUES (%s, %s, 'derived_mention')", (claim, member)),
        ]:
            connection.execute(statement, params)

    # Seed a profile for the member so the proposal has a row to update.
    from dm_assistant_core.application.entity_profiles import UpdateEntityProfileCommand
    from dm_assistant_core.domain.retrieval import RequesterVisibility
    dm = RequesterVisibility.model_validate({"role": "dm"})
    profiles.update(UpdateEntityProfileCommand(
        entity_id=member, version=0, canonical_name="Sable",
        status=None, location_type=None, parent_location=None, base_location=None,
        player=None, race=None, sex=None, aliases=(), summary="",
        life_status=None, life_status_since=None, life_status_claim_id=None,
        idempotency_key="seed-profile-sable"), dm)

    # The backfill proposes dead from the observed claim.
    proposals = repo.proposals()
    proposal = next(item for item in proposals if item.entity_id == str(member))
    assert proposal.death_date == "505-11-05"
    assert proposal.death_claim_id == str(claim)

    # Confirming writes the audited profile update.
    receipt = repo.apply(member, "dead", 505, 11, 5, claim, "life-sable-1")
    assert receipt.version >= 1  # seeded profile was version 1; the status write bumps it
    stored = profiles.get(member, dm)
    assert stored.life_status == "dead"
    assert stored.life_status_since is not None
    assert str(stored.life_status_claim_id) == str(claim)

    # A current roster seat held by the dead member surfaces as a dead seat.
    with psycopg.connect(dsn) as connection:
        connection.execute(
            "INSERT INTO membership_records (id, faction_id, member_id, role_title) "
            "VALUES (gen_random_uuid(), %s, %s, NULL)", (faction, member))
    seats = repo.dead_seats()
    seat = next(item for item in seats if item.member_id == str(member))
    assert seat.faction_name == "Dawn Wardens" and seat.life_status_since == "505-11-05"

    # The proposal queue no longer lists the confirmed entity.
    assert all(item.entity_id != str(member) for item in repo.proposals())


def test_entity_description_revision_same_document():
    import os
    import pytest

    dsn = os.getenv("CAMPAIGN_TEST_DATABASE_URL")
    if not dsn:
        pytest.skip("integration test requires CAMPAIGN_TEST_DATABASE_URL")
    from uuid import uuid4
    from dm_assistant_core.adapters.postgres.database import PostgresDatabase
    from dm_assistant_core.adapters.postgres.migrate import run_migrations
    from dm_assistant_core.application.entity_descriptions import (
        EntityDescriptionCommand, EntityDescriptionService)
    from dm_assistant_core.application.imports import MarkdownImportService
    from dm_assistant_core.adapters.postgres.imports import PostgresMarkdownImportRepository
    import psycopg

    run_migrations(dsn)
    entity, workflow, change_set = uuid4(), uuid4(), uuid4()
    with psycopg.connect(dsn) as connection:
        connection.execute("INSERT INTO workflow_sessions (id, kind, started_at) VALUES (%s, 'lore_entry', now())", (workflow,))
        connection.execute("INSERT INTO change_sets (id, idempotency_key, workflow_session_id, status, requested_at, applied_at) VALUES (%s, %s, %s, 'applied', now(), now())", (change_set, f"seed:{change_set}", workflow))
        connection.execute("INSERT INTO entities (id, entity_type, canonical_name, created_by_change_set_id, created_at, updated_at) VALUES (%s, 'npc', 'Vess', %s, now(), now())", (entity, change_set))

    service = EntityDescriptionService(
        MarkdownImportService(PostgresMarkdownImportRepository(PostgresDatabase(dsn))),
        _NameLookupSingle(PostgresDatabase(dsn), entity))
    first = service.write(EntityDescriptionCommand(
        entity_id=entity, text="First prose.", idempotency_key="desc-vess-1"))
    second = service.write(EntityDescriptionCommand(
        entity_id=entity, text="Second prose, revised.", document_id=first.document_id,
        idempotency_key="desc-vess-2"))
    assert second.document_id == first.document_id
    assert second.path == first.path == "entities/vess.md"
    with psycopg.connect(dsn) as connection:
        revisions = connection.execute(
            "SELECT count(*) FROM source_revisions WHERE source_document_id = %s",
            (first.document_id,)).fetchone()[0]
    assert revisions == 2
    # A revision naming a document that is not this entity's page path is
    # rejected before ingest — it would fork the page rather than revise it.
    with pytest.raises(ValueError, match="no longer this entity's page path"):
        service.write(EntityDescriptionCommand(
            entity_id=entity, text="Third prose.", document_id=uuid4(),
            idempotency_key="desc-vess-3"))
    with psycopg.connect(dsn) as connection:
        revisions = connection.execute(
            "SELECT count(*) FROM source_revisions WHERE source_document_id = %s",
            (first.document_id,)).fetchone()[0]
    assert revisions == 2


class _NameLookupSingle:
    def __init__(self, database, entity_id) -> None:
        self._database = database
        self._entity_id = entity_id

    def get(self, entity_id):
        with self._database.connection() as connection:
            row = connection.execute(
                "SELECT id, canonical_name FROM entities WHERE id = %s", (entity_id,)).fetchone()
        if row is None:
            return None
        return type("Entity", (), {"entity_id": row[0], "canonical_name": row[1]})()
