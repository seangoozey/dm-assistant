"""PostgreSQL repository for reading canonical rules elements and storing export artifacts."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from dm_assistant_core.adapters.postgres.database import PostgresDatabase
from dm_assistant_core.application.artifact_exports import (
    ArtifactExportRepository,
    ExportedArtifact,
    RulesElementRecord,
)
from dm_assistant_core.domain.rules_elements import RulesElementMechanics, RulesKind

#: The kind_definitions IDs seeded in migration 0010.
_RULES_CARD_ARTIFACT_KIND_ID = UUID("40000000-0000-0000-0000-000000000007")
_MARKDOWN_CARD_PROFILE_KIND_ID = UUID("70000000-0000-0000-0000-000000000001")


class PostgresArtifactExportRepository(ArtifactExportRepository):
    """Read canonical rules elements and persist derived artifacts transactionally."""

    def __init__(self, database: PostgresDatabase) -> None:
        self._database = database

    def load_rules_element(self, entity_id: UUID) -> RulesElementRecord | None:
        with self._database.connection() as connection:
            row = connection.execute(
                """
                SELECT e.id, e.canonical_name, rem.rules_kind, rem.summary, rem.mechanics_jsonb
                  FROM entities e
                  JOIN rules_element_mechanics rem ON rem.entity_id = e.id
                 WHERE e.id = %s AND e.entity_type = 'rules_element'
                """,
                (entity_id,),
            ).fetchone()
        if row is None:
            return None
        mechanics = RulesElementMechanics(
            rules_kind=RulesKind(str(row[2])),
            summary=str(row[3]),
            mechanics=dict(row[4]) if row[4] else {},
        )
        return RulesElementRecord(
            entity_id=row[0],
            canonical_name=str(row[1]),
            mechanics=mechanics,
        )

    def artifact_for_content_hash(self, content_hash: str) -> ExportedArtifact | None:
        with self._database.connection() as connection:
            row = connection.execute(
                """
                SELECT da.id, da.kind::text, da.format_version, da.producer_version,
                       da.content_hash, ai.entity_id, da.created_at, da.location
                  FROM derived_artifacts da
                  JOIN artifact_inputs ai ON ai.artifact_id = da.id
                 WHERE da.content_hash = %s AND da.kind = 'rules_card'
                 LIMIT 1
                """,
                (content_hash,),
            ).fetchone()
        if row is None:
            return None
        return ExportedArtifact(
            artifact_id=row[0],
            kind=str(row[1]),
            format_version=str(row[2]),
            producer_version=str(row[3]),
            content_hash=str(row[4]),
            source_entity_id=row[5],
            export_profile="markdown_card",
            content=str(row[7]),
            created_at=row[6],
            idempotent_replay=False,
        )

    def store_artifact(self, artifact: ExportedArtifact) -> ExportedArtifact:
        artifact_id = uuid4()
        now = datetime.now(UTC)
        with self._database.connection() as connection:
            connection.execute(
                """
                INSERT INTO derived_artifacts (
                    id, kind, format_version, content_hash, location, created_at,
                    producer_version, export_profile_kind_id
                ) VALUES (%s, 'rules_card', %s, %s, %s, %s, %s, %s)
                """,
                (
                    artifact_id,
                    artifact.format_version,
                    artifact.content_hash,
                    f"rules-card:{artifact.content_hash[:12]}",
                    now,
                    artifact.producer_version,
                    _MARKDOWN_CARD_PROFILE_KIND_ID,
                ),
            )
            connection.execute(
                """
                INSERT INTO artifact_inputs (artifact_id, entity_id)
                VALUES (%s, %s)
                """,
                (artifact_id, artifact.source_entity_id),
            )
        return artifact.model_copy(
            update={"artifact_id": artifact_id, "created_at": now, "idempotent_replay": False}
        )
