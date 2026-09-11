"""PostgreSQL entity identity lookup."""

from dm_assistant_core.adapters.postgres.database import PostgresDatabase
from dm_assistant_core.application.entity_lookup import EntityIdentity
from dm_assistant_core.domain import EntityKind


class PostgresEntityLookupRepository:
    def __init__(self, database: PostgresDatabase) -> None:
        self._database = database

    def search(self, name: str, limit: int) -> tuple[EntityIdentity, ...]:
        with self._database.connection() as connection:
            rows = connection.execute(
                """
                WITH matches AS (
                    SELECT e.id, e.canonical_name, e.entity_type,
                           CASE WHEN lower(e.canonical_name) = lower(%s)
                                THEN 'canonical' ELSE 'partial' END AS match_kind,
                           e.canonical_name AS matched_name,
                           CASE WHEN lower(e.canonical_name) = lower(%s) THEN 0 ELSE 2 END AS rank
                    FROM entities e
                    WHERE lower(e.canonical_name) = lower(%s) OR e.canonical_name ILIKE %s
                    UNION ALL
                    SELECT e.id, e.canonical_name, e.entity_type, 'alias', a.alias, 1
                    FROM entity_aliases a
                    JOIN entities e ON e.id = a.entity_id
                    WHERE lower(a.normalized_alias) = lower(%s) OR lower(a.alias) = lower(%s)
                )
                SELECT id, canonical_name, entity_type, match_kind, matched_name
                FROM (
                    SELECT DISTINCT ON (id) id, canonical_name, entity_type,
                           match_kind, matched_name, rank
                    FROM matches
                    ORDER BY id, rank
                ) resolved
                ORDER BY rank, length(canonical_name), lower(canonical_name), id
                LIMIT %s
                """,
                (name, name, name, f"%{name}%", name.casefold(), name, limit),
            ).fetchall()
        return tuple(
            EntityIdentity(
                entity_id=row[0],
                canonical_name=str(row[1]),
                entity_kind=EntityKind(str(row[2])),
                match_kind=row[3],
                matched_name=str(row[4]),
            )
            for row in rows
        )
