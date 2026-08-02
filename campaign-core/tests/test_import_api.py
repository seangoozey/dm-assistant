import asyncio
from pathlib import Path
from uuid import UUID

import httpx

from dm_assistant_core.api.app import create_app
from dm_assistant_core.application import MarkdownImportService
from dm_assistant_core.config import Settings
from dm_assistant_core.importer import (
    ImportObservationReceipt,
    ImportReceipt,
    MarkdownScanBatch,
    MarkdownScanner,
    MarkdownScannerConfig,
)
from dm_assistant_core.importer.models import ImportRejectedError

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = REPOSITORY_ROOT / "tests" / "fixtures" / "markdown_import"
RUN_ID = UUID("90000000-0000-0000-0000-000000000001")


class RecordingImportRepository:
    def __init__(self, reject: bool = False) -> None:
        self.batch: MarkdownScanBatch | None = None
        self.reject = reject

    def ingest(self, batch: MarkdownScanBatch) -> ImportReceipt:
        self.batch = batch
        if self.reject:
            raise ImportRejectedError("content hash mismatch")
        return ImportReceipt(
            import_run_id=RUN_ID,
            idempotency_key=batch.idempotency_key,
            root_identifier=batch.root_identifier,
            snapshot_at=batch.snapshot_at,
            importer_version=batch.importer_version,
            parser_version=batch.parser_version,
            path_policy_version=batch.path_policy_version,
            outcome="completed",
            observation=ImportObservationReceipt(
                admitted_file_count=len(batch.files),
                excluded_paths_encountered=batch.excluded_paths_encountered,
                files=(),
            ),
            idempotent_replay=False,
        )


def fixture_batch() -> MarkdownScanBatch:
    return MarkdownScanner(
        MarkdownScannerConfig(
            root=FIXTURE_ROOT,
            root_identifier="sanitized-fixture",
            importer_version="markdown-importer/1.0",
            parser_version="markdown-parser/1.0",
            path_policy_version="starfall-path-policy/1.0",
            read_only=True,
            scan_id="api-contract",
        )
    ).scan()


def settings() -> Settings:
    return Settings(
        database_url="postgresql://campaign:secret@localhost:5432/campaign",
        run_migrations=False,
    )


def test_import_api_preserves_the_exact_typed_batch() -> None:
    repository = RecordingImportRepository()
    batch = fixture_batch()
    app = create_app(settings(), imports=MarkdownImportService(repository))

    async def request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post(
                "/imports/markdown/scan",
                json=batch.model_dump(mode="json"),
            )

    response = asyncio.run(request())

    assert response.status_code == 200
    assert repository.batch == batch
    assert response.json()["import_run_id"] == str(RUN_ID)
    assert response.json()["observation"]["admitted_file_count"] == 17


def test_import_api_maps_integrity_rejection_to_conflict() -> None:
    batch = fixture_batch()
    app = create_app(
        settings(),
        imports=MarkdownImportService(RecordingImportRepository(reject=True)),
    )

    async def request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post(
                "/imports/markdown/scan", json=batch.model_dump(mode="json")
            )

    response = asyncio.run(request())

    assert response.status_code == 409
    assert response.json() == {"detail": "content hash mismatch"}
