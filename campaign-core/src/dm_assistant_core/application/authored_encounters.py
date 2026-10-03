"""Authored encounter documents (ADR-0021 follow-up, 2026-09-28).

An encounter is a table event — and per ADR-0021 encounters are Entities
(kind ``encounter``). The DM authors encounter material freely: this service
files an AUTHORED document as the encounter's record, with no statement
extraction — claims from encounter material are owned by the encounter once
the encounter-entity mechanism lands (TKT-0138's encounter slice), so v1
deliberately creates no candidates and therefore no new orphaned claims
(the 0148 guardrail philosophy: nothing enters canon ownerless by omission).

Session-independent by design (user ruling 2026-09-28: "the + in the library
should give access to the encounter creator, regardless of whether or not
there's an open session") — the document simply exists; a live session may
attach to it later through the existing encounter lifecycle.
"""

import re
from datetime import UTC, datetime
from hashlib import sha256
from typing import Protocol
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from dm_assistant_core.application.imports import MarkdownImportService
from dm_assistant_core.importer import (
    ImportCandidate,
    ImportClassification,
    ImportOutcome,
    MarkdownScanBatch,
    ScannedSource,
)


class EncounterDocumentCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1)
    capture_id: UUID | None = None
    idempotency_key: str = Field(min_length=1)


class EncounterDocumentReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    capture_id: UUID
    document_id: UUID
    revision_id: UUID
    path: str
    idempotent_replay: bool


class EncounterDocumentRepository(Protocol):
    def ingest(self, batch: MarkdownScanBatch) -> object: ...


class EncounterDocumentService:
    def __init__(self, imports: MarkdownImportService) -> None:
        self._imports = imports

    def write(self, command: EncounterDocumentCommand) -> EncounterDocumentReceipt:
        now = datetime.now(UTC)
        capture_id = command.capture_id or uuid4()
        title = command.title.strip()
        body = command.body.strip()
        if not title or not body:
            raise ValueError("an encounter needs a title and body")
        content = body.encode("utf-8")
        slug = re.sub(r"[^a-z0-9]+", "-", title.casefold()).strip("-") or "encounter"
        path = f"encounters/{slug}-{str(capture_id)[:8]}"
        source = ScannedSource(
            path=path,
            content_hash=sha256(content).hexdigest(),
            content=content,
            filesystem_modified_at=now,
            external_id=str(capture_id),
            canonical_name=title,
            frontmatter={
                "type": "encounter",
                "name": title,
                "capture_mode": "direct_input",
            },
            classification=ImportClassification.REAL_PLAY_EVIDENCE,
            proposed_outcome=ImportOutcome.NEW,
            # Authored evidence only — no statement extraction. Claims from
            # encounter material promote through reviewed surfaces and are
            # owned by the encounter (ADR-0021) once that mechanism lands.
            candidates=tuple(),
            entity_candidates=0,
            warnings=(),
        )
        receipt = self._imports.ingest(
            MarkdownScanBatch(
                root_identifier=f"direct-input:encounter:{capture_id}",
                snapshot_at=now,
                importer_version="direct-input/encounter-v1",
                parser_version="direct-input/encounter-v1",
                path_policy_version="direct-input/encounter-v1",
                idempotency_key=command.idempotency_key,
                excluded_paths_encountered=(),
                files=(source,),
            )
        )
        observation = receipt.observation.files[0]  # type: ignore[attr-defined]
        if not observation.source_document_id or not observation.source_revision_id:
            raise RuntimeError("the encounter document was not filed")
        _ = ImportCandidate  # kept for import parity; extraction is deliberately absent
        return EncounterDocumentReceipt(
            capture_id=capture_id,
            document_id=observation.source_document_id,
            revision_id=observation.source_revision_id,
            path=path,
            idempotent_replay=receipt.idempotent_replay,  # type: ignore[attr-defined]
        )
