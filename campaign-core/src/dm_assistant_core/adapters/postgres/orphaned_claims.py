"""PostgreSQL reads for the orphaned-claims review (TKT-0138)."""

from __future__ import annotations

from typing import Any

from dm_assistant_core.adapters.postgres.database import PostgresDatabase

# Current subject-less claims with their evidence document paths (capped).
_ORPHANS_SQL = """
SELECT c.id, c.assertion_text, c.state::text, c.authority::text,
       to_char(c.recorded_at, 'YYYY-MM-DD') AS recorded_day,
       (array_agg(DISTINCT p.normalized_path) FILTER (WHERE p.normalized_path IS NOT NULL))[1:3] AS paths
FROM claims c
LEFT JOIN claim_evidence ce ON ce.claim_id = c.id
LEFT JOIN source_spans ss ON ss.id = ce.source_span_id
LEFT JOIN source_revisions sr ON sr.id = ss.source_revision_id
LEFT JOIN source_documents sd ON sd.id = sr.source_document_id
LEFT JOIN source_document_paths p ON p.source_document_id = sd.id AND p.is_current
WHERE c.subject_entity_id IS NULL
  AND NOT EXISTS (SELECT 1 FROM claim_supersessions cs WHERE cs.superseded_claim_id = c.id)
  AND NOT EXISTS (SELECT 1 FROM claim_owner_dispositions cod WHERE cod.claim_id = c.id)
GROUP BY c.id, c.assertion_text, c.state, c.authority, c.recorded_at
ORDER BY c.assertion_text
"""

# Co-mention links (the importer's word-boundary linking + direct-capture
# mentions) on exactly the orphaned claims — the strongest suggestion basis.
_RELATED_SQL = """
SELECT cre.claim_id, e.id, e.canonical_name, e.entity_type::text
FROM claim_related_entities cre
JOIN claims c ON c.id = cre.claim_id
JOIN entities e ON e.id = cre.entity_id
WHERE c.subject_entity_id IS NULL
  AND NOT EXISTS (SELECT 1 FROM claim_supersessions cs WHERE cs.superseded_claim_id = c.id)
"""

_ENTITY_NAMES_SQL = "SELECT id, canonical_name, entity_type::text FROM entities"

_DOCUMENTS_SQL = """
SELECT d.id, p.normalized_path
FROM source_documents d
JOIN source_document_paths p ON p.source_document_id = d.id AND p.is_current
"""

_ENTITY_ALIASES_SQL = """
SELECT a.alias, a.entity_id, e.canonical_name, e.entity_type::text
FROM entity_aliases a
JOIN entities e ON e.id = a.entity_id
"""


class PostgresOrphanedClaimsRepository:
    def __init__(self, database: PostgresDatabase) -> None:
        self._database = database

    def orphaned_claims(self) -> list[tuple[Any, ...]]:
        with self._database.connection() as connection:
            return [
                tuple(row)
                for row in connection.execute(_ORPHANS_SQL).fetchall()
            ]

    def related_entities(self) -> list[tuple[Any, ...]]:
        with self._database.connection() as connection:
            return [
                tuple(row)
                for row in connection.execute(_RELATED_SQL).fetchall()
            ]

    def entity_names(self) -> list[tuple[Any, ...]]:
        with self._database.connection() as connection:
            return [
                tuple(row)
                for row in connection.execute(_ENTITY_NAMES_SQL).fetchall()
            ]

    def entity_aliases(self) -> list[tuple[Any, ...]]:
        with self._database.connection() as connection:
            return [
                tuple(row)
                for row in connection.execute(_ENTITY_ALIASES_SQL).fetchall()
            ]

    def document_paths(self) -> list[tuple[Any, ...]]:
        with self._database.connection() as connection:
            return [
                tuple(row)
                for row in connection.execute(_DOCUMENTS_SQL).fetchall()
            ]
