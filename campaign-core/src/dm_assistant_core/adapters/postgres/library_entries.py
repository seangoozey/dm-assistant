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
    LibraryEntryMember,
    LibraryEntryRole,
    LibraryEntrySource,
    LibraryEntrySummary,
)
from dm_assistant_core.domain import EntityKind

_IDENTITY_SQL = """
SELECT e.id, e.canonical_name, e.entity_type,
       ARRAY(SELECT a.alias FROM entity_aliases a WHERE a.entity_id = e.id
             AND coalesce(a.alias_kind, '') <> 'misspelling' ORDER BY lower(a.alias)),
       ARRAY(SELECT a.alias FROM entity_aliases a WHERE a.entity_id = e.id
             AND a.alias_kind = 'misspelling' ORDER BY lower(a.alias)),
       CASE WHEN e.entity_type = 'faction' THEN COALESCE((
         SELECT array_agg(jsonb_build_object(
                  'member_id', mr.member_id, 'name', me.canonical_name,
                  'role_title', mr.role_title,
                  'is_leadership', coalesce(fr.is_leadership, false))
                ORDER BY me.canonical_name)
         FROM membership_records mr
         JOIN entities me ON me.id = mr.member_id
         LEFT JOIN faction_roles fr ON fr.faction_id = mr.faction_id AND fr.name = mr.role_title
         WHERE mr.faction_id = e.id AND mr.superseded_by IS NULL),
         ARRAY[]::jsonb[]) ELSE NULL END,
       CASE WHEN e.entity_type = 'faction'
             AND NOT EXISTS (SELECT 1 FROM membership_records mr0 WHERE mr0.faction_id = e.id)
       THEN COALESCE((
         SELECT array_agg(DISTINCT m.canonical_name ORDER BY m.canonical_name) FROM (
           SELECT DISTINCT ON (me.id) me.canonical_name
           FROM claim_related_entities cre
           JOIN entities me ON me.id = cre.entity_id AND me.entity_type IN ('pc', 'npc')
           WHERE cre.claim_id IN (SELECT claim_id FROM claim_related_entities
                                  WHERE entity_id = e.id)
             AND me.id <> e.id
         ) m), ARRAY[]::text[]) ELSE NULL END,
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
        misspellings=tuple(row[4] or ()),
        members=tuple(LibraryEntryMember.model_validate(item) for item in (row[5] or ())),
        related=tuple(row[6] or ()),
        tags=tuple(row[7] or ()),
        current_claim_count=int(row[8]),
        source_count=int(row[9]),
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
                       c.subject_entity_id, owner.canonical_name,
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
                LEFT JOIN entities owner ON owner.id = c.subject_entity_id
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
                       c.subject_entity_id, owner.canonical_name,
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
                LEFT JOIN entities owner ON owner.id = c.subject_entity_id
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
            role_rows = connection.execute(
                """
                SELECT fr.name, fr.is_leadership,
                       (SELECT array_agg(me.canonical_name ORDER BY me.canonical_name)
                        FROM membership_records mr
                        JOIN entities me ON me.id = mr.member_id
                        WHERE mr.faction_id = fr.faction_id AND mr.role_title = fr.name
                          AND mr.superseded_by IS NULL)
                FROM faction_roles fr
                WHERE fr.faction_id = %s
                ORDER BY fr.is_leadership DESC, lower(fr.name)
                """,
                (entry_id,),
            ).fetchall()
        summary = _summary(row)
        sources = tuple(
            LibraryEntrySource(document_id=item[0], path=str(item[1])) for item in source_rows
        )
        roles = tuple(
            LibraryEntryRole(name=str(item[0]), is_leadership=bool(item[1]),
                             holder_names=tuple(item[2] or ()))
            for item in role_rows
        )
        claims = []
        for claim in claim_rows:
            claim_sources = tuple(LibraryEntrySource(**item) for item in (claim[11] or ()))
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
                    subject_entity_id=claim[8],
                    subject_entity_name=str(claim[9]) if claim[9] is not None else None,
                    projection=cast(ClaimProjection, str(claim[10])),
                    sources=claim_sources,
                )
            )
        history = []
        for claim in history_rows:
            claim_sources = tuple(LibraryEntrySource(**item) for item in (claim[11] or ()))
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
                    subject_entity_id=claim[8],
                    subject_entity_name=str(claim[9]) if claim[9] is not None else None,
                    projection=cast(ClaimProjection, str(claim[10])),
                    sources=claim_sources,
                    superseded_by_claim_id=claim[12],
                    supersession_reason=str(claim[13]),
                )
            )
        return LibraryEntry(
            **summary.model_dump(),
            claims=tuple(claims),
            claim_history=tuple(history),
            sources=sources,
            roles=roles,
        )
