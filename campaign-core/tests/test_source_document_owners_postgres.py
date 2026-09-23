"""Backward ownership link on source document claims (user ruling 2026-09-21).

getSourceDocument canonical claims carry their owning record so evidence
surfaces can title and group by entity — the document alone never told the
reader (or the model) whose record a claim belongs to.
"""

from __future__ import annotations

import hashlib
import os
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


def _get(path: str) -> object:
    import asyncio

    import httpx

    from dm_assistant_core.api.app import create_app
    from dm_assistant_core.config import Settings

    assert TEST_DSN is not None
    application = create_app(
        Settings(database_url=TEST_DSN, environment="test", run_migrations=False)
    )

    async def send() -> object:
        transport = httpx.ASGITransport(app=application)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            return await client.get(path, params={"requester_role": "dm"})

    return asyncio.run(send())


def test_source_document_claims_carry_their_owning_record() -> None:
    assert TEST_DSN is not None
    workflow, change_set, owner, unowned = uuid4(), uuid4(), uuid4(), uuid4()
    document, revision, span_owned, span_unowned = uuid4(), uuid4(), uuid4(), uuid4()
    owned_claim, loose_claim = uuid4(), uuid4()
    text = "The vault of Ishi was sealed by the Fleurite king. Rumors spread regardless."

    def excerpt_hash(start: int, end: int) -> str:
        return hashlib.sha256(text[start:end].encode()).hexdigest()

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
            "VALUES (%s, 'location', 'Vault of Ishi', %s, now(), now())",
            (owner, change_set),
        )
        connection.execute(
            "INSERT INTO source_documents (id, source_kind, connector, original_path, "
            "external_id, first_seen_at) VALUES (%s, 'markdown', 'filesystem', %s, %s, now())",
            (document, "lore/vault.md", str(document)),
        )
        connection.execute(
            "INSERT INTO source_document_paths (source_document_id, connector, "
            "normalized_path, first_seen_at, last_seen_at, is_current) "
            "VALUES (%s, 'filesystem', 'lore/vault.md', now(), now(), true)",
            (document,),
        )
        connection.execute(
            "INSERT INTO source_revisions (id, source_document_id, content_hash, "
            "raw_content, importer_version, captured_at) "
            "VALUES (%s, %s, %s, %s, 'seed', now())",
            (revision, document, hashlib.sha256(text.encode()).hexdigest(),
             text.encode()),
        )
        connection.execute(
            "INSERT INTO source_spans (id, source_revision_id, section_path, "
            "start_offset, end_offset, excerpt_hash) VALUES "
            "(%s, %s, 'Body', 0, 42, %s), (%s, %s, 'Body', 43, %s, %s)",
            (span_owned, revision, excerpt_hash(0, 42),
             span_unowned, revision, len(text), excerpt_hash(43, len(text))),
        )
        for claim_id, span_id, subject in (
            (owned_claim, span_owned, owner),
            (loose_claim, span_unowned, None),
        ):
            connection.execute(
                "INSERT INTO claims (id, subject_entity_id, assertion_text, state, "
                "authority, confidence, visibility, recorded_at, created_at, updated_at) "
                "VALUES (%s, %s, %s, 'established', 'explicit_lore', "
                "0.9500, 'dm_only', now(), now(), now())",
                (claim_id, subject, text[:42] if subject else text[43:]),
            )
            connection.execute(
                "INSERT INTO claim_evidence (claim_id, source_span_id, evidence_role) "
                "VALUES (%s, %s, 'support')",
                (claim_id, span_id),
            )

    response = _get(f"/imports/source-documents/{document}")
    assert response.status_code == 200, response.text
    claims = response.json()["canonical_claims"]
    assert len(claims) == 2
    by_id = {claim["claim_id"]: claim for claim in claims}
    owned = by_id[str(owned_claim)]
    loose = by_id[str(loose_claim)]
    assert owned["subject_entity_id"] == str(owner)
    assert owned["subject_entity_name"] == "Vault of Ishi"
    assert loose["subject_entity_id"] is None
    assert loose["subject_entity_name"] is None
