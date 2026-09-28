"""PostgreSQL reads for the unpromoted-material audit (TKT-0136 repair lane)."""

from __future__ import annotations

from typing import Any

from dm_assistant_core.adapters.postgres.database import PostgresDatabase

# Entities with an authored description page (entities/{slug}.md — the same
# slug rule the description service files under) and zero current claims.
_EMPTY_SHELLS_SQL = """
SELECT e.id, e.canonical_name, e.entity_type::text,
       page.document_id
FROM entities e
JOIN LATERAL (
    SELECT d.id AS document_id
    FROM source_documents d
    JOIN source_document_paths p
        ON p.source_document_id = d.id AND p.is_current
    WHERE p.normalized_path = 'entities/'
        || btrim(regexp_replace(lower(e.canonical_name), '[^a-z0-9]+', '-', 'g'), '-')
        || '.md'
    LIMIT 1
) page ON true
WHERE NOT EXISTS (
    SELECT 1 FROM claims c
    WHERE c.subject_entity_id = e.id
      AND NOT EXISTS (SELECT 1 FROM claim_supersessions cs
                      WHERE cs.superseded_claim_id = c.id)
)
ORDER BY e.canonical_name
LIMIT 100
"""

# Direct-input documents (session notes) with statements still pending.
_PENDING_CAPTURES_SQL = """
SELECT sd.id, p.normalized_path,
       latest.frontmatter_json->>'type' AS kind,
       count(*) AS pending
FROM import_candidates ic
JOIN source_documents sd ON sd.id = ic.source_document_id
JOIN source_document_paths p ON p.source_document_id = sd.id AND p.is_current
JOIN LATERAL (
    SELECT sr.frontmatter_json
    FROM source_revisions sr
    WHERE sr.source_document_id = sd.id
    ORDER BY sr.captured_at DESC, sr.id DESC
    LIMIT 1
) latest ON true
WHERE ic.review_status = 'pending' AND ic.status = 'active'
  -- Brainstorm thought documents belong to their session's single
  -- unpromoted_thoughts finding — listing them here too double-counts a
  -- work-in-progress once per thought (live case: The Wrath of Romulus).
  AND NOT EXISTS (SELECT 1 FROM brainstorm_thoughts bt
                  WHERE bt.source_document_id = sd.id)
GROUP BY sd.id, p.normalized_path, latest.frontmatter_json
ORDER BY pending DESC, p.normalized_path
LIMIT 100
"""

# Brainstorm sessions with thought candidates never promoted.
_UNPROMOTED_THOUGHTS_SQL = """
SELECT bs.workflow_session_id, bs.title, count(*) AS pending
FROM brainstorm_thoughts bt
JOIN brainstorm_sessions bs ON bs.workflow_session_id = bt.workflow_session_id
JOIN import_candidates ic ON ic.id = bt.candidate_id
WHERE ic.review_status = 'pending' AND ic.status = 'active'
GROUP BY bs.workflow_session_id, bs.title
ORDER BY pending DESC, bs.title
LIMIT 100
"""


class PostgresUnpromotedAuditRepository:
    def __init__(self, database: PostgresDatabase) -> None:
        self._database = database

    def empty_shells(self) -> list[tuple[Any, ...]]:
        with self._database.connection() as connection:
            return [
                tuple(row)
                for row in connection.execute(_EMPTY_SHELLS_SQL).fetchall()
            ]

    def pending_captures(self) -> list[tuple[Any, ...]]:
        with self._database.connection() as connection:
            return [
                tuple(row)
                for row in connection.execute(_PENDING_CAPTURES_SQL).fetchall()
            ]

    def unpromoted_thoughts(self) -> list[tuple[Any, ...]]:
        with self._database.connection() as connection:
            return [
                tuple(row)
                for row in connection.execute(_UNPROMOTED_THOUGHTS_SQL).fetchall()
            ]
