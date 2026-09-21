from uuid import UUID

from dm_assistant_core.adapters.postgres.database import PostgresDatabase
from dm_assistant_core.application.dossier import DossierDecisionReceipt


class PostgresDossierRepository:
    def __init__(self, database: PostgresDatabase) -> None:
        self._database = database

    def latest_by_claim(self, entity_id: UUID) -> dict[UUID, str]:
        with self._database.connection() as connection:
            rows = connection.execute(
                "SELECT DISTINCT ON (claim_id) claim_id, action "
                "FROM dossier_decisions WHERE entity_id = %s "
                "ORDER BY claim_id, decided_at DESC",
                (entity_id,),
            ).fetchall()
        return {row[0]: row[1] for row in rows}

    def record(self, receipt: DossierDecisionReceipt) -> None:
        with self._database.connection() as connection:
            connection.execute(
                "INSERT INTO dossier_decisions "
                "(receipt_id, entity_id, claim_id, action, decided_at) "
                "VALUES (%s, %s, %s, %s, %s)",
                (
                    receipt.receipt_id,
                    receipt.entity_id,
                    receipt.claim_id,
                    receipt.action,
                    receipt.decided_at,
                ),
            )
