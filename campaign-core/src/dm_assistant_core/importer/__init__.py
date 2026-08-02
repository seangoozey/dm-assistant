"""Read-only Markdown connector and typed import contracts."""

from dm_assistant_core.importer.models import (
    CandidateAuthority,
    ImportCandidate,
    ImportClassification,
    ImportFileOutcome,
    ImportObservationReceipt,
    ImportOutcome,
    ImportReceipt,
    ImportWarning,
    MarkdownScanBatch,
    ScannedSource,
)
from dm_assistant_core.importer.scanner import (
    MarkdownScanner,
    MarkdownScannerConfig,
    SourceSafetyError,
)

__all__ = [
    "CandidateAuthority",
    "ImportCandidate",
    "ImportClassification",
    "ImportFileOutcome",
    "ImportObservationReceipt",
    "ImportOutcome",
    "ImportReceipt",
    "ImportWarning",
    "MarkdownScanBatch",
    "MarkdownScanner",
    "MarkdownScannerConfig",
    "ScannedSource",
    "SourceSafetyError",
]
