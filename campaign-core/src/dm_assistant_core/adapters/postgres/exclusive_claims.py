"""PostgreSQL reads for the exclusive-claims gather (TKT-0140 Step 1)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from dm_assistant_core.adapters.postgres.database import PostgresDatabase

_UNQUALIFIED_SQL = """
SELECT e.id, e.canonical_name, e.entity_type::text
FROM entities e
WHERE NOT EXISTS (
    SELECT 1 FROM claims c
    WHERE c.subject_entity_id = e.id
      AND NOT EXISTS (SELECT 1 FROM claim_supersessions cs
                      WHERE cs.superseded_claim_id = c.id)
)
"""

_DOCUMENTS_SQL = """
SELECT d.id, p.normalized_path
FROM source_documents d
JOIN source_document_paths p ON p.source_document_id = d.id AND p.is_current
"""

_ENTITY_NAMES_SQL = "SELECT id, canonical_name FROM entities"

# Claims whose ONLY evidence spans lives on this document — the document's
# exclusive material, whatever its current owner (or none).
_EXCLUSIVE_SQL = """
SELECT DISTINCT c.id, c.assertion_text, c.state::text, c.subject_entity_id, owner.canonical_name
FROM claims c
JOIN claim_evidence ce ON ce.claim_id = c.id
JOIN source_spans ss ON ss.id = ce.source_span_id
JOIN source_revisions sr ON sr.id = ss.source_revision_id
LEFT JOIN entities owner ON owner.id = c.subject_entity_id
WHERE sr.source_document_id = %s
  AND NOT EXISTS (SELECT 1 FROM claim_supersessions cs WHERE cs.superseded_claim_id = c.id)
  AND NOT EXISTS (
      SELECT 1 FROM claim_evidence ce2
      JOIN source_spans ss2 ON ss2.id = ce2.source_span_id
      JOIN source_revisions sr2 ON sr2.id = ss2.source_revision_id
      WHERE ce2.claim_id = c.id AND sr2.source_document_id <> %s
  )
ORDER BY c.assertion_text
"""


class PostgresExclusiveClaimsRepository:
    def __init__(self, database: PostgresDatabase) -> None:
        self._database = database

    def unqualified_entities(self) -> list[tuple[Any, ...]]:
        with self._database.connection() as connection:
            return [
                tuple(row)
                for row in connection.execute(_UNQUALIFIED_SQL).fetchall()
            ]

    def document_paths(self) -> list[tuple[Any, ...]]:
        with self._database.connection() as connection:
            return [
                tuple(row)
                for row in connection.execute(_DOCUMENTS_SQL).fetchall()
            ]

    def entity_names(self) -> list[tuple[Any, ...]]:
        with self._database.connection() as connection:
            return [
                tuple(row)
                for row in connection.execute(_ENTITY_NAMES_SQL).fetchall()
            ]

    def claims_exclusive_to(self, document_id: UUID) -> list[tuple[Any, ...]]:
        with self._database.connection() as connection:
            return [
                tuple(row)
                for row in connection.execute(
                    _EXCLUSIVE_SQL, (document_id, document_id)
                ).fetchall()
            ]
