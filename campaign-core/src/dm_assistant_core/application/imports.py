"""Application service for durable Markdown scan ingestion."""

from typing import Protocol
from uuid import UUID

from dm_assistant_core.importer import ImportReceipt, MarkdownScanBatch


class MarkdownImportRepository(Protocol):
    def ingest(self, batch: MarkdownScanBatch) -> ImportReceipt: ...

    def current_document_path(self, document_id: UUID) -> str | None: ...


class MarkdownImportService:
    def __init__(self, repository: MarkdownImportRepository) -> None:
        self._repository = repository

    def ingest(self, batch: MarkdownScanBatch) -> ImportReceipt:
        return self._repository.ingest(batch)

    def current_document_path(self, document_id: UUID) -> str | None:
        return self._repository.current_document_path(document_id)
