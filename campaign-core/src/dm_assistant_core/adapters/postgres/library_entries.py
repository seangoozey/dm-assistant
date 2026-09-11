"""PostgreSQL canonical library-entry projection."""

# SQL remains formatted as readable query text rather than Python-width fragments.
# ruff: noqa: E501

from typing import Any, cast
from uuid import UUID

from dm_assistant_core.adapters.postgres.database import PostgresDatabase
from dm_assistant_core.application.library_entries import (
    ClaimProjection,
    LibraryEntry,
    LibraryEntryClaim,
    LibraryEntryClaimHistory,
    LibraryEntrySource,
    LibraryEntrySummary,
)
from dm_assistant_core.domain import EntityKind

_IDENTITY_SQL = """
SELECT e.id, e.canonical_name, e.entity_type,
       ARRAY(SELECT a.alias FROM entity_aliases a WHERE a.entity_id = e.id ORDER BY lower(a.alias)),
       ARRAY(SELECT t.name FROM current_entity_tags t WHERE t.entity_id = e.id ORDER BY t.normalized_name),
       (SELECT count(*) FROM claims c WHERE (c.subject_entity_id = e.id OR EXISTS (
            SELECT 1 FROM claim_related_entities cre WHERE cre.claim_id = c.id AND cre.entity_id = e.id
        ))
        AND NOT EXISTS (SELECT 1 FROM claim_supersessions cs WHERE cs.superseded_claim_id = c.id)),
       (SELECT count(DISTINCT linked.source_document_id) FROM (
            SELECT sr.source_document_id FROM claims c
            JOIN claim_evidence ce ON ce.claim_id = c.id
            JOIN source_spans ss ON ss.id = ce.source_span_id
            JOIN source_revisions sr ON sr.id = ss.source_revision_id
            WHERE c.subject_entity_id = e.id OR EXISTS (
                SELECT 1 FROM claim_related_entities cre WHERE cre.claim_id = c.id AND cre.entity_id = e.id
            )
            UNION
            SELECT (csi.after_json->>'source_document_id')::uuid
            FROM change_set_items csi
            WHERE csi.change_set_id = e.created_by_change_set_id
              AND csi.after_json->>'id' = e.id::text
              AND csi.after_json->>'source_document_id' IS NOT NULL
       ) linked)
FROM entities e
"""


def _summary(row: Any) -> LibraryEntrySummary:
    return LibraryEntrySummary(
        entry_id=row[0],
        canonical_name=str(row[1]),
        entity_kind=EntityKind(str(row[2])),
        aliases=tuple(row[3] or ()),
        tags=tuple(row[4] or ()),
        current_claim_count=int(row[5]),
        source_count=int(row[6]),
    )


class PostgresLibraryEntryRepository:
    def __init__(self, database: PostgresDatabase) -> None:
        self._database = database

    def list(self) -> tuple[LibraryEntrySummary, ...]:
        with self._database.connection() as connection:
            rows = connection.execute(
                _IDENTITY_SQL + " ORDER BY e.entity_type, lower(e.canonical_name), e.id"
            ).fetchall()
        return tuple(_summary(row) for row in rows)

    def get(self, entry_id: UUID) -> LibraryEntry | None:
        with self._database.connection() as connection:
            row = connection.execute(_IDENTITY_SQL + " WHERE e.id = %s", (entry_id,)).fetchone()
            if row is None:
                return None
            claim_rows = connection.execute(
                """
                SELECT c.id, c.assertion_text, c.state::text, c.authority::text,
                       c.visibility, c.is_conditional, cc.trigger_text, c.recorded_at,
                       CASE WHEN c.state = 'intended' AND c.authority IN ('real_play', 'dm_correction')
                                 AND NOT c.predicts_subject_action THEN 'player_plan'
                            WHEN c.authority IN ('real_play', 'dm_correction') THEN 'real_play'
                            WHEN c.authority = 'npc_intention' THEN 'npc_plan'
                            WHEN c.authority IN ('brainstorm', 'preparation') THEN 'dm_plan'
                            WHEN c.state = 'intended' AND c.predicts_subject_action THEN 'player_plan'
                            ELSE 'lore_fact' END,
                       (SELECT jsonb_agg(source ORDER BY source->>'path') FROM (
                            SELECT DISTINCT jsonb_build_object('document_id', sd.id, 'path', sdp.normalized_path) AS source
                            FROM claim_evidence ce
                            JOIN source_spans ss ON ss.id = ce.source_span_id
                            JOIN source_revisions sr ON sr.id = ss.source_revision_id
                            JOIN source_documents sd ON sd.id = sr.source_document_id
                            JOIN source_document_paths sdp ON sdp.source_document_id = sd.id
                            WHERE ce.claim_id = c.id
                       ) evidence_sources)
                FROM claims c
                LEFT JOIN claim_conditions cc ON cc.claim_id = c.id
                WHERE (c.subject_entity_id = %s OR EXISTS (
                    SELECT 1 FROM claim_related_entities cre WHERE cre.claim_id = c.id AND cre.entity_id = %s
                ))
                  AND NOT EXISTS (SELECT 1 FROM claim_supersessions cs WHERE cs.superseded_claim_id = c.id)
                ORDER BY c.recorded_at, c.id
                """,
                (entry_id, entry_id),
            ).fetchall()
            history_rows = connection.execute(
                """
                SELECT c.id, c.assertion_text, c.state::text, c.authority::text,
                       c.visibility, c.is_conditional, cc.trigger_text, c.recorded_at,
                       CASE WHEN c.state = 'intended' AND c.authority IN ('real_play', 'dm_correction')
                                 AND NOT c.predicts_subject_action THEN 'player_plan'
                            WHEN c.authority IN ('real_play', 'dm_correction') THEN 'real_play'
                            WHEN c.authority = 'npc_intention' THEN 'npc_plan'
                            WHEN c.authority IN ('brainstorm', 'preparation') THEN 'dm_plan'
                            WHEN c.state = 'intended' AND c.predicts_subject_action THEN 'player_plan'
                            ELSE 'lore_fact' END,
                       (SELECT jsonb_agg(source ORDER BY source->>'path') FROM (
                            SELECT DISTINCT jsonb_build_object('document_id', sd.id, 'path', sdp.normalized_path) AS source
                            FROM claim_evidence ce
                            JOIN source_spans ss ON ss.id = ce.source_span_id
                            JOIN source_revisions sr ON sr.id = ss.source_revision_id
                            JOIN source_documents sd ON sd.id = sr.source_document_id
                            JOIN source_document_paths sdp ON sdp.source_document_id = sd.id
                            WHERE ce.claim_id = c.id
                       ) evidence_sources),
                       cs.superseding_claim_id, cs.reason
                FROM claims c
                JOIN claim_supersessions cs ON cs.superseded_claim_id = c.id
                LEFT JOIN claim_conditions cc ON cc.claim_id = c.id
                WHERE c.subject_entity_id = %s OR EXISTS (
                    SELECT 1 FROM claim_related_entities cre WHERE cre.claim_id = c.id AND cre.entity_id = %s
                )
                ORDER BY c.recorded_at, c.id
                """,
                (entry_id, entry_id),
            ).fetchall()
            source_rows = connection.execute(
                """
                SELECT DISTINCT sd.id, sdp.normalized_path FROM (
                    SELECT sr.source_document_id FROM claims c
                    JOIN claim_evidence ce ON ce.claim_id = c.id
                    JOIN source_spans ss ON ss.id = ce.source_span_id
                    JOIN source_revisions sr ON sr.id = ss.source_revision_id
                    WHERE c.subject_entity_id = %s OR EXISTS (
                        SELECT 1 FROM claim_related_entities cre WHERE cre.claim_id = c.id AND cre.entity_id = %s
                    )
                    UNION
                    SELECT (csi.after_json->>'source_document_id')::uuid
                    FROM entities created
                    JOIN change_set_items csi ON csi.change_set_id = created.created_by_change_set_id
                    WHERE created.id = %s AND csi.after_json->>'id' = created.id::text
                      AND csi.after_json->>'source_document_id' IS NOT NULL
                ) linked
                JOIN source_documents sd ON sd.id = linked.source_document_id
                JOIN source_document_paths sdp ON sdp.source_document_id = sd.id
                ORDER BY sdp.normalized_path
                """,
                (entry_id, entry_id, entry_id),
            ).fetchall()
        summary = _summary(row)
        sources = tuple(
            LibraryEntrySource(document_id=item[0], path=str(item[1])) for item in source_rows
        )
        claims = []
        for claim in claim_rows:
            claim_sources = tuple(LibraryEntrySource(**item) for item in (claim[9] or ()))
            claims.append(
                LibraryEntryClaim(
                    claim_id=claim[0],
                    assertion_text=str(claim[1]),
                    state=str(claim[2]),
                    authority=str(claim[3]),
                    visibility=str(claim[4]),
                    conditional=bool(claim[5]),
                    condition_text=str(claim[6]) if claim[6] is not None else None,
                    recorded_at=claim[7],
                    projection=cast(ClaimProjection, str(claim[8])),
                    sources=claim_sources,
                )
            )
        history = []
        for claim in history_rows:
            claim_sources = tuple(LibraryEntrySource(**item) for item in (claim[9] or ()))
            history.append(
                LibraryEntryClaimHistory(
                    claim_id=claim[0],
                    assertion_text=str(claim[1]),
                    state=str(claim[2]),
                    authority=str(claim[3]),
                    visibility=str(claim[4]),
                    conditional=bool(claim[5]),
                    condition_text=str(claim[6]) if claim[6] is not None else None,
                    recorded_at=claim[7],
                    projection=cast(ClaimProjection, str(claim[8])),
                    sources=claim_sources,
                    superseded_by_claim_id=claim[10],
                    supersession_reason=str(claim[11]),
                )
            )
        return LibraryEntry(
            **summary.model_dump(),
            claims=tuple(claims),
            claim_history=tuple(history),
            sources=sources,
        )
