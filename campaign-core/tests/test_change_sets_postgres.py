from __future__ import annotations

import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from hashlib import sha256
from typing import Any
from uuid import UUID, uuid4

import httpx
import psycopg
import pytest
from psycopg.types.json import Jsonb

from dm_assistant_core.adapters.postgres import PostgresChangeSetRepository, PostgresDatabase
from dm_assistant_core.adapters.postgres.migrate import run_migrations
from dm_assistant_core.api.app import create_app
from dm_assistant_core.config import Settings
from dm_assistant_core.domain import ApplyChangeSetCommand, ChangeSetRejectedError
from tests.support.interaction_harness import load_interaction_fixture

TEST_DSN = os.getenv("CAMPAIGN_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    TEST_DSN is None,
    reason="set CAMPAIGN_TEST_DATABASE_URL to a disposable PostgreSQL database",
)


@dataclass(frozen=True)
class SeededChangeSet:
    workflow_id: UUID
    proposal_id: UUID
    version_id: UUID
    approval_id: UUID
    change_set_id: UUID
    item_ids: tuple[UUID, ...]
    target_ids: tuple[UUID, ...]
    content_hash: str
    version_number: int

    def command(self) -> ApplyChangeSetCommand:
        return ApplyChangeSetCommand(
            change_set_id=self.change_set_id,
            reviewed_version=self.version_number,
            approval_id=self.approval_id,
            content_hash=self.content_hash,
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
            "TRUNCATE TABLE import_runs, source_documents, workflow_sessions, "
            "change_sets CASCADE"
        )


def seed_change_set(
    *,
    item_count: int = 1,
    approved_indexes: tuple[int, ...] | None = None,
    mutation_kinds: tuple[str, ...] | None = None,
) -> SeededChangeSet:
    assert TEST_DSN is not None
    workflow_id = uuid4()
    proposal_id = uuid4()
    version_id = uuid4()
    approval_id = uuid4()
    change_set_id = uuid4()
    item_ids = tuple(uuid4() for _ in range(item_count))
    target_ids = tuple(uuid4() for _ in range(item_count))
    content_hash = sha256(f"proposal:{version_id}".encode()).hexdigest()
    approved = approved_indexes or tuple(range(item_count))
    kinds = mutation_kinds or tuple("create_entity" for _ in range(item_count))

    with psycopg.connect(TEST_DSN) as connection:
        connection.execute(
            "INSERT INTO workflow_sessions (id, kind, started_at) VALUES (%s, 'brainstorm', now())",
            (workflow_id,),
        )
        connection.execute(
            "INSERT INTO proposals (id, workflow_session_id, status, created_at) "
            "VALUES (%s, %s, 'pending', now())",
            (proposal_id, workflow_id),
        )
        connection.execute(
            "INSERT INTO proposal_versions "
            "(id, proposal_id, version_number, content_hash, created_at) "
            "VALUES (%s, %s, 1, %s, now())",
            (version_id, proposal_id, content_hash),
        )
        for index, (item_id, target_id, mutation_kind) in enumerate(
            zip(item_ids, target_ids, kinds, strict=True), start=1
        ):
            payload = {
                "id": str(target_id),
                "entity_type": "npc",
                "canonical_name": f"Sanitized NPC {index}",
            }
            connection.execute(
                "INSERT INTO proposal_items "
                "(id, proposal_version_id, sequence, mutation_kind, target_type, "
                "target_id, after_json) "
                "VALUES (%s, %s, %s, %s, 'entity', %s, %s)",
                (item_id, version_id, index, mutation_kind, target_id, Jsonb(payload)),
            )
        connection.execute(
            "INSERT INTO approvals (id, proposal_version_id, scope_json, approved_at) "
            "VALUES (%s, %s, %s, now())",
            (approval_id, version_id, Jsonb([str(item_ids[index]) for index in approved])),
        )
        connection.execute(
            "INSERT INTO change_sets "
            "(id, idempotency_key, workflow_session_id, proposal_version_id, status, requested_at) "
            "VALUES (%s, %s, %s, %s, 'pending', now())",
            (change_set_id, f"test:{change_set_id}", workflow_id, version_id),
        )
    return SeededChangeSet(
        workflow_id=workflow_id,
        proposal_id=proposal_id,
        version_id=version_id,
        approval_id=approval_id,
        change_set_id=change_set_id,
        item_ids=item_ids,
        target_ids=target_ids,
        content_hash=content_hash,
        version_number=1,
    )


def seed_direct_lore_claim(subject_entity_id: UUID) -> tuple[SeededChangeSet, UUID, UUID]:
    assert TEST_DSN is not None
    parent_workflow_id = uuid4()
    child_workflow_id = uuid4()
    proposal_id = uuid4()
    version_id = uuid4()
    item_id = uuid4()
    claim_id = uuid4()
    approval_id = uuid4()
    change_set_id = uuid4()
    document_id = uuid4()
    revision_id = uuid4()
    span_id = uuid4()
    content_hash = sha256(f"direct-lore:{version_id}".encode()).hexdigest()
    payload = {
        "id": str(claim_id),
        "subject_entity_id": str(subject_entity_id),
        "assertion_text": "Sanitized supplied history.",
        "state": "established",
        "authority": "explicit_lore",
        "confidence": "1",
        "visibility": "dm_only",
        "recorded_at": "2026-08-01T12:00:00Z",
        "session_id": str(child_workflow_id),
        "source_span_id": str(span_id),
        "evidence_role": "direct_input",
    }
    with psycopg.connect(TEST_DSN) as connection:
        connection.execute(
            "INSERT INTO workflow_sessions (id, kind, started_at) "
            "VALUES (%s, 'brainstorm', now())",
            (parent_workflow_id,),
        )
        connection.execute(
            "INSERT INTO workflow_sessions (id, kind, started_at, parent_session_id) "
            "VALUES (%s, 'lore_entry', now(), %s)",
            (child_workflow_id, parent_workflow_id),
        )
        connection.execute(
            "INSERT INTO source_documents "
            "(id, source_kind, connector, original_path, first_seen_at) "
            "VALUES (%s, 'direct_input', 'test', %s, now())",
            (document_id, f"sanitized/{document_id}.md"),
        )
        connection.execute(
            "INSERT INTO source_revisions "
            "(id, source_document_id, content_hash, raw_content, importer_version, captured_at) "
            "VALUES (%s, %s, %s, %s, 'test', now())",
            (revision_id, document_id, "c" * 64, b"Sanitized supplied history."),
        )
        connection.execute(
            "INSERT INTO source_spans "
            "(id, source_revision_id, start_offset, end_offset, excerpt_hash) "
            "VALUES (%s, %s, 0, 27, %s)",
            (span_id, revision_id, "d" * 64),
        )
        connection.execute(
            "INSERT INTO proposals (id, workflow_session_id, status, created_at) "
            "VALUES (%s, %s, 'pending', now())",
            (proposal_id, child_workflow_id),
        )
        connection.execute(
            "INSERT INTO proposal_versions "
            "(id, proposal_id, version_number, content_hash, created_at) "
            "VALUES (%s, %s, 1, %s, now())",
            (version_id, proposal_id, content_hash),
        )
        connection.execute(
            "INSERT INTO proposal_items "
            "(id, proposal_version_id, sequence, mutation_kind, target_type, "
            "target_id, after_json) "
            "VALUES (%s, %s, 1, 'create_claim', 'claim', %s, %s)",
            (item_id, version_id, claim_id, Jsonb(payload)),
        )
        connection.execute(
            "INSERT INTO approvals (id, proposal_version_id, scope_json, approved_at) "
            "VALUES (%s, %s, %s, now())",
            (approval_id, version_id, Jsonb([str(item_id)])),
        )
        connection.execute(
            "INSERT INTO change_sets "
            "(id, idempotency_key, workflow_session_id, proposal_version_id, status, requested_at) "
            "VALUES (%s, %s, %s, %s, 'pending', now())",
            (
                change_set_id,
                f"test:{change_set_id}",
                child_workflow_id,
                version_id,
            ),
        )
    return (
        SeededChangeSet(
            workflow_id=child_workflow_id,
            proposal_id=proposal_id,
            version_id=version_id,
            approval_id=approval_id,
            change_set_id=change_set_id,
            item_ids=(item_id,),
            target_ids=(claim_id,),
            content_hash=content_hash,
            version_number=1,
        ),
        parent_workflow_id,
        span_id,
    )


def table_count(table: str, change_set_id: UUID | None = None) -> int:
    assert TEST_DSN is not None
    allowed = {"entities", "change_set_items", "receipts"}
    assert table in allowed
    where = " WHERE change_set_id = %s" if change_set_id and table != "entities" else ""
    parameters = (change_set_id,) if where else ()
    with psycopg.connect(TEST_DSN) as connection:
        row = connection.execute(f"SELECT count(*) FROM {table}{where}", parameters).fetchone()
    assert row is not None
    return int(row[0])


def fixture_case(case_id: str) -> Any:
    return next(case for case in load_interaction_fixture().cases if case.id == case_id)


def test_scoped_approval_fixture_runs_through_http_and_postgres() -> None:
    assert TEST_DSN is not None
    case = fixture_case("inspect-one-pending-claim-does-not-promote-siblings")
    assert "sibling" in " ".join(case.forbidden_output).lower()
    seeded = seed_change_set(item_count=2, approved_indexes=(0,))
    settings = Settings(database_url=TEST_DSN, environment="test", run_migrations=False)
    app = create_app(settings)

    async def apply_twice() -> tuple[httpx.Response, httpx.Response]:
        transport = httpx.ASGITransport(app=app)
        body = {
            "reviewed_version": 1,
            "approval_id": str(seeded.approval_id),
            "content_hash": seeded.content_hash,
        }
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            first = await client.post(f"/change-sets/{seeded.change_set_id}/apply", json=body)
            retry = await client.post(f"/change-sets/{seeded.change_set_id}/apply", json=body)
            return first, retry

    first, retry = asyncio.run(apply_twice())
    assert first.status_code == 200
    assert retry.status_code == 200
    assert first.json()["receipt_id"] == retry.json()["receipt_id"]
    assert first.json()["idempotent_replay"] is False
    assert retry.json()["idempotent_replay"] is True
    with psycopg.connect(TEST_DSN) as connection:
        rows = connection.execute("SELECT id FROM entities ORDER BY id").fetchall()
        proposal_status = connection.execute(
            "SELECT status FROM proposals WHERE id = %s", (seeded.proposal_id,)
        ).fetchone()
    assert rows == [(seeded.target_ids[0],)]
    assert proposal_status == ("pending",)
    assert table_count("change_set_items", seeded.change_set_id) == 1
    assert table_count("receipts", seeded.change_set_id) == 1


def test_edited_version_invalidates_prior_approval_without_writes() -> None:
    assert TEST_DSN is not None
    case = fixture_case("edited-claim-requires-exact-version-promotion")
    assert "earlier proposal version" in " ".join(case.forbidden_output)
    seeded = seed_change_set()
    second_version_id = uuid4()
    with psycopg.connect(TEST_DSN) as connection:
        connection.execute(
            "INSERT INTO proposal_versions "
            "(id, proposal_id, version_number, content_hash, created_at, supersedes_version_id) "
            "VALUES (%s, %s, 2, %s, now(), %s)",
            (second_version_id, seeded.proposal_id, "b" * 64, seeded.version_id),
        )

    repository = PostgresChangeSetRepository(PostgresDatabase(TEST_DSN))
    with pytest.raises(ChangeSetRejectedError, match="superseded proposal version"):
        repository.apply(seeded.command())

    assert table_count("entities") == 0
    assert table_count("change_set_items", seeded.change_set_id) == 0
    assert table_count("receipts", seeded.change_set_id) == 0


def test_content_hash_mismatch_is_rejected_without_writes() -> None:
    assert TEST_DSN is not None
    seeded = seed_change_set()
    repository = PostgresChangeSetRepository(PostgresDatabase(TEST_DSN))
    changed_command = seeded.command().model_copy(update={"content_hash": "f" * 64})

    with pytest.raises(ChangeSetRejectedError, match="content hash does not match"):
        repository.apply(changed_command)

    assert table_count("entities") == 0
    assert table_count("change_set_items", seeded.change_set_id) == 0
    assert table_count("receipts", seeded.change_set_id) == 0


def test_direct_lore_fixture_applies_evidence_backed_claim_and_preserves_parent() -> None:
    assert TEST_DSN is not None
    case = fixture_case("direct-lore-update-returns-to-brainstorm")
    assert "return" in " ".join(case.expected_output).lower()
    entity_seed = seed_change_set()
    repository = PostgresChangeSetRepository(PostgresDatabase(TEST_DSN))
    repository.apply(entity_seed.command())
    claim_seed, parent_workflow_id, span_id = seed_direct_lore_claim(
        entity_seed.target_ids[0]
    )

    receipt = repository.apply(claim_seed.command())

    assert receipt.applied_item_ids == claim_seed.item_ids
    with psycopg.connect(TEST_DSN) as connection:
        claim = connection.execute(
            "SELECT assertion_text, state, authority FROM claims WHERE id = %s",
            (claim_seed.target_ids[0],),
        ).fetchone()
        evidence = connection.execute(
            "SELECT source_span_id, evidence_role FROM claim_evidence WHERE claim_id = %s",
            (claim_seed.target_ids[0],),
        ).fetchone()
        parent = connection.execute(
            "SELECT kind, closed_at FROM workflow_sessions WHERE id = %s",
            (parent_workflow_id,),
        ).fetchone()
    assert claim == ("Sanitized supplied history.", "established", "explicit_lore")
    assert evidence == (span_id, "direct_input")
    assert parent == ("brainstorm", None)


def test_failure_on_later_item_rolls_back_mutation_and_receipt() -> None:
    assert TEST_DSN is not None
    seeded = seed_change_set(
        item_count=2,
        mutation_kinds=("create_entity", "unsupported_mutation"),
    )
    repository = PostgresChangeSetRepository(PostgresDatabase(TEST_DSN))

    with pytest.raises(ChangeSetRejectedError, match="unsupported canonical mutation"):
        repository.apply(seeded.command())

    assert table_count("entities") == 0
    assert table_count("change_set_items", seeded.change_set_id) == 0
    assert table_count("receipts", seeded.change_set_id) == 0
    with psycopg.connect(TEST_DSN) as connection:
        status = connection.execute(
            "SELECT status, applied_at FROM change_sets WHERE id = %s",
            (seeded.change_set_id,),
        ).fetchone()
    assert status == ("pending", None)


def test_concurrent_retries_return_one_receipt_without_duplicates() -> None:
    assert TEST_DSN is not None
    seeded = seed_change_set()

    def apply() -> Any:
        repository = PostgresChangeSetRepository(PostgresDatabase(TEST_DSN))
        return repository.apply(seeded.command())

    with ThreadPoolExecutor(max_workers=2) as pool:
        receipts = tuple(pool.map(lambda _: apply(), range(2)))

    assert receipts[0].receipt_id == receipts[1].receipt_id
    assert {receipt.idempotent_replay for receipt in receipts} == {False, True}
    assert table_count("entities") == 1
    assert table_count("change_set_items", seeded.change_set_id) == 1
    assert table_count("receipts", seeded.change_set_id) == 1
