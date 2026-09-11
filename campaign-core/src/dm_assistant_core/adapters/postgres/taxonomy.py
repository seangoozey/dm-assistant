"""PostgreSQL reader for controlled kinds and tags."""

from dm_assistant_core.adapters.postgres.database import PostgresDatabase
from dm_assistant_core.application.taxonomy import TaxonomySnapshot
from dm_assistant_core.domain import EntityKind, EntityKindGuidance, PlanKind, PlanKindGuidance


class PostgresTaxonomyRepository:
    def __init__(self, database: PostgresDatabase) -> None:
        self._database = database

    def snapshot(self) -> TaxonomySnapshot:
        with self._database.connection() as connection:
            kind_rows = connection.execute(
                """
                SELECT kd.canonical_key, kv.label, kv.description
                FROM kind_definitions kd
                JOIN LATERAL (
                    SELECT label, description
                    FROM kind_versions
                    WHERE kind_id = kd.id
                    ORDER BY version DESC
                    LIMIT 1
                ) kv ON true
                WHERE kd.namespace = 'entity' AND kd.status = 'active'
                ORDER BY kd.canonical_key
                """
            ).fetchall()
            tag_rows = connection.execute(
                "SELECT normalized_name FROM tags ORDER BY normalized_name"
            ).fetchall()
            plan_rows = connection.execute(
                """
                SELECT kd.canonical_key, kv.label, kv.description
                FROM kind_definitions kd
                JOIN LATERAL (
                    SELECT label, description FROM kind_versions
                    WHERE kind_id = kd.id ORDER BY version DESC LIMIT 1
                ) kv ON true
                WHERE kd.namespace = 'plan' AND kd.status = 'active'
                ORDER BY kd.canonical_key
                """
            ).fetchall()
        return TaxonomySnapshot(
            entity_kinds=tuple(
                EntityKindGuidance(
                    kind=EntityKind(str(row[0])), label=str(row[1]), description=str(row[2])
                )
                for row in kind_rows
            ),
            plan_kinds=tuple(
                PlanKindGuidance(
                    kind=PlanKind(str(row[0])), label=str(row[1]), description=str(row[2])
                )
                for row in plan_rows
            ),
            tags=tuple(str(row[0]) for row in tag_rows),
        )
