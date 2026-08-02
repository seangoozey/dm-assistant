"""PostgreSQL reader for accepted claims, relationships, and import context."""

from __future__ import annotations

import re
from typing import Any

from dm_assistant_core.adapters.postgres.database import PostgresDatabase
from dm_assistant_core.domain import (
    RetrievalAuthority,
    RetrievalQuery,
    RetrievalRecord,
    RetrievalRecordKind,
)
from dm_assistant_core.domain.models import ClaimState

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
            for record in records
            if not terms or terms & _query_terms(record.assertion)
        ]
        return tuple(
            sorted(relevant, key=lambda record: (record.citation, record.record_id))[:100]
        )

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
            effective_from=str(row[10]) if row[10] is not None else None,
            expected_at=str(row[11]) if row[11] is not None else None,
            observed_at=str(row[12]) if row[12] is not None else None,
        )


def _query_terms(text: str) -> set[str]:
    return {
        token
        for token in WORD.findall(text.casefold())
        if len(token) >= 3 and token not in {"the", "what", "when", "where", "who", "why"}
    }


_CLAIMS_SQL = """
SELECT DISTINCT ON (c.id)
    c.id, 'claim', c.assertion_text, c.state::text, c.authority::text,
    c.visibility, sd.id, sd.original_path || '#' || coalesce(ss.section_path, 'source'),
    true, c.recorded_at, c.effective_from, c.expected_at, c.observed_at
FROM claims c
JOIN claim_evidence ce ON ce.claim_id = c.id
JOIN source_spans ss ON ss.id = ce.source_span_id
JOIN source_revisions sr ON sr.id = ss.source_revision_id
JOIN source_documents sd ON sd.id = sr.source_document_id
ORDER BY c.id, ss.start_offset
"""

_RELATIONSHIPS_SQL = """
SELECT DISTINCT ON (r.id)
    r.id, 'relationship', r.assertion_text, r.state::text, r.authority::text,
    r.visibility, sd.id, sd.original_path || '#' || coalesce(ss.section_path, 'source'),
    true, r.recorded_at, r.effective_from, r.expected_at, r.observed_at
FROM relationships r
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
    false, ic.created_at, NULL, NULL, NULL
FROM import_candidates ic
JOIN import_candidate_evidence ice ON ice.candidate_id = ic.id
JOIN source_revisions sr ON sr.id = ice.source_revision_id
JOIN source_documents sd ON sd.id = ic.source_document_id
WHERE ic.status = 'active'
ORDER BY ic.id, ice.start_offset
"""
