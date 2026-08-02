"""Application service for durable Markdown scan ingestion."""

from typing import Protocol

from dm_assistant_core.importer import ImportReceipt, MarkdownScanBatch


class MarkdownImportRepository(Protocol):
    def ingest(self, batch: MarkdownScanBatch) -> ImportReceipt: ...


class MarkdownImportService:
    def __init__(self, repository: MarkdownImportRepository) -> None:
        self._repository = repository

    def ingest(self, batch: MarkdownScanBatch) -> ImportReceipt:
        return self._repository.ingest(batch)
