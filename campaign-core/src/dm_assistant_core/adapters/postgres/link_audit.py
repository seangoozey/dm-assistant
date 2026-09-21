from typing import Any
from uuid import UUID

from dm_assistant_core.adapters.postgres.database import PostgresDatabase


class PostgresLinkAuditRepository:
    def __init__(self, database: PostgresDatabase) -> None:
        self._database = database

    def entities_with_sources(self) -> list[tuple[UUID, str, str, list[tuple[UUID, str]]]]:
        with self._database.connection() as connection:
            rows = connection.execute(
                """
                SELECT DISTINCT e.id, e.canonical_name, e.entity_type, sd.id, sdp.normalized_path
                FROM entities e
                JOIN claims c ON c.subject_entity_id = e.id
                JOIN claim_evidence ce ON ce.claim_id = c.id
                JOIN source_spans ss ON ss.id = ce.source_span_id
                JOIN source_revisions sr ON sr.id = ss.source_revision_id
                JOIN source_documents sd ON sd.id = sr.source_document_id
                JOIN source_document_paths sdp ON sdp.source_document_id = sd.id AND sdp.is_current
                WHERE c.state NOT IN ('superseded')
                ORDER BY e.id, sdp.normalized_path
                """
            ).fetchall()
        grouped: dict[UUID, tuple[str, str, list[tuple[UUID, str]]]] = {}
        for row in rows:
            entity_id, name, kind, doc_id, path = row[0], row[1], row[2] or "unknown", row[3], str(row[4])
            if entity_id not in grouped:
                grouped[entity_id] = (name, kind, [])
            grouped[entity_id][2].append((doc_id, path))
        return [
            (entity_id, data[0], data[1], data[2])
            for entity_id, data in grouped.items()
        ]

    def all_entity_names(self) -> list[str]:
        with self._database.connection() as connection:
            rows = connection.execute(
                "SELECT canonical_name FROM entities"
            ).fetchall()
        return [row[0] for row in rows]
