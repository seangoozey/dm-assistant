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

# Offered values = (code-seeded baseline ∪ stored rows) − stored-retired —
# the same merge TemplateVocabularyService.values() applies, so the audit
# judges against exactly what Settings and the editor dropdowns offer.
from dm_assistant_core.application.template_vocabularies import VOCABULARIES

_VOCABULARY_SQL = """
SELECT vocabulary, value, retired FROM template_vocabularies
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
        stored: dict[str, dict[str, bool]] = {}
        for vocabulary, value, retired in rows:
            stored.setdefault(str(vocabulary), {})[str(value)] = bool(retired)
        values: dict[str, set[str]] = {}
        for vocabulary, seeds in VOCABULARIES.items():
            merged = {value: False for value in seeds}
            merged.update(stored.get(vocabulary, {}))
            offered = {value for value, retired in merged.items() if not retired}
            values[vocabulary] = offered
        for vocabulary, overrides in stored.items():
            if vocabulary in values:
                continue
            values[vocabulary] = {
                value for value, retired in overrides.items() if not retired
            }
        return values

    def ownership_counts(self) -> tuple[int, int]:
        with self._database.connection() as connection:
            orphaned = connection.execute(
                """
                SELECT count(*) FROM claims c
                WHERE c.subject_entity_id IS NULL
                  AND NOT EXISTS (SELECT 1 FROM claim_supersessions cs
                                  WHERE cs.superseded_claim_id = c.id)
                  AND NOT EXISTS (SELECT 1 FROM claim_owner_dispositions cod
                                  WHERE cod.claim_id = c.id)
                """
            ).fetchone()[0]
            disposed = connection.execute(
                "SELECT count(*) FROM claim_owner_dispositions"
            ).fetchone()[0]
            return int(orphaned), int(disposed)

    def unminted_attribute_profiles(self) -> int:
        with self._database.connection() as connection:
            return int(connection.execute(
                """
                SELECT count(*) FROM entity_profiles ep
                WHERE ep.profile_json ?| array['race','sex','status','location_type',
                                               'parent_location','base_location','life_status']
                  AND NOT EXISTS (SELECT 1 FROM attribute_claim_bindings b
                                  WHERE b.entity_id = ep.entity_id)
                """
            ).fetchone()[0])
