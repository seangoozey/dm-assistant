"""Campaign timestamp coverage (TKT-0118): the session dating walk and
conflict-ranked undated-claim residue, over the 0058 overlay machinery."""

from datetime import datetime
from uuid import UUID

from dm_assistant_core.adapters.postgres.database import PostgresDatabase


class SessionDatingEntry:
    def __init__(self, document_id, path, title, session_date, year, month, day,
                 undated_claims, dated_by) -> None:
        self.document_id = document_id
        self.path = path
        self.title = title
        self.session_date = session_date
        self.year = year
        self.month = month
        self.day = day
        self.undated_claims = undated_claims
        self.dated_by = dated_by


class UndatedClaimEntry:
    def __init__(self, claim_id, assertion, entities, conflict_relevant) -> None:
        self.claim_id = claim_id
        self.assertion = assertion
        self.entities = entities
        self.conflict_relevant = conflict_relevant


class PostgresSessionDatingRepository:
    def __init__(self, database: PostgresDatabase) -> None:
        self._database = database

    def walk(self) -> tuple[SessionDatingEntry, ...]:
        """Session documents in real-world order, with their current in-game
        date (DM overlay wins over capture-authored frontmatter) and the count
        of claims waiting to inherit."""
        with self._database.connection() as connection:
            rows = connection.execute(
                """
                SELECT sd.id::text, sdp.normalized_path,
                       coalesce(sr.frontmatter_json->>'name',
                                regexp_replace(split_part(sdp.normalized_path, '/', -1), '\\.md$', '')) AS title,
                       coalesce(sr.frontmatter_json->>'session_date',
                                (regexp_match(split_part(sdp.normalized_path, '/', -1), '^(\\d{4})[ -](\\d{2})[ -](\\d{2})'))[1]
                                  || '-' || (regexp_match(split_part(sdp.normalized_path, '/', -1), '^(\\d{4})[ -](\\d{2})[ -](\\d{2})'))[2]
                                  || '-' || (regexp_match(split_part(sdp.normalized_path, '/', -1), '^(\\d{4})[ -](\\d{2})[ -](\\d{2})'))[3]) AS real_date,
                       coalesce(d.campaign_year, (sr.frontmatter_json->'in_game_date'->>'year')::integer),
                       coalesce(d.campaign_month, (sr.frontmatter_json->'in_game_date'->>'month')::smallint),
                       coalesce(d.campaign_day, (sr.frontmatter_json->'in_game_date'->>'day')::smallint),
                       (SELECT count(*) FROM claims c
                        JOIN claim_evidence ce ON ce.claim_id = c.id
                        JOIN source_spans ss ON ss.id = ce.source_span_id
                        JOIN source_revisions sr2 ON sr2.id = ss.source_revision_id
                        WHERE sr2.source_document_id = sd.id
                          AND c.effective_from_year IS NULL
                          AND NOT EXISTS (SELECT 1 FROM claim_supersessions cs WHERE cs.superseded_claim_id = c.id)),
                       CASE WHEN d.source_document_id IS NOT NULL THEN 'dm'
                            WHEN sr.frontmatter_json ? 'in_game_date' THEN 'capture'
                            ELSE NULL END
                FROM source_documents sd
                JOIN source_document_paths sdp ON sdp.source_document_id = sd.id
                JOIN LATERAL (SELECT frontmatter_json FROM source_revisions
                              WHERE source_document_id = sd.id
                              ORDER BY captured_at DESC LIMIT 1) sr ON true
                LEFT JOIN document_campaign_dates d ON d.source_document_id = sd.id
                WHERE (sdp.normalized_path LIKE 'sessions/%'
                         AND sdp.normalized_path NOT LIKE 'sessions/prep/%'
                         AND sdp.normalized_path NOT LIKE 'sessions/archive/%')
                   OR sd.connector LIKE '%direct-input:session-note%'
                ORDER BY real_date NULLS LAST, sdp.normalized_path
                """
            ).fetchall()
        return tuple(
            SessionDatingEntry(
                document_id=row[0], path=row[1], title=row[2], session_date=row[3],
                year=row[4], month=row[5], day=row[6], undated_claims=int(row[7]),
                dated_by=row[8])
            for row in rows
        )

    def set_date(self, document_id: UUID, year: int, month: int, day: int,
                 reason: str | None) -> dict:
        with self._database.connection() as connection:
            row = connection.execute(
                "SELECT apply_session_document_date(%s, %s, %s, %s, %s)",
                (document_id, year, month, day, reason)).fetchone()
        return row[0]

    def inherit(self) -> dict:
        with self._database.connection() as connection:
            row = connection.execute(
                "SELECT inherit_claim_dates_from_documents()").fetchone()
        return row[0]

    def undated_claims(self, limit: int = 50) -> tuple[UndatedClaimEntry, ...]:
        """Undated current claims, conflict-ranked: claims linked to entities
        that have other dated claims surface first (the collisions 0097 cares
        about); unlinked or static lore last."""
        with self._database.connection() as connection:
            rows = connection.execute(
                """
                WITH undated AS (
                    SELECT c.id, c.assertion_text
                    FROM claims c
                    WHERE c.effective_from_year IS NULL
                      AND NOT EXISTS (SELECT 1 FROM claim_supersessions cs WHERE cs.superseded_claim_id = c.id)
                )
                SELECT u.id::text, left(u.assertion_text, 180),
                       coalesce(array_agg(DISTINCT e.canonical_name) FILTER (WHERE e.id IS NOT NULL), ARRAY[]::text[]),
                       EXISTS (
                           SELECT 1 FROM claims other
                           JOIN claim_related_entities cre2 ON cre2.claim_id = other.id
                           JOIN entities e2 ON e2.id = cre2.entity_id
                           WHERE other.effective_from_year IS NOT NULL
                             AND e2.id IN (SELECT entity_id FROM claim_related_entities WHERE claim_id = u.id)
                       ) AS conflict_relevant
                FROM undated u
                LEFT JOIN claim_related_entities cre ON cre.claim_id = u.id
                LEFT JOIN entities e ON e.id = cre.entity_id
                GROUP BY u.id, u.assertion_text
                ORDER BY conflict_relevant DESC,
                         count(DISTINCT e.id) DESC,
                         min(u.assertion_text)
                LIMIT %s
                """,
                (limit,),
            ).fetchall()
        return tuple(
            UndatedClaimEntry(claim_id=row[0], assertion=row[1],
                              entities=tuple(row[2] or ()),
                              conflict_relevant=bool(row[3]))
            for row in rows
        )
