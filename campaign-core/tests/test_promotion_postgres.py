"""Postgres integration for the Promotion Pipeline commit chain (TKT-0136).

Exercises the real machinery end to end: derive reads claims, approve files
the description with statement candidates, proposes, approves, and applies
the change set in one user action — then replays idempotently.
"""

from __future__ import annotations

import os
from typing import Any
from uuid import uuid4

import psycopg
import pytest

from dm_assistant_core.adapters.postgres.migrate import run_migrations

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
            "TRUNCATE TABLE import_runs, source_documents, workflow_sessions, "
            "change_sets CASCADE"
        )


def _post(path: str, payload: dict) -> Any:
    """Run one request through the app with the async transport the API needs."""
    import asyncio

    import httpx

    from dm_assistant_core.api.app import create_app
    from dm_assistant_core.config import Settings

    assert TEST_DSN is not None
    application = create_app(
        Settings(database_url=TEST_DSN, environment="test", run_migrations=False)
    )

    async def send() -> Any:
        transport = httpx.ASGITransport(app=application)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            return await client.post(path, json=payload)

    return asyncio.run(send())


def _seed_entity(name: str) -> str:
    assert TEST_DSN is not None
    workflow, change_set, entity = uuid4(), uuid4(), uuid4()
    with psycopg.connect(TEST_DSN) as connection:
        connection.execute(
            "INSERT INTO workflow_sessions (id, kind, started_at) "
            "VALUES (%s, 'lore_entry', now())",
            (workflow,),
        )
        connection.execute(
            "INSERT INTO change_sets (id, idempotency_key, workflow_session_id, "
            "status, requested_at, applied_at) "
            "VALUES (%s, %s, %s, 'applied', now(), now())",
            (change_set, f"seed:{change_set}", workflow),
        )
        connection.execute(
            "INSERT INTO entities (id, entity_type, canonical_name, "
            "created_by_change_set_id, created_at, updated_at) "
            "VALUES (%s, 'location', %s, %s, now(), now())",
            (entity, name, change_set),
        )
    return str(entity)


def _approve_payload(entity_id: str, document_text: str, candidates: list, key: str) -> dict:
    return {
        "surface": "description",
        "entity_id": entity_id,
        "document_text": document_text,
        "statements": [
            {
                "span_start": candidate["span_start"],
                "span_end": candidate["span_end"],
                "assertion_text": candidate["assertion_text"],
                "state": "established",
                "included": candidate["included"],
            }
            for candidate in candidates
        ],
        "referenced_claim_ids": [],
        "idempotency_key": key,
    }


def test_promotion_commit_chain_and_idempotent_replay() -> None:
    entity_id = _seed_entity("Fleurite Treasury")
    document_text = (
        "The Treasury funds the rebellion. Its vault lies beneath the palace."
    )

    derived = _post(
        "/promotion/derive",
        {
            "surface": "description",
            "entity_id": entity_id,
            "document_text": document_text,
            "referenced_claim_ids": [],
        },
    )
    assert derived.status_code == 200, derived.text
    candidates = derived.json()["candidates"]
    assert [candidate["consequence"]["kind"] for candidate in candidates] == [
        "new_claim",
        "new_claim",
    ]
    assert all(candidate["included"] for candidate in candidates)

    key = f"promotion-test:{uuid4()}"
    approved = _post(
        "/promotion/approve", _approve_payload(entity_id, document_text, candidates, key)
    )
    assert approved.status_code == 200, approved.text
    receipt = approved.json()
    assert receipt["claims_committed"] == 2
    assert receipt["claim_ids"]

    replay = _post(
        "/promotion/approve", _approve_payload(entity_id, document_text, candidates, key)
    )
    assert replay.status_code == 200, replay.text
    assert replay.json()["claims_committed"] == 2
    assert replay.json()["idempotent_replay"] is True

    with psycopg.connect(TEST_DSN) as connection:
        rows = connection.execute(
            "SELECT assertion_text, state, authority, subject_entity_id "
            "FROM claims WHERE subject_entity_id = %s ORDER BY assertion_text",
            (entity_id,),
        ).fetchall()
    assert len(rows) == 2
    assert {row[1] for row in rows} == {"established"}
    assert {row[2] for row in rows} == {"explicit_lore"}


def test_derive_flags_restatement_of_referenced_claim() -> None:
    entity_id = _seed_entity("Vault of Ishi")
    claim_id = uuid4()
    with psycopg.connect(TEST_DSN) as connection:
        connection.execute(
            "INSERT INTO claims (id, subject_entity_id, assertion_text, state, "
            "authority, confidence, visibility, recorded_at, created_at, updated_at) "
            "VALUES (%s, %s, 'The vault of Ishi was sealed by the Fleurite king', "
            "'established', 'explicit_lore', 0.9500, 'dm_only', now(), now(), now())",
            (claim_id, entity_id),
        )
    derived = _post(
        "/promotion/derive",
        {
            "surface": "description",
            "entity_id": entity_id,
            "document_text": "The vault of Ishi was sealed by the Fleurite king.",
            "referenced_claim_ids": [str(claim_id)],
        },
    )
    assert derived.status_code == 200
    candidate = derived.json()["candidates"][0]
    assert candidate["consequence"]["kind"] == "reference"
    assert candidate["included"] is False


def test_lore_promotion_creates_entity_claims_and_moves_linked() -> None:
    """The bound-created surface: entity mint, description with statement
    candidates, claims applied, and linked assertions re-attributed to the
    new owner — one approve action, then idempotent replay."""
    # Seed an orphaned-ish claim owned by an existing record to move.
    assert TEST_DSN is not None
    workflow, change_set, owner = uuid4(), uuid4(), uuid4()
    claim_to_move = uuid4()
    with psycopg.connect(TEST_DSN) as connection:
        connection.execute(
            "INSERT INTO workflow_sessions (id, kind, started_at) "
            "VALUES (%s, 'lore_entry', now())",
            (workflow,),
        )
        connection.execute(
            "INSERT INTO change_sets (id, idempotency_key, workflow_session_id, "
            "status, requested_at, applied_at) VALUES (%s, %s, %s, 'applied', now(), now())",
            (change_set, f"seed:{change_set}", workflow),
        )
        connection.execute(
            "INSERT INTO entities (id, entity_type, canonical_name, "
            "created_by_change_set_id, created_at, updated_at) "
            "VALUES (%s, 'faction', 'Fleurite Exiles', %s, now(), now())",
            (owner, change_set),
        )
        connection.execute(
            "INSERT INTO claims (id, subject_entity_id, assertion_text, state, "
            "authority, confidence, visibility, recorded_at, created_at, updated_at) "
            "VALUES (%s, %s, 'The king sealed the treasury before fleeing.', "
            "'established', 'explicit_lore', 0.9500, 'dm_only', now(), now(), now())",
            (claim_to_move, owner),
        )

    document_text = (
        "The Fleurite Treasury funds the rebellion. Its vault lies beneath the palace."
    )
    derived = _post(
        "/promotion/derive",
        {
            "surface": "lore",
            "entity_name": "Fleurite Treasury",
            "entity_kind": "location",
            "document_text": document_text,
            "referenced_claim_ids": [],
        },
    )
    assert derived.status_code == 200, derived.text
    payload = derived.json()
    assert payload["ownership"] == "bound_created"
    assert payload["entity_name"] == "Fleurite Treasury"
    assert [c["consequence"]["kind"] for c in payload["candidates"]] == [
        "new_claim",
        "new_claim",
    ]

    key = f"promotion-lore-test:{uuid4()}"
    approved = _post(
        "/promotion/approve",
        {
            "surface": "lore",
            "entity_name": "Fleurite Treasury",
            "entity_kind": "location",
            "document_text": document_text,
            "statements": [
                {
                    "span_start": c["span_start"],
                    "span_end": c["span_end"],
                    "assertion_text": c["assertion_text"],
                    "state": "established",
                    "included": c["included"],
                }
                for c in payload["candidates"]
            ],
            "referenced_claim_ids": [],
            "linked_claim_ids": [str(claim_to_move)],
            "idempotency_key": key,
        },
    )
    assert approved.status_code == 200, approved.text
    receipt = approved.json()
    assert receipt["claims_committed"] == 2
    new_entity = receipt["entity_id"]
    assert receipt["moved_claim_ids"] == [str(claim_to_move)]

    replay = _post(
        "/promotion/approve",
        {
            "surface": "lore",
            "entity_name": "Fleurite Treasury",
            "entity_kind": "location",
            "document_text": document_text,
            "statements": [
                {
                    "span_start": c["span_start"],
                    "span_end": c["span_end"],
                    "assertion_text": c["assertion_text"],
                    "state": "established",
                    "included": c["included"],
                }
                for c in payload["candidates"]
            ],
            "referenced_claim_ids": [],
            "linked_claim_ids": [str(claim_to_move)],
            "idempotency_key": key,
        },
    )
    assert replay.status_code == 200, replay.text
    assert replay.json()["claims_committed"] == 2
    assert replay.json()["idempotent_replay"] is True

    with psycopg.connect(TEST_DSN) as connection:
        rows = connection.execute(
            "SELECT assertion_text FROM claims WHERE subject_entity_id = %s "
            "ORDER BY assertion_text",
            (new_entity,),
        ).fetchall()
        moved = connection.execute(
            "SELECT subject_entity_id FROM claims WHERE id = %s",
            (claim_to_move,),
        ).fetchone()
        entity = connection.execute(
            "SELECT entity_type, canonical_name FROM entities WHERE id = %s",
            (new_entity,),
        ).fetchone()
    assert len(rows) == 3  # two promoted + the moved linked claim
    assert str(moved[0]) == new_entity
    assert entity[0] == "location" and entity[1] == "Fleurite Treasury"


def test_brainstorm_promotion_mints_records_and_applies_claims() -> None:
    """Free surface end to end: a real brainstorm session's thought candidates
    promote with per-statement subjects — one existing record, one new record
    shared by two thoughts — bound to the brainstorm workflow session."""
    import asyncio

    import httpx

    from dm_assistant_core.adapters.postgres.brainstorms import (
        PostgresBrainstormRepository,
    )
    from dm_assistant_core.adapters.postgres.database import PostgresDatabase
    from dm_assistant_core.api.app import create_app
    from dm_assistant_core.application.brainstorms import (
        BrainstormService,
        CaptureBrainstormThoughtCommand,
        StartBrainstormCommand,
    )
    from dm_assistant_core.config import Settings

    assert TEST_DSN is not None
    # Seed an existing record to use as one subject.
    workflow, change_set, existing = uuid4(), uuid4(), uuid4()
    with psycopg.connect(TEST_DSN) as connection:
        connection.execute(
            "INSERT INTO workflow_sessions (id, kind, started_at) "
            "VALUES (%s, 'lore_entry', now())",
            (workflow,),
        )
        connection.execute(
            "INSERT INTO change_sets (id, idempotency_key, workflow_session_id, "
            "status, requested_at, applied_at) VALUES (%s, %s, %s, 'applied', now(), now())",
            (change_set, f"seed:{change_set}", workflow),
        )
        connection.execute(
            "INSERT INTO entities (id, entity_type, canonical_name, "
            "created_by_change_set_id, created_at, updated_at) "
            "VALUES (%s, 'faction', 'Fleurite Exiles', %s, now(), now())",
            (existing, change_set),
        )

    from dm_assistant_core.adapters.postgres.imports import (
        PostgresMarkdownImportRepository,
    )
    from dm_assistant_core.adapters.postgres.retrieval import (
        PostgresRetrievalRepository,
    )
    from dm_assistant_core.application.imports import MarkdownImportService
    from dm_assistant_core.application.retrieval import RetrievalService

    brainstorms = BrainstormService(
        PostgresBrainstormRepository(PostgresDatabase(TEST_DSN)),
        MarkdownImportService(PostgresMarkdownImportRepository(PostgresDatabase(TEST_DSN))),
        RetrievalService(PostgresRetrievalRepository(PostgresDatabase(TEST_DSN))),
    )
    session = brainstorms.start(
        StartBrainstormCommand(title="Guild ideas", idempotency_key=f"bs:{uuid4()}")
    )
    # capture() returns the refreshed session; the thoughts ride on it.
    session = brainstorms.capture(
        session.session_id,
        CaptureBrainstormThoughtCommand(
            text="The Guild repairs the archive's oldest ledgers.",
            idempotency_key=f"th:{uuid4()}",
        ),
    )
    session = brainstorms.capture(
        session.session_id,
        CaptureBrainstormThoughtCommand(
            text="The Guild answers to no crown.",
            idempotency_key=f"th:{uuid4()}",
        ),
    )
    thought_a, thought_b = session.thoughts

    application = create_app(
        Settings(database_url=TEST_DSN, environment="test", run_migrations=False)
    )

    async def post(path: str, payload: dict) -> Any:
        transport = httpx.ASGITransport(app=application)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post(path, json=payload, params={"requester_role": "dm"})

    key = f"promotion-brainstorm-test:{uuid4()}"
    statements = [
        {
            "span_start": 0,
            "span_end": len("The Guild repairs the archive's oldest ledgers."),
            "assertion_text": "The Guild repairs the archive's oldest ledgers.",
            "state": "considered",
            "included": True,
            "subject": {"entity_id": str(existing)},
            "candidate_id": str(thought_a.candidate_id),
            "evidence_revision_id": str(thought_a.source_revision_id),
        },
        {
            "span_start": 0,
            "span_end": len("The Guild answers to no crown."),
            "assertion_text": "The Guild answers to no crown.",
            "state": "established",
            "included": True,
            "subject": {"new_record": "r1", "name": "Vault Guild", "entity_kind": "faction"},
            "candidate_id": str(thought_b.candidate_id),
            "evidence_revision_id": str(thought_b.source_revision_id),
        },
    ]
    approved = asyncio.run(post("/promotion/approve", {
        "surface": "brainstorm",
        "document_text": "joined",
        "workflow_session_id": str(session.session_id),
        "statements": statements,
        "referenced_claim_ids": [],
        "idempotency_key": key,
    }))
    assert approved.status_code == 200, approved.text
    receipt = approved.json()
    assert receipt["claims_committed"] == 2
    assert len(receipt["created_entity_ids"]) == 1
    guild = receipt["created_entity_ids"][0]

    with psycopg.connect(TEST_DSN) as connection:
        rows = connection.execute(
            "SELECT subject_entity_id, assertion_text, state, authority FROM claims "
            "WHERE id = ANY(%s) ORDER BY assertion_text",
            ([str(c) for c in receipt["claim_ids"]],),
        ).fetchall()
        entity = connection.execute(
            "SELECT entity_type, canonical_name FROM entities WHERE id = %s", (guild,)
        ).fetchone()
        proposal = connection.execute(
            "SELECT workflow_session_id FROM proposals WHERE id = %s",
            (receipt["proposal_id"],),
        ).fetchone()
    assert len(rows) == 2
    by_subject = {str(row[0]): row for row in rows}
    assert str(existing) in by_subject
    assert guild in by_subject
    assert by_subject[guild][2] == "established"
    assert entity[0] == "faction" and entity[1] == "Vault Guild"
    assert str(proposal[0]) == str(session.session_id)


def test_unpromoted_material_audit_finds_shells_and_pending_captures() -> None:
    """The repair lane's standing audit: an entity with an authored page and
    no claims (empty shell) and a pending direct capture both surface."""
    import asyncio

    import httpx

    from dm_assistant_core.adapters.postgres.database import PostgresDatabase
    from dm_assistant_core.adapters.postgres.imports import (
        PostgresMarkdownImportRepository,
    )
    from dm_assistant_core.api.app import create_app
    from dm_assistant_core.application.imports import MarkdownImportService
    from dm_assistant_core.config import Settings

    assert TEST_DSN is not None
    # An empty shell: entity + authored page path, zero claims.
    workflow, change_set, shell = uuid4(), uuid4(), uuid4()
    slug = "shell-hollow"
    with psycopg.connect(TEST_DSN) as connection:
        connection.execute(
            "INSERT INTO workflow_sessions (id, kind, started_at) "
            "VALUES (%s, 'lore_entry', now())",
            (workflow,),
        )
        connection.execute(
            "INSERT INTO change_sets (id, idempotency_key, workflow_session_id, "
            "status, requested_at, applied_at) VALUES (%s, %s, %s, 'applied', now(), now())",
            (change_set, f"seed:{change_set}", workflow),
        )
        connection.execute(
            "INSERT INTO entities (id, entity_type, canonical_name, "
            "created_by_change_set_id, created_at, updated_at) "
            "VALUES (%s, 'location', 'Shell Hollow', %s, now(), now())",
            (shell, change_set),
        )
        connection.execute(
            "INSERT INTO source_documents (id, source_kind, connector, original_path, "
            "external_id, first_seen_at) VALUES (%s, 'markdown', 'filesystem', %s, %s, now())",
            (uuid4(), f"entities/{slug}.md", str(uuid4())),
        )
        doc = connection.execute(
            "SELECT id FROM source_documents ORDER BY first_seen_at DESC LIMIT 1"
        ).fetchone()[0]
        connection.execute(
            "INSERT INTO source_document_paths (source_document_id, connector, "
            "normalized_path, first_seen_at, last_seen_at, is_current) "
            "VALUES (%s, 'filesystem', %s, now(), now(), true)",
            (doc, f"entities/{slug}.md"),
        )
        connection.execute(
            "INSERT INTO source_revisions (id, source_document_id, content_hash, "
            "raw_content, importer_version, captured_at, frontmatter_json) "
            "VALUES (%s, %s, %s, %s, 'seed', now(), %s::jsonb)",
            (uuid4(), doc, "a" * 64, b"# Shell Hollow\n\nAn empty place.",
             '{"type": "entity-description"}'),
        )

    # A pending capture via the description service (statement candidates that
    # are never proposed stay pending).
    descriptions = MarkdownImportService(PostgresMarkdownImportRepository(PostgresDatabase(TEST_DSN)))
    from dm_assistant_core.application.entity_descriptions import (
        EntityDescriptionCommand,
        EntityDescriptionService,
    )

    class NameLookup:
        def __init__(self) -> None:
            self._database = PostgresDatabase(TEST_DSN)

        def get(self, entity_id):
            with self._database.connection() as connection:
                row = connection.execute(
                    "SELECT id, canonical_name FROM entities WHERE id = %s",
                    (entity_id,),
                ).fetchone()
            if row is None:
                return None
            return type("Entity", (), {"entity_id": row[0], "canonical_name": row[1]})()

    writer = EntityDescriptionService(descriptions, NameLookup())
    writer.write(EntityDescriptionCommand(
        entity_id=shell,
        text="Shell Hollow holds nothing yet. Its wells ran dry long ago.",
        idempotency_key=f"audit:{uuid4()}",
        statement_spans=((0, 31),),
    ))

    application = create_app(
        Settings(database_url=TEST_DSN, environment="test", run_migrations=False)
    )

    async def get(path: str) -> Any:
        transport = httpx.ASGITransport(app=application)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get(path, params={"requester_role": "dm"})

    result = asyncio.run(get("/campaign/unpromoted-material"))
    assert result.status_code == 200, result.text
    findings = result.json()["findings"]
    shells = [f for f in findings if f["kind"] == "empty_shell" and f["entity_id"] == str(shell)]
    assert shells, findings
    assert "authored page but no claims" in shells[0]["detail"]
    captures = [f for f in findings if f["kind"] == "pending_capture" and "shell" in (f["document_path"] or "")]
    assert captures, findings
    assert captures[0]["count"] >= 1


def test_qualified_entity_audit_computes_the_bar() -> None:
    """Q1 (zero claims fails), Q4 (parent_location kind), Q6 (vocabulary
    membership), pending criteria never silently passed."""
    import asyncio

    import httpx

    from dm_assistant_core.api.app import create_app
    from dm_assistant_core.config import Settings

    assert TEST_DSN is not None
    workflow, change_set = uuid4(), uuid4()
    with_claims, empty, wrong_parent, city = uuid4(), uuid4(), uuid4(), uuid4()
    with psycopg.connect(TEST_DSN) as connection:
        connection.execute(
            "INSERT INTO workflow_sessions (id, kind, started_at) VALUES (%s, 'lore_entry', now())",
            (workflow,),
        )
        connection.execute(
            "INSERT INTO change_sets (id, idempotency_key, workflow_session_id, "
            "status, requested_at, applied_at) VALUES (%s, %s, %s, 'applied', now(), now())",
            (change_set, f"seed:{change_set}", workflow),
        )
        for entity_id, name, kind in (
            (with_claims, "Qualified Keep", "location"),
            (empty, "Empty Hollow", "location"),
            (wrong_parent, "Wrong Parent", "location"),
            (city, "Realmsport", "faction"),
        ):
            connection.execute(
                "INSERT INTO entities (id, entity_type, canonical_name, "
                "created_by_change_set_id, created_at, updated_at) "
                "VALUES (%s, %s, %s, %s, now(), now())",
                (entity_id, kind, name, change_set),
            )
        connection.execute(
            "INSERT INTO claims (id, subject_entity_id, assertion_text, state, "
            "authority, confidence, visibility, recorded_at, created_at, updated_at) "
            "VALUES (%s, %s, 'The keep stands.', 'established', 'explicit_lore', "
            "0.9500, 'dm_only', now(), now(), now())",
            (uuid4(), with_claims),
        )
        connection.execute(
            "INSERT INTO claims (id, subject_entity_id, assertion_text, state, "
            "authority, confidence, visibility, recorded_at, created_at, updated_at) "
            "VALUES (%s, %s, 'The city thrives.', 'established', 'explicit_lore', "
            "0.9500, 'dm_only', now(), now(), now())",
            (uuid4(), city),
        )
        # wrong_parent's parent_location points at a faction.
        connection.execute(
            "INSERT INTO entity_profiles (entity_id, version, profile_json) "
            "VALUES (%s, 1, %s::jsonb)",
            (wrong_parent, '{"parent_location": "Realmsport"}'),
        )
        # A retired vocabulary value in use fails Q6.
        retire_receipt, add_receipt = uuid4(), uuid4()
        connection.execute(
            "INSERT INTO vocabulary_receipts (receipt_id, vocabulary, action, value, changed_at) "
            "VALUES (%s, 'location_type', 'retire', 'citadel', now())",
            (retire_receipt,),
        )
        connection.execute(
            "INSERT INTO vocabulary_receipts (receipt_id, vocabulary, action, value, changed_at) "
            "VALUES (%s, 'location_type', 'add', 'keep', now())",
            (add_receipt,),
        )
        connection.execute(
            "INSERT INTO template_vocabularies (vocabulary, value, retired, receipt_id, updated_at) "
            "VALUES ('location_type', 'citadel', true, %s, now()), ('location_type', 'keep', false, %s, now())",
            (retire_receipt, add_receipt),
        )
        connection.execute(
            "INSERT INTO entity_profiles (entity_id, version, profile_json) "
            "VALUES (%s, 1, %s::jsonb)",
            (with_claims, '{"location_type": "citadel"}'),
        )

    application = create_app(
        Settings(database_url=TEST_DSN, environment="test", run_migrations=False)
    )

    async def get(path: str) -> Any:
        transport = httpx.ASGITransport(app=application)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get(path, params={"requester_role": "dm"})

    result = asyncio.run(get("/campaign/qualified-entities"))
    assert result.status_code == 200, result.text
    payload = result.json()
    by_id = {f["entity_id"]: f for f in payload["unqualified"]}

    # Empty Hollow: Q1 fails — no current claims.
    assert str(empty) in by_id
    empty_reasons = [c["reason"] for c in by_id[str(empty)]["criteria"] if c["status"] == "fail"]
    assert any("no current claims" in r for r in empty_reasons)

    # Wrong Parent: Q4 fails — parent_location is a faction.
    assert str(wrong_parent) in by_id
    parent_reasons = [c["reason"] for c in by_id[str(wrong_parent)]["criteria"] if c["status"] == "fail"]
    assert any("not a location" in r for r in parent_reasons)

    # Qualified Keep fails ONLY on Q6: retired vocabulary value in use.
    assert str(with_claims) in by_id
    keep_fails = [c["criterion"] for c in by_id[str(with_claims)]["criteria"] if c["status"] == "fail"]
    assert keep_fails == ["q6_vocabulary"]
    # Pending criteria are reported, never silently passed.
    pendings = {c["criterion"]: c["status"] for f in payload["unqualified"] for c in f["criteria"]}
    assert pendings.get("q3_ownership") == "pending"
    assert pendings.get("q5_attributes_minted") == "pending"

    # Realmsport (faction with claims, no failing criteria) is not listed.
    assert str(city) not in by_id


def test_brainstorm_wip_collapses_to_one_finding() -> None:
    """A work-in-progress brainstorm surfaces ONCE (its session row with the
    thought count), never again per thought document."""
    import asyncio

    import httpx

    from dm_assistant_core.adapters.postgres.brainstorms import (
        PostgresBrainstormRepository,
    )
    from dm_assistant_core.adapters.postgres.database import PostgresDatabase
    from dm_assistant_core.adapters.postgres.imports import (
        PostgresMarkdownImportRepository,
    )
    from dm_assistant_core.adapters.postgres.retrieval import (
        PostgresRetrievalRepository,
    )
    from dm_assistant_core.api.app import create_app
    from dm_assistant_core.application.brainstorms import (
        BrainstormService,
        CaptureBrainstormThoughtCommand,
        StartBrainstormCommand,
    )
    from dm_assistant_core.application.imports import MarkdownImportService
    from dm_assistant_core.application.retrieval import RetrievalService
    from dm_assistant_core.config import Settings

    assert TEST_DSN is not None
    brainstorms = BrainstormService(
        PostgresBrainstormRepository(PostgresDatabase(TEST_DSN)),
        MarkdownImportService(PostgresMarkdownImportRepository(PostgresDatabase(TEST_DSN))),
        RetrievalService(PostgresRetrievalRepository(PostgresDatabase(TEST_DSN))),
    )
    session = brainstorms.start(
        StartBrainstormCommand(title="The Wrath of Romulus", idempotency_key=f"bs:{uuid4()}")
    )
    for index in range(5):
        session = brainstorms.capture(
            session.session_id,
            CaptureBrainstormThoughtCommand(
                text=f"Wrath thought {index} about the countermove.",
                idempotency_key=f"th:{uuid4()}",
            ),
        )

    application = create_app(
        Settings(database_url=TEST_DSN, environment="test", run_migrations=False)
    )

    async def get(path: str) -> Any:
        transport = httpx.ASGITransport(app=application)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get(path, params={"requester_role": "dm"})

    result = asyncio.run(get("/campaign/unpromoted-material"))
    assert result.status_code == 200
    findings = result.json()["findings"]
    wrath = [f for f in findings if "wrath" in f["entity_name"].lower()]
    assert len(wrath) == 1, findings
    assert wrath[0]["kind"] == "unpromoted_thoughts"
    assert wrath[0]["count"] == 5


def test_initial_attribution_and_exclusive_claims_endpoint() -> None:
    """Step 1 end to end: an unqualified entity's document-exclusive orphan
    claims surface via the endpoint, and Assign Ownership (initial
    attribution, migration 0067) gives the entity its first claim."""
    import asyncio

    import httpx

    from dm_assistant_core.api.app import create_app
    from dm_assistant_core.config import Settings

    assert TEST_DSN is not None
    workflow, change_set, shell = uuid4(), uuid4(), uuid4()
    doc, revision, span = uuid4(), uuid4(), uuid4()
    claim_a, claim_b = uuid4(), uuid4()
    other_doc, other_rev, other_span = uuid4(), uuid4(), uuid4()
    with psycopg.connect(TEST_DSN) as connection:
        connection.execute(
            "INSERT INTO workflow_sessions (id, kind, started_at) VALUES (%s, 'lore_entry', now())",
            (workflow,),
        )
        connection.execute(
            "INSERT INTO change_sets (id, idempotency_key, workflow_session_id, "
            "status, requested_at, applied_at) VALUES (%s, %s, %s, 'applied', now(), now())",
            (change_set, f"seed:{change_set}", workflow),
        )
        connection.execute(
            "INSERT INTO entities (id, entity_type, canonical_name, "
            "created_by_change_set_id, created_at, updated_at) "
            "VALUES (%s, 'npc', 'Raven King', %s, now(), now())",
            (shell, change_set),
        )
        for path, document, rev, sp in (
            ("lore/the-raven-king.md", doc, revision, span),
            ("lore/cosmology.md", other_doc, other_rev, other_span),
        ):
            connection.execute(
                "INSERT INTO source_documents (id, source_kind, connector, original_path, "
                "external_id, first_seen_at) VALUES (%s, 'markdown', 'filesystem', %s, %s, now())",
                (document, path, str(document)),
            )
            connection.execute(
                "INSERT INTO source_document_paths (source_document_id, connector, "
                "normalized_path, first_seen_at, last_seen_at, is_current) "
                "VALUES (%s, 'filesystem', %s, now(), now(), true)",
                (document, path),
            )
            connection.execute(
                "INSERT INTO source_revisions (id, source_document_id, content_hash, "
                "raw_content, importer_version, captured_at) VALUES (%s, %s, %s, %s, 'seed', now())",
                (rev, document, 'a' * 64, b"notes"),
            )
            connection.execute(
                "INSERT INTO source_spans (id, source_revision_id, section_path, "
                "start_offset, end_offset, excerpt_hash) VALUES (%s, %s, 'Body', 0, 10, %s)",
                (sp, rev, 'b' * 64),
            )
        # claim_a: orphan, evidenced ONLY on the raven-king doc → exclusive.
        # claim_b: orphan, evidenced on BOTH docs → not exclusive.
        for claim_id in (claim_a, claim_b):
            connection.execute(
                "INSERT INTO claims (id, subject_entity_id, assertion_text, state, "
                "authority, confidence, visibility, recorded_at, created_at, updated_at) "
                "VALUES (%s, NULL, %s, 'established', 'explicit_lore', "
                "0.9500, 'dm_only', now(), now(), now())",
                (claim_id, "Raven King claim " + str(claim_id)[:8]),
            )
            connection.execute(
                "INSERT INTO claim_evidence (claim_id, source_span_id, evidence_role) "
                "VALUES (%s, %s, 'support')",
                (claim_id, span),
            )
        connection.execute(
            "INSERT INTO claim_evidence (claim_id, source_span_id, evidence_role) "
            "VALUES (%s, %s, 'support')",
            (claim_b, other_span),
        )

    application = create_app(
        Settings(database_url=TEST_DSN, environment="test", run_migrations=False)
    )

    async def call(method: str, path: str, payload: dict | None = None) -> Any:
        transport = httpx.ASGITransport(app=application)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            if method == "GET":
                return await client.get(path, params={"requester_role": "dm"})
            return await client.post(path, json=payload, params={"requester_role": "dm"})

    gathered = asyncio.run(call("GET", "/campaign/unqualified-exclusive-claims"))
    assert gathered.status_code == 200, gathered.text
    groups = [g for g in gathered.json()["groups"] if g["canonical_name"] == "Raven King"]
    assert groups and groups[0]["document_path"] == "lore/the-raven-king.md"
    claim_ids = [c["claim_id"] for c in groups[0]["claims"]]
    assert str(claim_a) in claim_ids
    assert str(claim_b) not in claim_ids  # dual-evidenced → not exclusive

    assigned = asyncio.run(call("POST", f"/claims/{claim_a}/reattribute", {
        "claim_id": str(claim_a),
        "new_entity_id": str(shell),
        "reason": "Assign Ownership: Raven King's document claims",
    }))
    assert assigned.status_code == 200, assigned.text
    with psycopg.connect(TEST_DSN) as connection:
        owner = connection.execute(
            "SELECT subject_entity_id FROM claims WHERE id = %s", (claim_a,)
        ).fetchone()[0]
    assert str(owner) == str(shell)
