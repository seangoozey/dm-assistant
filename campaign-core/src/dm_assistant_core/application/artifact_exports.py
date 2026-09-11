"""Deterministic derived-artifact export for canonical rules elements.

Reads an approved canonical rules-element entity and its structured mechanics, renders a
versioned Markdown card, and records a derived artifact with full provenance. The export
never mutates canonical records; regeneration of the same canonical record under the same
profile version produces the same content hash and returns the existing artifact.
"""

from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
from typing import Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from dm_assistant_core.domain.rules_elements import (
    MARKDOWN_CARD_PROFILE,
    MARKDOWN_CARD_PROFILE_VERSION,
    RulesElementMechanics,
    render_markdown_card,
)


class RulesElementRecord(BaseModel):
    """A canonical rules-element entity and its mechanics, as read for export."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    entity_id: UUID
    canonical_name: str = Field(min_length=1)
    mechanics: RulesElementMechanics


class ExportedArtifact(BaseModel):
    """The derived artifact produced by an export, with provenance."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    artifact_id: UUID
    kind: str
    format_version: str
    producer_version: str
    content_hash: str
    source_entity_id: UUID
    export_profile: str
    content: str
    created_at: datetime
    idempotent_replay: bool


class ArtifactExportError(ValueError):
    """An export request failed a deterministic safety or state rule."""


class ArtifactExportRepository(Protocol):
    """Read canonical records and persist derived artifacts without mutating canon."""

    def load_rules_element(self, entity_id: UUID) -> RulesElementRecord | None: ...

    def artifact_for_content_hash(self, content_hash: str) -> ExportedArtifact | None: ...

    def store_artifact(self, artifact: ExportedArtifact) -> ExportedArtifact: ...


class ArtifactExportService:
    """Render a deterministic Markdown card from a canonical rules element."""

    def __init__(self, repository: ArtifactExportRepository) -> None:
        self._repository = repository

    def export_rules_card(self, entity_id: UUID) -> ExportedArtifact:
        record = self._repository.load_rules_element(entity_id)
        if record is None:
            raise ArtifactExportError("rules element entity does not exist")
        content = render_markdown_card(
            canonical_name=record.canonical_name,
            rules_kind=record.mechanics.rules_kind,
            summary=record.mechanics.summary,
            mechanics=record.mechanics.mechanics,
        )
        content_hash = sha256(content.encode("utf-8")).hexdigest()
        existing = self._repository.artifact_for_content_hash(content_hash)
        if existing is not None:
            return existing.model_copy(update={"idempotent_replay": True})
        artifact = ExportedArtifact(
            artifact_id=entity_id,  # placeholder; store assigns the real UUID
            kind="rules_card",
            format_version=MARKDOWN_CARD_PROFILE_VERSION,
            producer_version=MARKDOWN_CARD_PROFILE_VERSION,
            content_hash=content_hash,
            source_entity_id=record.entity_id,
            export_profile=MARKDOWN_CARD_PROFILE,
            content=content,
            created_at=datetime.now(UTC),
            idempotent_replay=False,
        )
        return self._repository.store_artifact(artifact)
