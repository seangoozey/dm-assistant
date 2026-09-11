from dm_assistant_core.adapters.postgres.database import PostgresDatabase
from dm_assistant_core.application.ai_configuration import ActivationReceipt


class PostgresAIConfigurationRepository:
    def __init__(self, database: PostgresDatabase) -> None:
        self._database = database

    def latest(self) -> ActivationReceipt | None:
        with self._database.connection() as connection:
            row = connection.execute(
                """
                SELECT receipt_id, profile_key, prompt_version, activated_at
                FROM ai_configuration_activations
                ORDER BY activated_at DESC
                LIMIT 1
                """
            ).fetchone()
        return (
            ActivationReceipt(
                receipt_id=row[0], profile_key=row[1], prompt_version=row[2], activated_at=row[3]
            )
            if row
            else None
        )

    def activate(self, receipt: ActivationReceipt) -> None:
        with self._database.connection() as connection:
            connection.execute(
                """
                INSERT INTO ai_configuration_activations (
                    receipt_id, profile_key, prompt_version, activated_at
                ) VALUES (%s, %s, %s, %s)
                """,
                (
                    receipt.receipt_id,
                    receipt.profile_key,
                    receipt.prompt_version,
                    receipt.activated_at,
                ),
            )
