from __future__ import annotations

import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from pathlib import Path
from typing import Any

import httpx
import psycopg
import pytest

from dm_assistant_core.adapters.postgres import PostgresDatabase, PostgresMarkdownImportRepository
from dm_assistant_core.adapters.postgres.migrate import run_migrations
from dm_assistant_core.api.app import create_app
from dm_assistant_core.config import Settings
from dm_assistant_core.importer import (
    ImportOutcome,
    MarkdownScanner,
    MarkdownScannerConfig,
)
from dm_assistant_core.importer.models import ImportRejectedError

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


def scanner(
    root: Path,
    scan_id: str,
    root_identifier: str = "integration",
    parser_version: str = "markdown-parser/1.0",
    reextract_paths: tuple[str, ...] = (),
) -> MarkdownScanner:
    return MarkdownScanner(
        MarkdownScannerConfig(
            root=root,
            root_identifier=root_identifier,
            importer_version="markdown-importer/1.0",
            parser_version=parser_version,
            path_policy_version="starfall-path-policy/1.0",
            read_only=True,
            scan_id=scan_id,
            reextract_paths=reextract_paths,
        )
    )


def count(table: str) -> int:
    assert TEST_DSN is not None
    allowed = {
        "source_documents",
        "source_revisions",
        "source_extractions",
        "import_candidates",
        "import_runs",
        "import_observations",
        "review_items",
        "entities",
        "claims",
    }
    assert table in allowed
    with psycopg.connect(TEST_DSN) as connection:
        row = connection.execute(f"SELECT count(*) FROM {table}").fetchone()
    assert row is not None
    return int(row[0])


def write_location(path: Path, *, stable_id: str | None, extra: str = "") -> None:
    identifier = f"id: {stable_id}\n" if stable_id else ""
    path.write_text(
        "---\n"
        f"{identifier}"
        "name: Synthetic Reading Room\n"
        "type: location\n"
        "status: canon\n"
        "fixture: synthetic\n"
        "---\n\n"
        "## Established Facts\n\n"
        f"The room has one brass lamp and an oak desk. {extra}\n",
        encoding="utf-8",
    )


def test_fixture_scan_is_atomic_idempotent_and_noncanonical_through_http() -> None:
    assert TEST_DSN is not None
    batch = scanner(FIXTURE_ROOT, "fixture-http", "sanitized-fixture").scan()
    app = create_app(
        Settings(database_url=TEST_DSN, environment="test", run_migrations=False)
    )

    async def apply_twice() -> tuple[httpx.Response, httpx.Response]:
        transport = httpx.ASGITransport(app=app)
        payload = batch.model_dump(mode="json")
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            first = await client.post("/imports/markdown/scan", json=payload)
            retry = await client.post("/imports/markdown/scan", json=payload)
            return first, retry

    first, retry = asyncio.run(apply_twice())

    assert first.status_code == 200
    assert retry.status_code == 200
    assert first.json()["import_run_id"] == retry.json()["import_run_id"]
    assert first.json()["idempotent_replay"] is False
    assert retry.json()["idempotent_replay"] is True
    assert count("source_documents") == 17
    assert count("source_revisions") == 17
    assert count("import_candidates") == 18
    assert count("import_runs") == 1
    assert count("import_observations") == 17
    assert count("entities") == 0
    assert count("claims") == 0
    with psycopg.connect(TEST_DSN) as connection:
        row = connection.execute(
            "SELECT sr.raw_content, sr.original_path, sr.parser_version, "
            "sr.path_policy_version FROM source_revisions sr "
            "WHERE sr.original_path = 'npcs/mixed-npc.md'"
        ).fetchone()
    assert row is not None
    assert bytes(row[0]) == (FIXTURE_ROOT / "npcs" / "mixed-npc.md").read_bytes()
    assert row[1:] == (
        "npcs/mixed-npc.md",
        "markdown-parser/1.0",
        "starfall-path-policy/1.0",
    )


def test_ordinary_rescan_does_not_duplicate_open_import_reviews() -> None:
    assert TEST_DSN is not None
    repository = PostgresMarkdownImportRepository(PostgresDatabase(TEST_DSN))
    repository.ingest(scanner(FIXTURE_ROOT, "review-dedup-first").scan())
    first_review_count = count("review_items")

    second = repository.ingest(scanner(FIXTURE_ROOT, "review-dedup-second").scan())

    assert all(item.outcome is ImportOutcome.UNCHANGED for item in second.observation.files)
    assert count("review_items") == first_review_count


def test_reconciliation_handles_unchanged_changed_moved_and_missing(tmp_path: Path) -> None:
    assert TEST_DSN is not None
    root = tmp_path / "source"
    locations = root / "locations"
    locations.mkdir(parents=True)
    old_path = locations / "old-name.md"
    new_path = locations / "new-name.md"
    write_location(old_path, stable_id="synthetic-location-1")
    repository = PostgresMarkdownImportRepository(PostgresDatabase(TEST_DSN))

    initial = repository.ingest(scanner(root, "initial").scan())
    unchanged = repository.ingest(scanner(root, "unchanged").scan())
    old_path.rename(new_path)
    moved = repository.ingest(scanner(root, "moved").scan())
    write_location(new_path, stable_id="synthetic-location-1", extra="A map is displayed.")
    changed = repository.ingest(scanner(root, "changed").scan())
    new_path.unlink()
    missing = repository.ingest(scanner(root, "missing").scan())

    assert initial.observation.files[0].outcome is ImportOutcome.NEW
    assert unchanged.observation.files[0].outcome is ImportOutcome.UNCHANGED
    assert moved.observation.files[0].outcome is ImportOutcome.MOVED
    assert changed.observation.files[0].outcome is ImportOutcome.CHANGED
    assert missing.observation.files[0].outcome is ImportOutcome.MISSING_SOURCE
    assert count("source_documents") == 1
    assert count("source_revisions") == 2
    assert count("import_candidates") == 2
    assert count("claims") == 0
    with psycopg.connect(TEST_DSN) as connection:
        paths = connection.execute(
            "SELECT normalized_path FROM source_document_paths ORDER BY normalized_path"
        ).fetchall()
    assert paths == [("locations/new-name.md",), ("locations/old-name.md",)]


def test_parser_upgrade_reextracts_unchanged_bytes_without_reusing_changed_disposition(
    tmp_path: Path,
) -> None:
    assert TEST_DSN is not None
    root = tmp_path / "source"
    gm = root / "gm"
    gm.mkdir(parents=True)
    (gm / "campaign-bible.md").write_text(
        "# Synthetic Planning Notebook\n\n"
        "## Planning Areas\n\n"
        "### Possible Branch\n\nOne synthetic branch remains optional.\n\n"
        "### Prepared Pressure\n\nOffer one synthetic complication.\n\n"
        "### Current Intentions\n\nThe synthetic guild intends to ask a question.\n",
        encoding="utf-8",
    )
    repository = PostgresMarkdownImportRepository(PostgresDatabase(TEST_DSN))
    initial_batch = scanner(root, "parser-v1").scan()
    source = initial_batch.files[0]
    first = source.candidates[0]
    last = source.candidates[-1]
    combined = source.content.decode("utf-8")[first.start_offset : last.end_offset].strip()
    legacy = first.model_copy(
        update={
            "fingerprint": sha256(b"synthetic-legacy-combined-candidate").hexdigest(),
            "section": "Planning Areas",
            "assertion_text": combined,
            "start_offset": first.start_offset,
            "end_offset": last.end_offset,
        }
    )
    initial_batch = initial_batch.model_copy(
        update={"files": (source.model_copy(update={"candidates": (legacy,)}),)}
    )

    initial = repository.ingest(initial_batch)
    legacy_id = initial.observation.files[0].candidate_ids[0]
    with psycopg.connect(TEST_DSN) as connection:
        connection.execute(
            "UPDATE import_candidates SET review_status='deferred' WHERE id=%s",
            (legacy_id,),
        )
        connection.execute(
            "INSERT INTO candidate_dispositions "
            "(id, candidate_id, disposition, reason, created_at) "
            "VALUES (gen_random_uuid(), %s, 'deferred', 'Synthetic parser audit.', now())",
            (legacy_id,),
        )

    upgraded_batch = scanner(
        root,
        "parser-v2",
        parser_version="markdown-parser/2.0",
        reextract_paths=("gm/campaign-bible.md",),
    ).scan()
    upgraded = repository.ingest(upgraded_batch)
    ordinary_retry = repository.ingest(
        scanner(root, "parser-v2-ordinary", parser_version="markdown-parser/2.0").scan()
    )
    exact_retry = repository.ingest(upgraded_batch)

    assert upgraded.observation.files[0].outcome is ImportOutcome.REEXTRACTED
    assert ordinary_retry.observation.files[0].outcome is ImportOutcome.UNCHANGED
    assert exact_retry.import_run_id == upgraded.import_run_id
    assert exact_retry.idempotent_replay is True
    assert count("source_revisions") == 1
    assert count("source_extractions") == 2
    assert count("import_candidates") == 4
    with psycopg.connect(TEST_DSN) as connection:
        legacy_row = connection.execute(
            "SELECT status, review_status, "
            "(SELECT count(*) FROM candidate_dispositions WHERE candidate_id=%s) "
            "FROM import_candidates WHERE id=%s",
            (legacy_id, legacy_id),
        ).fetchone()
        active_rows = connection.execute(
            "SELECT status, review_status, extractor_version FROM import_candidates "
            "WHERE id<>%s ORDER BY assertion_text",
            (legacy_id,),
        ).fetchall()
    assert legacy_row == ("source_removed", "deferred", 1)
    assert active_rows == [
        ("active", "pending", "markdown-parser/2.0"),
        ("active", "pending", "markdown-parser/2.0"),
        ("active", "pending", "markdown-parser/2.0"),
    ]


def test_parser_upgrade_only_reextracts_explicit_paths(tmp_path: Path) -> None:
    assert TEST_DSN is not None
    root = tmp_path / "source"
    locations = root / "locations"
    locations.mkdir(parents=True)
    write_location(locations / "selected.md", stable_id="synthetic-selected")
    write_location(locations / "untouched.md", stable_id="synthetic-untouched")
    repository = PostgresMarkdownImportRepository(PostgresDatabase(TEST_DSN))
    repository.ingest(scanner(root, "scope-v1").scan())

    upgraded = repository.ingest(
        scanner(
            root,
            "scope-v2",
            parser_version="markdown-parser/2.0",
            reextract_paths=("locations/selected.md",),
        ).scan()
    )

    outcomes = {item.path: item.outcome for item in upgraded.observation.files}
    assert outcomes == {
        "locations/selected.md": ImportOutcome.REEXTRACTED,
        "locations/untouched.md": ImportOutcome.UNCHANGED,
    }
    with psycopg.connect(TEST_DSN) as connection:
        extraction_counts = dict(
            connection.execute(
                "SELECT sp.normalized_path, count(se.parser_version) "
                "FROM source_document_paths sp "
                "JOIN source_revisions sr ON sr.source_document_id=sp.source_document_id "
                "JOIN source_extractions se ON se.source_revision_id=sr.id "
                "GROUP BY sp.normalized_path ORDER BY sp.normalized_path"
            ).fetchall()
        )
    assert extraction_counts == {
        "locations/selected.md": 2,
        "locations/untouched.md": 1,
    }


def test_ambiguous_different_hash_move_creates_review_without_merge(tmp_path: Path) -> None:
    assert TEST_DSN is not None
    root = tmp_path / "source"
    locations = root / "locations"
    locations.mkdir(parents=True)
    old_path = locations / "old-name.md"
    new_path = locations / "new-name.md"
    write_location(old_path, stable_id=None)
    repository = PostgresMarkdownImportRepository(PostgresDatabase(TEST_DSN))
    repository.ingest(scanner(root, "possible-initial").scan())
    old_path.unlink()
    write_location(new_path, stable_id=None, extra="A small map is displayed.")

    receipt = repository.ingest(scanner(root, "possible-move").scan())

    file_outcome = next(
        item for item in receipt.observation.files if item.path == "locations/new-name.md"
    )
    assert file_outcome.outcome is ImportOutcome.POSSIBLE_MOVE
    assert file_outcome.review_ids
    assert count("source_documents") == 2
    assert count("claims") == 0


def test_tampered_batch_rolls_back_before_any_receipt() -> None:
    assert TEST_DSN is not None
    batch = scanner(FIXTURE_ROOT, "tampered").scan()
    first = batch.files[0].model_copy(update={"content_hash": "f" * 64})
    tampered = batch.model_copy(update={"files": (first, *batch.files[1:])})
    repository = PostgresMarkdownImportRepository(PostgresDatabase(TEST_DSN))

    with pytest.raises(ImportRejectedError, match="content hash mismatch"):
        repository.ingest(tampered)

    assert count("source_documents") == 0
    assert count("source_revisions") == 0
    assert count("import_runs") == 0


def test_concurrent_retry_creates_one_import_run() -> None:
    assert TEST_DSN is not None
    batch = scanner(FIXTURE_ROOT, "concurrent").scan()

    def ingest() -> Any:
        repository = PostgresMarkdownImportRepository(PostgresDatabase(TEST_DSN))
        return repository.ingest(batch)

    with ThreadPoolExecutor(max_workers=2) as pool:
        receipts = tuple(pool.map(lambda _: ingest(), range(2)))

    assert receipts[0].import_run_id == receipts[1].import_run_id
    assert {receipt.idempotent_replay for receipt in receipts} == {False, True}
    assert count("import_runs") == 1
    assert count("source_revisions") == 17
