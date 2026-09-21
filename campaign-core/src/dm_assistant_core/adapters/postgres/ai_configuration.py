from dm_assistant_core.adapters.postgres.database import PostgresDatabase
from dm_assistant_core.application.ai_configuration import ActivationReceipt


class PostgresAIConfigurationRepository:
    def __init__(self, database: PostgresDatabase) -> None:
        self._database = database

    def latest_by_purpose(self) -> dict[str, ActivationReceipt]:
        with self._database.connection() as connection:
            rows = connection.execute(
                """
                SELECT DISTINCT ON (purpose)
                    receipt_id, purpose, profile_key, prompt_version, activated_at
                FROM ai_configuration_activations
                ORDER BY purpose, activated_at DESC
                """
            ).fetchall()
        return {
            row[1]: ActivationReceipt(
                receipt_id=row[0],
                purpose=row[1],
                profile_key=row[2],
                prompt_version=row[3],
                activated_at=row[4],
            )
            for row in rows
        }

    def activate(self, receipt: ActivationReceipt) -> None:
        with self._database.connection() as connection:
            connection.execute(
                """
                INSERT INTO ai_configuration_activations (
                    receipt_id, purpose, profile_key, prompt_version, activated_at
                ) VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    receipt.receipt_id,
                    receipt.purpose,
                    receipt.profile_key,
                    receipt.prompt_version,
                    receipt.activated_at,
                ),
            )
