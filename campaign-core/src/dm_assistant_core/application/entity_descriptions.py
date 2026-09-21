"""Entity description authoring (TKT-0111, ADR-0015 layer 2).

A description is DM-authored prose filed as an evidence-class direct-input
document whose path slug exactly names the entity — the page matcher's
exact-name rule then adopts it as the entry's page, clearing the no-page
marker. The gathered zone records claim-ID references in frontmatter: the
description references the record; it never duplicates it.
"""

from datetime import UTC, datetime
from hashlib import sha256
from re import sub as resub
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from dm_assistant_core.importer.models import (
    ImportClassification,
    ImportOutcome,
    MarkdownScanBatch,
    ScannedSource,
)


class EntityDescriptionCommand(BaseModel):
    """File DM-authored prose as an entity's description document."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    entity_id: UUID
    text: str = Field(min_length=1)
    referenced_claim_ids: tuple[UUID, ...] = ()
    idempotency_key: str = Field(min_length=1)
    document_id: UUID | None = None  # set when revising an existing description


class EntityDescriptionReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    entity_id: UUID
    document_id: UUID
    revision_id: UUID
    path: str
    idempotent_replay: bool


class EntityDescriptionService:
    def __init__(self, imports, entities) -> None:
        self._imports = imports
        self._entities = entities

    def write(self, command: EntityDescriptionCommand) -> EntityDescriptionReceipt:
        entity = self._entities.get(command.entity_id)
        if entity is None:
            raise ValueError("no identity matches that entity")
        name = entity.canonical_name
        now = datetime.now(UTC)
        content = command.text.strip().encode("utf-8")
        slug = resub(r"[^a-z0-9]+", "-", name.casefold()).strip("-") or "entity"
        # Revisions file at the same canonical path: the importer keys
        # documents by path and appends a new source_revision when content
        # differs, so the page matcher's exact-name rule keeps pointing at
        # the latest text while superseded prose stays in revision history.
        path = f"entities/{slug}.md"
        if command.document_id is not None and (
            self._imports.current_document_path(command.document_id) != path
        ):
            # A rename moves the canonical path; a "revision" filed there
            # would fork into a second page document. Write fresh instead.
            raise ValueError(
                "that document is no longer this entity's page path — "
                "file a new description rather than a revision"
            )
        source = ScannedSource(
            path=path,
            content_hash=sha256(content).hexdigest(),
            content=content,
            filesystem_modified_at=now,
            external_id=str(uuid4()),
            canonical_name=name,
            frontmatter={
                "type": "entity-description",
                "name": name,
                "entity_id": str(command.entity_id),
                "capture_mode": "direct_input",
                "referenced_claims": [str(claim) for claim in command.referenced_claim_ids],
                "written_at": now.isoformat(),
            },
            classification=ImportClassification.DURABLE_EVIDENCE,
            proposed_outcome=ImportOutcome.NEW,
            candidates=(),
            entity_candidates=0,
            warnings=(),
        )
        receipt = self._imports.ingest(
            MarkdownScanBatch(
                root_identifier=f"direct-input:entity-description:{command.entity_id}",
                snapshot_at=now,
                importer_version="direct-input/entity-description-v1",
                parser_version="direct-input/entity-description-v1",
                path_policy_version="direct-input/entity-description-v1",
                idempotency_key=command.idempotency_key,
                excluded_paths_encountered=(),
                files=(source,),
            )
        )
        outcome = receipt.observation.files[0]
        if not outcome.source_document_id or not outcome.source_revision_id:
            raise ValueError("the description document could not be filed")
        return EntityDescriptionReceipt(
            entity_id=command.entity_id,
            document_id=outcome.source_document_id,
            revision_id=outcome.source_revision_id,
            path=path,
            idempotent_replay=bool(receipt.idempotent_replay),
        )
