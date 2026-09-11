# ruff: noqa: E501
import os
from hashlib import sha256
from uuid import UUID, uuid4

import psycopg
import pytest

from dm_assistant_core.adapters.postgres.claim_reconciliation import (
    PostgresClaimReconciliationRepository,
)
from dm_assistant_core.adapters.postgres.database import PostgresDatabase
from dm_assistant_core.adapters.postgres.migrate import run_migrations
from dm_assistant_core.application.claim_reconciliation import (
    ApplyClaimReconciliationCommand,
    ClaimReconciliationError,
    ClaimReplacementDraft,
    ReconciliationDecision,
    ReplaceClaimCommand,
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
            "TRUNCATE TABLE import_runs, source_documents, workflow_sessions, change_sets CASCADE"
        )


def seed_claim_pair() -> tuple[UUID, UUID]:
    assert TEST_DSN is not None
    workflow_id, change_set_id, entity_id = uuid4(), uuid4(), uuid4()
    newer_document_id, older_document_id = uuid4(), uuid4()
    newer_revision_id, older_revision_id = uuid4(), uuid4()
    newer_span_id, older_span_id = uuid4(), uuid4()
    newer_id, older_id = uuid4(), uuid4()
    raw = b"The hero may unite the nations."
    digest = sha256(raw).hexdigest()
    with psycopg.connect(TEST_DSN) as connection:
        connection.execute(
            "INSERT INTO workflow_sessions(id,kind,started_at) VALUES (%s,'lore_entry',now())",
            (workflow_id,),
        )
        connection.execute(
            "INSERT INTO change_sets(id,idempotency_key,workflow_session_id,status,requested_at,applied_at) "
            "VALUES (%s,%s,%s,'applied',now(),now())",
            (change_set_id, f"seed:{change_set_id}", workflow_id),
        )
        connection.execute(
            "INSERT INTO entities(id,entity_type,canonical_name,created_by_change_set_id,created_at,updated_at) "
            "VALUES (%s,'npc','Test Hero',%s,now(),now())",
            (entity_id, change_set_id),
        )
        connection.execute(
            "INSERT INTO source_documents(id,source_kind,connector,original_path,first_seen_at) "
            "VALUES (%s,'markdown','test','pcs/test-hero.md',now()),"
            "(%s,'markdown','test','sessions/test-hero-history.md',now())",
            (newer_document_id, older_document_id),
        )
        connection.execute(
            "INSERT INTO source_revisions(id,source_document_id,content_hash,raw_content,importer_version,captured_at) "
            "VALUES (%s,%s,%s,%s,'test',now()),(%s,%s,%s,%s,'test',now())",
            (
                newer_revision_id, newer_document_id, digest, raw,
                older_revision_id, older_document_id, digest, raw,
            ),
        )
        connection.execute(
            "INSERT INTO source_spans(id,source_revision_id,section_path,start_offset,end_offset,excerpt_hash) "
            "VALUES (%s,%s,'DM Plans / Current',0,%s,%s),"
            "(%s,%s,'DM Plans / Archive',0,%s,%s)",
            (
                newer_span_id, newer_revision_id, len(raw), digest,
                older_span_id, older_revision_id, len(raw), digest,
            ),
        )
        connection.execute(
            "INSERT INTO claims(id,subject_entity_id,assertion_text,state,authority,confidence,visibility," 
            "recorded_at,created_at,updated_at) VALUES "
            "(%s,%s,'The hero might unite all nations.','possible','brainstorm',1,'dm_only',now()-interval '1 day',now(),now()),"
            "(%s,%s,'The hero may unite the nations.','possible','brainstorm',1,'dm_only',now(),now(),now())",
            (older_id, entity_id, newer_id, entity_id),
        )
        connection.execute(
            "INSERT INTO claim_evidence(claim_id,source_span_id,evidence_role) VALUES "
            "(%s,%s,'support'),(%s,%s,'support')",
            (older_id, older_span_id, newer_id, newer_span_id),
        )
    return newer_id, older_id


def repository() -> PostgresClaimReconciliationRepository:
    assert TEST_DSN is not None
    return PostgresClaimReconciliationRepository(PostgresDatabase(TEST_DSN))


def test_stale_snapshot_is_rejected() -> None:
    newer_id, older_id = seed_claim_pair()
    review = repository().review(newer_id, older_id)
    command = ApplyClaimReconciliationCommand(
        superseding_claim_id=newer_id,
        superseded_claim_id=older_id,
        superseding_snapshot_hash="0" * 64,
        superseded_snapshot_hash=review.superseded.snapshot_hash,
        decision=ReconciliationDecision.SUPERSEDE,
        reason="Reviewed replacement",
        idempotency_key="reconcile:stale",
    )
    with pytest.raises(ClaimReconciliationError, match="stale"):
        repository().apply(command)


def test_reconciliation_replay_returns_the_original_receipt() -> None:
    newer_id, older_id = seed_claim_pair()
    review = repository().review(newer_id, older_id)
    command = ApplyClaimReconciliationCommand(
        superseding_claim_id=newer_id,
        superseded_claim_id=older_id,
        superseding_snapshot_hash=review.superseding.snapshot_hash,
        superseded_snapshot_hash=review.superseded.snapshot_hash,
        decision=ReconciliationDecision.DUPLICATE,
        reason="Exact reviewed duplicate",
        idempotency_key="reconcile:replay",
    )
    first = repository().apply(command)
    replay = repository().apply(command)

    with psycopg.connect(TEST_DSN) as connection:
        evidence = connection.execute(
            "SELECT sd.original_path FROM claim_evidence ce "
            "JOIN source_spans ss ON ss.id=ce.source_span_id "
            "JOIN source_revisions sr ON sr.id=ss.source_revision_id "
            "JOIN source_documents sd ON sd.id=sr.source_document_id "
            "WHERE ce.claim_id=%s ORDER BY ss.section_path",
            (newer_id,),
        ).fetchall()
        supersession = connection.execute(
            "SELECT superseding_claim_id FROM claim_supersessions WHERE superseded_claim_id=%s",
            (older_id,),
        ).fetchone()

    assert replay.idempotent_replay is True
    assert replay.receipt_id == first.receipt_id
    assert replay.change_set_id == first.change_set_id
    assert {row[0] for row in evidence} == {
        "pcs/test-hero.md", "sessions/test-hero-history.md"
    }
    assert supersession == (newer_id,)


def test_claim_can_be_split_with_dimensions_and_provenance_preserved() -> None:
    newer_id, _ = seed_claim_pair()
    snapshot = repository().get(newer_id)
    command = ReplaceClaimCommand(
        claim_id=newer_id,
        snapshot_hash=snapshot.snapshot_hash,
        replacements=(
            ClaimReplacementDraft(
                assertion_text="The hero prepared a coalition.",
                state="prepared",
                authority="preparation",
                visibility="dm_only",
            ),
            ClaimReplacementDraft(
                assertion_text="The hero formed the coalition.",
                state="observed",
                authority="real_play",
                visibility="party",
                observed={"year": 2026, "month": 4, "day": 25},
            ),
        ),
        reason="Separate preparation from the observed outcome.",
        idempotency_key="replace:split",
    )

    first = repository().replace(command)
    replay = repository().replace(command)

    with psycopg.connect(TEST_DSN) as connection:
        replacements = connection.execute(
            "SELECT id,state::text,authority::text,visibility,observed_year "
            "FROM claims WHERE id=ANY(%s) ORDER BY state",
            (list(first.replacement_claim_ids),),
        ).fetchall()
        evidence_counts = connection.execute(
            "SELECT claim_id,count(*) FROM claim_evidence WHERE claim_id=ANY(%s) "
            "GROUP BY claim_id",
            (list(first.replacement_claim_ids),),
        ).fetchall()
        supersession_count = connection.execute(
            "SELECT count(*) FROM claim_supersessions WHERE superseded_claim_id=%s",
            (newer_id,),
        ).fetchone()

    assert replacements == [
        (first.replacement_claim_ids[1], "observed", "real_play", "party", 2026),
        (first.replacement_claim_ids[0], "prepared", "preparation", "dm_only", None),
    ]
    assert {row[0]: row[1] for row in evidence_counts} == {
        replacement_id: 1 for replacement_id in first.replacement_claim_ids
    }
    assert supersession_count == (2,)
    assert replay.idempotent_replay is True
    assert replay.receipt_id == first.receipt_id
