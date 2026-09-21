"""Conflict review queue (TKT-0097): deterministic detection + audited repair.

Detection is mechanical and deliberately narrow so the queue launches
trustworthy: observed real-play deaths with known dates versus current claims
about the same entity dated strictly later. Time dissolves what it can (the
death date); authority is shown on both sides. Decided pairs never reappear.
"""

from uuid import UUID

from dm_assistant_core.adapters.postgres.database import PostgresDatabase


class ConflictPair:
    def __init__(self, entity_name, claim_a_id, claim_a_assertion, claim_a_date,
                 claim_b_id, claim_b_assertion, claim_b_date, claim_b_authority,
                 claim_b_state) -> None:
        self.entity_name = entity_name
        self.claim_a_id = claim_a_id
        self.claim_a_assertion = claim_a_assertion
        self.claim_a_date = claim_a_date
        self.claim_b_id = claim_b_id
        self.claim_b_assertion = claim_b_assertion
        self.claim_b_date = claim_b_date
        self.claim_b_authority = claim_b_authority
        self.claim_b_state = claim_b_state


class PostgresConflictReviewRepository:
    def __init__(self, database: PostgresDatabase) -> None:
        self._database = database

    def queue(self) -> tuple[ConflictPair, ...]:
        """Observed, dated deaths versus strictly-later claims about the dead
        entity. Historical journal mentions are undated, so time itself keeps
        them out — only dated post-death assertions surface."""
        with self._database.connection() as connection:
            rows = connection.execute(
                r"""
                WITH deaths AS (
                    -- The dead record's own name sits next to a death word in an
                    -- observed real-play claim. Subjectless claims count: the death
                    -- links the entity through claim_related_entities (the live
                    -- Martin Faeroth case), so both linkages are checked.
                    SELECT DISTINCT c.id AS death_id, e.id AS entity_id,
                           c.effective_from_year AS y, c.effective_from_month AS m,
                           c.effective_from_day AS d
                    FROM claims c
                    JOIN entities e ON (
                        e.id = c.subject_entity_id
                        OR EXISTS (SELECT 1 FROM claim_related_entities cre
                                   WHERE cre.claim_id = c.id AND cre.entity_id = e.id))
                    WHERE c.state = 'observed' AND c.authority IN ('real_play', 'dm_correction')
                      AND c.effective_from_year IS NOT NULL
                      AND c.assertion_text ~* ('(^|[^[:alnum:]])' || e.canonical_name
                               || '([[:space:]]+(was|is|has|had))?[[:space:]]*(died|dead|slain|killed)\M')
                      AND NOT EXISTS (SELECT 1 FROM claim_supersessions cs WHERE cs.superseded_claim_id = c.id)
                )
                SELECT e.canonical_name,
                       d.death_id, da.assertion_text,
                       (d.y || '-' || lpad(d.m::text, 2, '0') || '-' || lpad(d.d::text, 2, '0')),
                       b.id::text, left(b.assertion_text, 400),
                       (b.effective_from_year || '-' || lpad(coalesce(b.effective_from_month, 0)::text, 2, '0') || '-' || lpad(coalesce(b.effective_from_day, 0)::text, 2, '0')),
                       b.authority::text, b.state::text
                FROM deaths d
                JOIN entities e ON e.id = d.entity_id
                JOIN claims da ON da.id = d.death_id
                JOIN claims b ON (
                    b.subject_entity_id = d.entity_id
                    OR EXISTS (SELECT 1 FROM claim_related_entities cre
                               WHERE cre.claim_id = b.id AND cre.entity_id = d.entity_id))
                 AND b.id <> d.death_id
                 AND b.effective_from_year IS NOT NULL
                 AND (b.effective_from_year > d.y
                      OR (b.effective_from_year = d.y AND coalesce(b.effective_from_month, 0) > coalesce(d.m, 0))
                      OR (b.effective_from_year = d.y AND coalesce(b.effective_from_month, 0) = coalesce(d.m, 0)
                          AND coalesce(b.effective_from_day, 0) > coalesce(d.d, 0)))
                 AND NOT EXISTS (SELECT 1 FROM claim_supersessions cs WHERE cs.superseded_claim_id = b.id)
                WHERE NOT EXISTS (SELECT 1 FROM conflict_decisions cd
                                  WHERE cd.claim_a_id = d.death_id AND cd.claim_b_id = b.id)
                ORDER BY e.canonical_name, b.effective_from_year, b.id
                """
            ).fetchall()
        return tuple(
            ConflictPair(
                entity_name=row[0], claim_a_id=str(row[1]), claim_a_assertion=row[2],
                claim_a_date=row[3], claim_b_id=row[4], claim_b_assertion=row[5],
                claim_b_date=row[6], claim_b_authority=row[7], claim_b_state=row[8])
            for row in rows
        )

    def decide(self, claim_a: UUID, claim_b: UUID, action: str, reason: str) -> dict:
        with self._database.connection() as connection:
            row = connection.execute(
                "SELECT apply_conflict_decision(%s, %s, %s, %s)",
                (claim_a, claim_b, action, reason)).fetchone()
        return row[0]
