from typing import Any
from uuid import UUID

from dm_assistant_core.adapters.postgres.database import PostgresDatabase
from dm_assistant_core.application.claim_reattribution import ReattributionReceipt


class PostgresClaimReattributionRepository:
    def __init__(self, database: PostgresDatabase) -> None:
        self._database = database

    def claim_subject(self, claim_id: UUID) -> UUID | None:
        with self._database.connection() as connection:
            row = connection.execute(
                "SELECT subject_entity_id FROM claims WHERE id = %s", (claim_id,)
            ).fetchone()
        return row[0] if row is not None else None

    def move(self, receipt: ReattributionReceipt, reason: str) -> None:
        with self._database.connection() as connection:
            connection.execute(
                "UPDATE claims SET subject_entity_id = %s WHERE id = %s",
                (receipt.new_entity_id, receipt.claim_id),
            )
            connection.execute(
                "INSERT INTO claim_reattributions "
                "(receipt_id, claim_id, old_entity_id, new_entity_id, reason, moved_at) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (
                    receipt.receipt_id, receipt.claim_id,
                    receipt.old_entity_id, receipt.new_entity_id,
                    reason, receipt.moved_at,
                ),
            )

    def moved_from(self, entity_id: UUID) -> list[tuple[Any, ...]]:
        with self._database.connection() as connection:
            rows = connection.execute(
                """
                SELECT cr.claim_id, c.assertion_text, c.state,
                       cr.new_entity_id, e.canonical_name, cr.moved_at, cr.reason
                FROM claim_reattributions cr
                JOIN claims c ON c.id = cr.claim_id
                JOIN entities e ON e.id = cr.new_entity_id
                WHERE cr.old_entity_id = %s
                ORDER BY cr.moved_at DESC
                """,
                (entity_id,),
            ).fetchall()
        return [tuple(row) for row in rows]
