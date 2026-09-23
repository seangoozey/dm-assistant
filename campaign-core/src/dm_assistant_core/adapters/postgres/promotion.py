"""PostgreSQL reads for the Promotion Pipeline facade (ADR-0018, TKT-0136)."""

from __future__ import annotations

from uuid import UUID

from dm_assistant_core.adapters.postgres.database import PostgresDatabase
from dm_assistant_core.application.promotion import ClaimSummary, StoredChangeSet


class PostgresPromotionReadRepository:
    """The narrow reads derive and commit-replay need; no canonical writes."""

    def __init__(self, database: PostgresDatabase) -> None:
        self._database = database

    def claims_for_entity(self, entity_id: UUID) -> tuple[ClaimSummary, ...]:
        with self._database.connection() as connection:
            rows = connection.execute(
                "SELECT id, assertion_text, predicate FROM claims "
                "WHERE subject_entity_id = %s ORDER BY recorded_at, id",
                (entity_id,),
            ).fetchall()
        return tuple(
            ClaimSummary(
                claim_id=row[0], assertion_text=str(row[1]), predicate=row[2]
            )
            for row in rows
        )

    def claims_by_ids(self, claim_ids: tuple[UUID, ...]) -> tuple[ClaimSummary, ...]:
        if not claim_ids:
            return ()
        with self._database.connection() as connection:
            rows = connection.execute(
                "SELECT id, assertion_text, predicate FROM claims WHERE id = ANY(%s)",
                (list(claim_ids),),
            ).fetchall()
        return tuple(
            ClaimSummary(
                claim_id=row[0], assertion_text=str(row[1]), predicate=row[2]
            )
            for row in rows
        )

    def change_set_for_key(self, idempotency_key: str) -> StoredChangeSet | None:
        with self._database.connection() as connection:
            row = connection.execute(
                "SELECT cs.idempotency_key, cs.id, cs.status::text, pv.version_number, "
                "cs.approval_id, pv.content_hash, pv.proposal_id FROM change_sets cs "
                "JOIN proposal_versions pv ON pv.id = cs.proposal_version_id "
                "WHERE cs.idempotency_key = %s "
                "OR cs.idempotency_key LIKE %s "
                "ORDER BY cs.requested_at DESC LIMIT 1",
                (idempotency_key, f"{idempotency_key}:%"),
            ).fetchone()
        if row is None:
            return None
        return StoredChangeSet(
            change_set_id=row[1],
            status=str(row[2]),
            reviewed_version=int(row[3]),
            approval_id=row[4],
            content_hash=str(row[5]),
            proposal_id=row[6],
        )

    def claim_targets_for_items(
        self, item_ids: tuple[UUID, ...]
    ) -> tuple[tuple[UUID, UUID], ...]:
        if not item_ids:
            return ()
        with self._database.connection() as connection:
            rows = connection.execute(
                "SELECT id, target_id FROM proposal_items "
                "WHERE id = ANY(%s) AND mutation_kind = 'create_claim'",
                (list(item_ids),),
            ).fetchall()
        return tuple((row[0], row[1]) for row in rows)
