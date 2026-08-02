from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

import httpx
import psycopg
import pytest

from dm_assistant_core.adapters.postgres.migrate import run_migrations
from dm_assistant_core.api.app import create_app
from dm_assistant_core.config import Settings
from dm_assistant_core.importer import MarkdownScanner, MarkdownScannerConfig

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = REPOSITORY_ROOT / "tests" / "fixtures" / "markdown_import"
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


def fixture_batch() -> Any:
    return MarkdownScanner(
        MarkdownScannerConfig(
            root=FIXTURE_ROOT,
            root_identifier="sanitized-review-fixture",
            importer_version="markdown-importer/1.0",
            parser_version="markdown-parser/1.0",
            path_policy_version="starfall-path-policy/1.0",
            read_only=True,
            scan_id="import-review-read-api",
        )
    ).scan()


def database_snapshot() -> tuple[Any, ...]:
    assert TEST_DSN is not None
    with psycopg.connect(TEST_DSN) as connection:
        row = connection.execute(
            "SELECT "
            "(SELECT count(*) FROM entities), "
            "(SELECT count(*) FROM claims), "
            "(SELECT count(*) FROM relationships), "
            "(SELECT count(*) FROM import_runs), "
            "(SELECT count(*) FROM import_candidates), "
            "(SELECT count(*) FROM review_items), "
            "(SELECT coalesce(string_agg(id::text || ':' || status, ',' ORDER BY id), '') "
            " FROM review_items)"
        ).fetchone()
    assert row is not None
    return row


def test_import_review_reads_real_persisted_evidence_without_mutation() -> None:
    assert TEST_DSN is not None
    app = create_app(Settings(database_url=TEST_DSN, environment="test", run_migrations=False))
    batch = fixture_batch()

    async def exercise() -> tuple[tuple[Any, ...], dict[str, httpx.Response]]:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            imported = await client.post(
                "/imports/markdown/scan", json=batch.model_dump(mode="json")
            )
            run_id = imported.json()["import_run_id"]
            with psycopg.connect(TEST_DSN) as connection:
                connection.execute(
                    "UPDATE import_candidates SET visibility = 'party' WHERE id = "
                    "(SELECT id FROM import_candidates ORDER BY id LIMIT 1)"
                )
                connection.execute(
                    "UPDATE review_items SET status = 'superseded' WHERE id = "
                    "(SELECT id FROM review_items ORDER BY id LIMIT 1)"
                )
            before_reads = database_snapshot()
            responses = {
                "runs": await client.get("/imports/runs?requester_role=dm&limit=10"),
                "run": await client.get(f"/imports/runs/{run_id}?requester_role=dm"),
                "first": await client.get(
                    f"/imports/candidates?requester_role=dm&run_id={run_id}&limit=2"
                ),
                "second": await client.get(
                    f"/imports/candidates?requester_role=dm&run_id={run_id}&limit=2&offset=2"
                ),
                "source": await client.get(
                    "/imports/candidates?requester_role=dm&source=npcs&limit=100"
                ),
                "party": await client.get(
                    "/imports/candidates?requester_role=party&limit=100"
                ),
                "reviews": await client.get(
                    f"/imports/reviews?requester_role=dm&run_id={run_id}&limit=100"
                ),
                "superseded": await client.get(
                    "/imports/reviews?requester_role=dm&status=superseded&limit=100"
                ),
                "quarantine": await client.get(
                    "/imports/reviews?requester_role=dm&kind=import_quarantine&limit=100"
                ),
            }
            candidate_id = responses["first"].json()["items"][0]["candidate_id"]
            responses["candidate"] = await client.get(
                f"/imports/candidates/{candidate_id}?requester_role=dm"
            )
            return before_reads, responses

    before_reads, responses = asyncio.run(exercise())

    for response in responses.values():
        assert response.status_code == 200
    runs = responses["runs"].json()
    assert runs["total"] == 1
    assert runs["items"][0]["admitted_file_count"] == 17
    assert runs["items"][0]["candidate_count"] == 18
    assert responses["run"].json()["receipt"]["observation"]["admitted_file_count"] == 17

    first_ids = {item["candidate_id"] for item in responses["first"].json()["items"]}
    second_ids = {item["candidate_id"] for item in responses["second"].json()["items"]}
    assert len(first_ids) == 2
    assert len(second_ids) == 2
    assert first_ids.isdisjoint(second_ids)
    assert responses["first"].json()["total"] == 18

    source_items = responses["source"].json()["items"]
    assert source_items
    assert all("npcs" in item["evidence"][0]["source_path"] for item in source_items)
    party_items = responses["party"].json()["items"]
    assert len(party_items) == 1
    assert party_items[0]["visibility"] == "party"

    candidate = responses["candidate"].json()
    assert candidate["assertion_text"] in candidate["evidence"][0]["excerpt"]
    assert len(candidate["evidence"][0]["content_hash"]) == 64
    assert candidate["evidence"][0]["start_offset"] < candidate["evidence"][0]["end_offset"]

    reviews = responses["reviews"].json()
    assert reviews["total"] > 0
    assert all(item["status"] != "superseded" for item in reviews["items"])
    superseded = responses["superseded"].json()
    assert superseded["total"] == 1
    assert superseded["items"][0]["status"] == "superseded"
    assert {item["kind"] for item in reviews["items"]} >= {"import_quarantine"}
    quarantine = responses["quarantine"].json()
    assert quarantine["total"] > 0
    assert all(item["classification"] == "quarantine" for item in quarantine["items"])

    assert database_snapshot() == before_reads
