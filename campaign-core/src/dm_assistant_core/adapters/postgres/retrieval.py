"""PostgreSQL reader for accepted claims, relationships, and import context."""

from __future__ import annotations

import re
from typing import Any
from uuid import UUID

from dm_assistant_core.adapters.postgres.database import PostgresDatabase
from dm_assistant_core.domain import (
    EntityKind,
    RetrievalAuthority,
    RetrievalQuery,
    RetrievalRecord,
    RetrievalRecordKind,
)
from dm_assistant_core.domain.derived_retrieval import IndexSuggestion, record_fingerprint
from dm_assistant_core.domain.models import ClaimState
from dm_assistant_core.domain.retrieval import _is_visible
from dm_assistant_core.domain.retrieval_paths import CurrentLink

WORD = re.compile(r"[a-z0-9]+")
AUTHORITY_MAP = {
    "real_play": RetrievalAuthority.REAL_PLAY,
    "dm_correction": RetrievalAuthority.EXPLICIT_CORRECTION,
    "explicit_lore": RetrievalAuthority.EXPLICIT_LORE,
    "npc_intention": RetrievalAuthority.NPC_INTENTION,
    "preparation": RetrievalAuthority.PREPARATION,
    "brainstorm": RetrievalAuthority.BRAINSTORM,
    "unclassified": RetrievalAuthority.UNCLASSIFIED,
    "derived": RetrievalAuthority.DERIVED,
}


class PostgresRetrievalRepository:
    """Read authoritative records and non-canonical candidates without writing state."""

    def __init__(self, database: PostgresDatabase) -> None:
        self._database = database

    def current_records(
        self, query: RetrievalQuery, record_ids: tuple[str, ...],
    ) -> tuple[RetrievalRecord, ...]:
        """Fetch exact canonical IDs in one statement snapshot, never lexical guesses.

        Import candidates cannot enter through this reader. Derived suggestions are
        not authorization; visibility is checked again before returning records.
        """
        if len(record_ids) > 100:
            raise ValueError("at most 100 record IDs allowed")
        for identity in record_ids:
            UUID(identity)
        if not record_ids:
            return ()
        with self._database.connection() as connection:
            return self._current_records(query, record_ids, connection)

    def current_paths(
        self, query: RetrievalQuery, record_ids: tuple[str, ...],
    ) -> tuple[tuple[RetrievalRecord, ...], tuple[CurrentLink, ...]]:
        """Read bounded shared-evidence associations, not semantic relationships.

        Both endpoints cite the exact same immutable span. This only establishes
        an evidence association. No lexical or model-generated edges enter here.
        """
        if len(record_ids) > 100:
            raise ValueError("at most 100 record IDs allowed")
        ids = list(dict.fromkeys(UUID(identity) for identity in record_ids))
        if not ids:
            return (), ()
        with self._database.connection() as connection:
            connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            # Facets filter returned targets later, not intermediate path records.
            path_query = query.model_copy(update={"entity_kinds": (), "tags": ()})
            records = self._current_records(path_query, record_ids, connection)
            rows = connection.execute(_SHARED_EVIDENCE_SQL, (ids,)).fetchall()
        snapshots = {r.record_id: IndexSuggestion(record_id=r.record_id,
                     fingerprint=record_fingerprint(r)) for r in records}
        links = tuple(CurrentLink(
            edge_id=f"shared-span:{span}:{left}:{right}", from_id=str(left), to_id=str(right),
            evidence=(snapshots[str(left)], snapshots[str(right)]),
        ) for left, right, span in rows
            if str(left) in snapshots and str(right) in snapshots)
        return records, links

    def _current_records(
        self, query: RetrievalQuery, record_ids: tuple[str, ...], connection: Any,
    ) -> tuple[RetrievalRecord, ...]:
        if len(record_ids) > 100:
            raise ValueError("at most 100 record IDs allowed")
        ids = list(dict.fromkeys(UUID(identity) for identity in record_ids))
        if not ids:
            return ()
        sql = (
            "WITH current_records(record_id, kind, assertion, state, authority, visibility, "
            "source_id, citation, accepted, recorded_at, effective_year, effective_month, "
            "effective_day, expected_year, expected_month, expected_day, observed_year, "
            "observed_month, observed_day, entity_kind, tags, searchable_text, entity_id) AS "
            f"(({_CLAIMS_SQL}) UNION ALL ({_RELATIONSHIPS_SQL})) "
            "SELECT current_records.*, "
            "(SELECT string_agg(concat_ws(':', ss.id, sr.id, sr.content_hash, "
            "ss.start_offset, ss.end_offset, ss.excerpt_hash), ',' ORDER BY ss.id) "
            "FROM (SELECT claim_id AS record_id, source_span_id FROM claim_evidence "
            "UNION ALL SELECT relationship_id, source_span_id FROM relationship_evidence) links "
            "JOIN source_spans ss ON ss.id=links.source_span_id "
            "JOIN source_revisions sr ON sr.id=ss.source_revision_id "
            "WHERE links.record_id=current_records.record_id) AS evidence_binding "
            "FROM current_records WHERE record_id = ANY(%s::uuid[])"
        )
        rows = connection.execute(sql, (ids,)).fetchall()
        records = [self._to_record(row[:-1]).model_copy(update={"evidence_binding": row[-1]})
                   for row in rows]
        return tuple(sorted((r for r in records
                             if r.record_id in record_ids and _is_visible(r, query)
                             and r.state not in {ClaimState.SUPERSEDED, ClaimState.REJECTED}
                             and (not query.entity_kinds or r.entity_kind in query.entity_kinds)
                             and (not query.tags or set(query.tags).issubset(r.tags))),
                            key=lambda r: r.record_id))

    def relevant_records(self, query: RetrievalQuery) -> tuple[RetrievalRecord, ...]:
        with self._database.connection() as connection:
            rows = [
                *connection.execute(_CLAIMS_SQL).fetchall(),
                *connection.execute(_RELATIONSHIPS_SQL).fetchall(),
                *connection.execute(_CANDIDATES_SQL).fetchall(),
            ]
        records = tuple(self._to_record(row) for row in rows)
        terms = _query_terms(query.question)
        relevant = [
            record
            for record, row in zip(records, rows, strict=True)
            if (not terms or terms & _query_terms(str(row[21])))
            and _is_visible(record, query)
            and (not query.entity_kinds or record.entity_kind in query.entity_kinds)
            and (not query.tags or set(query.tags).issubset(record.tags))
        ]
        return tuple(sorted(relevant, key=lambda record: (record.citation, record.record_id))[:100])

    @staticmethod
    def _to_record(row: tuple[Any, ...]) -> RetrievalRecord:
        return RetrievalRecord(
            record_id=str(row[0]),
            kind=RetrievalRecordKind(str(row[1])),
            assertion=str(row[2]),
            state=ClaimState(str(row[3])),
            authority=AUTHORITY_MAP[str(row[4])],
            visibility="dm" if row[5] == "dm_only" else str(row[5]),
            source_id=str(row[6]),
            citation=str(row[7]),
            accepted=bool(row[8]),
            recorded_at=str(row[9]) if row[9] is not None else None,
            effective_from=_render_date(row[10], row[11], row[12]),
            expected_at=_render_date(row[13], row[14], row[15]),
            observed_at=_render_date(row[16], row[17], row[18]),
            entity_kind=EntityKind(str(row[19])) if row[19] is not None else None,
            tags=tuple(str(tag) for tag in (row[20] or ())),
            entity_id=str(row[22]) if row[22] is not None else None,
        )


def _query_terms(text: str) -> set[str]:
    return {
        token
        for token in WORD.findall(text.casefold())
        if len(token) >= 3 and token not in {"the", "what", "when", "where", "who", "why"}
    }


def _render_date(year: Any, month: Any, day: Any) -> str | None:
    """Render integer campaign-date columns as an opaque retrieval label.

    The retrieval layer treats campaign dates as opaque strings (the acceptance fixtures
    use symbolic labels like ``day-18``). A BCE year renders as a negative integer so it
    orders and displays honestly.
    """
    if year is None:
        return None
    parts = [str(int(year))]
    if month is not None:
        parts.append(f"{int(month):02d}")
        if day is not None:
            parts.append(f"{int(day):02d}")
    return "-".join(parts)


_SHARED_EVIDENCE_SQL = """
WITH evidence AS (
    SELECT claim_id AS record_id, source_span_id FROM claim_evidence
    UNION
    SELECT relationship_id, source_span_id FROM relationship_evidence
), requested AS (
    SELECT * FROM evidence WHERE record_id = ANY(%s::uuid[])
)
SELECT a.record_id, b.record_id, min(a.source_span_id::text)
FROM requested a JOIN requested b ON a.source_span_id = b.source_span_id
WHERE a.record_id <> b.record_id
GROUP BY a.record_id, b.record_id
ORDER BY a.record_id, b.record_id
"""


_CLAIMS_SQL = """
SELECT DISTINCT ON (c.id)
    c.id, 'claim', c.assertion_text, c.state::text, c.authority::text,
    c.visibility, sd.id, sd.original_path || '#' || coalesce(ss.section_path, 'source'),
    true, c.recorded_at,
    c.effective_from_year, c.effective_from_month, c.effective_from_day,
    c.expected_year, c.expected_month, c.expected_day,
    c.observed_year, c.observed_month, c.observed_day,
    coalesce(kd.canonical_key, e.entity_type),
    ARRAY(SELECT cet.normalized_name FROM current_entity_tags cet
          WHERE cet.entity_id = e.id ORDER BY cet.normalized_name),
    concat_ws(' ', c.assertion_text, e.canonical_name,
              (SELECT string_agg(ea.alias, ' ') FROM entity_aliases ea
               WHERE ea.entity_id = e.id)),
    e.id
FROM claims c
LEFT JOIN entities e ON e.id = c.subject_entity_id
LEFT JOIN kind_definitions kd ON kd.id = e.entity_kind_id
JOIN claim_evidence ce ON ce.claim_id = c.id
JOIN source_spans ss ON ss.id = ce.source_span_id
JOIN source_revisions sr ON sr.id = ss.source_revision_id
JOIN source_documents sd ON sd.id = sr.source_document_id
WHERE NOT EXISTS (
    SELECT 1 FROM claim_supersessions cs WHERE cs.superseded_claim_id = c.id
)
ORDER BY c.id, ss.start_offset
"""

_RELATIONSHIPS_SQL = """
SELECT DISTINCT ON (r.id)
    r.id, 'relationship', r.assertion_text, r.state::text, r.authority::text,
    r.visibility, sd.id, sd.original_path || '#' || coalesce(ss.section_path, 'source'),
    true, r.recorded_at,
    r.effective_from_year, r.effective_from_month, r.effective_from_day,
    r.expected_year, r.expected_month, r.expected_day,
    r.observed_year, r.observed_month, r.observed_day,
    coalesce(kd.canonical_key, e.entity_type),
    ARRAY(SELECT cet.normalized_name FROM current_entity_tags cet
          WHERE cet.entity_id = e.id ORDER BY cet.normalized_name),
    concat_ws(' ', r.assertion_text, e.canonical_name,
              (SELECT string_agg(ea.alias, ' ') FROM entity_aliases ea
               WHERE ea.entity_id = e.id)),
    e.id
FROM relationships r
JOIN entities e ON e.id = r.from_entity_id
LEFT JOIN kind_definitions kd ON kd.id = e.entity_kind_id
JOIN relationship_evidence re ON re.relationship_id = r.id
JOIN source_spans ss ON ss.id = re.source_span_id
JOIN source_revisions sr ON sr.id = ss.source_revision_id
JOIN source_documents sd ON sd.id = sr.source_document_id
ORDER BY r.id, ss.start_offset
"""

_CANDIDATES_SQL = """
SELECT DISTINCT ON (ic.id)
    ic.id, 'claim', ic.assertion_text, ic.state::text, ic.authority::text,
    ic.visibility, sd.id,
    coalesce(sr.original_path, sd.original_path) || '#' || ice.section_path,
    false, ic.created_at,
    NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL,
    ARRAY[]::text[], ic.assertion_text, NULL
FROM import_candidates ic
JOIN import_candidate_evidence ice ON ice.candidate_id = ic.id
JOIN source_revisions sr ON sr.id = ice.source_revision_id
JOIN source_documents sd ON sd.id = ic.source_document_id
WHERE ic.status = 'active'
ORDER BY ic.id, ice.start_offset
"""
