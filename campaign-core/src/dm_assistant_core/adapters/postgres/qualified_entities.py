"""PostgreSQL reads for the Qualified Entity audit (TKT-0139)."""

from __future__ import annotations

from typing import Any

from dm_assistant_core.adapters.postgres.database import PostgresDatabase

_ENTITY_ROWS_SQL = """
SELECT e.id, e.canonical_name, e.entity_type::text,
       (SELECT count(*) FROM claims c
        WHERE c.subject_entity_id = e.id
          AND NOT EXISTS (SELECT 1 FROM claim_supersessions cs
                          WHERE cs.superseded_claim_id = c.id)) AS current_claims,
       parent.canonical_name, parent.entity_type::text, ep.profile_json
FROM entities e
LEFT JOIN LATERAL (
    SELECT profile_json FROM entity_profiles
    WHERE entity_id = e.id
    ORDER BY version DESC LIMIT 1
) ep ON true
LEFT JOIN entities parent ON lower(parent.canonical_name) = lower(btrim(ep.profile_json->>'parent_location'))
"""

_VOCABULARY_SQL = """
SELECT vocabulary, value FROM template_vocabularies
WHERE retired = false
"""


class PostgresQualifiedAuditRepository:
    def __init__(self, database: PostgresDatabase) -> None:
        self._database = database

    def entity_rows(self) -> list[tuple[Any, ...]]:
        with self._database.connection() as connection:
            return [
                tuple(row)
                for row in connection.execute(_ENTITY_ROWS_SQL).fetchall()
            ]

    def active_vocabulary_values(self) -> dict[str, set[str]]:
        with self._database.connection() as connection:
            rows = connection.execute(_VOCABULARY_SQL).fetchall()
        values: dict[str, set[str]] = {}
        for vocabulary, value in rows:
            values.setdefault(str(vocabulary), set()).add(str(value))
        return values
