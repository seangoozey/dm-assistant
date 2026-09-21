from dm_assistant_core.adapters.postgres.database import PostgresDatabase
from dm_assistant_core.application.prompt_configuration import PromptOverrideReceipt


class PostgresPromptOverrideRepository:
    def __init__(self, database: PostgresDatabase) -> None:
        self._database = database

    def load(self, purpose: str) -> tuple[str, str, object, object] | None:
        with self._database.connection() as connection:
            row = connection.execute(
                "SELECT prompt_text, version_label, receipt_id, updated_at "
                "FROM prompt_overrides WHERE purpose = %s",
                (purpose,),
            ).fetchone()
        return tuple(row) if row is not None else None

    def count_receipts(self, purpose: str) -> int:
        with self._database.connection() as connection:
            row = connection.execute(
                "SELECT count(*) FROM prompt_override_receipts WHERE purpose = %s",
                (purpose,),
            ).fetchone()
        return int(row[0]) if row is not None else 0

    def file_receipt(self, receipt: PromptOverrideReceipt, prompt_text: str | None) -> None:
        with self._database.connection() as connection:
            connection.execute(
                "INSERT INTO prompt_override_receipts "
                "(receipt_id, purpose, action, version_label, changed_at) "
                "VALUES (%s, %s, %s, %s, %s)",
                (
                    receipt.receipt_id,
                    receipt.purpose,
                    receipt.action,
                    receipt.version_label,
                    receipt.changed_at,
                ),
            )
            if prompt_text is None:
                connection.execute(
                    "DELETE FROM prompt_overrides WHERE purpose = %s", (receipt.purpose,))
            else:
                connection.execute(
                    "INSERT INTO prompt_overrides "
                    "(purpose, prompt_text, version_label, receipt_id, updated_at) "
                    "VALUES (%s, %s, %s, %s, %s) "
                    "ON CONFLICT (purpose) DO UPDATE SET "
                    "prompt_text = EXCLUDED.prompt_text, "
                    "version_label = EXCLUDED.version_label, "
                    "receipt_id = EXCLUDED.receipt_id, "
                    "updated_at = EXCLUDED.updated_at",
                    (
                        receipt.purpose,
                        prompt_text,
                        receipt.version_label,
                        receipt.receipt_id,
                        receipt.changed_at,
                    ),
                )

    def clear(self, purpose: str) -> None:
        with self._database.connection() as connection:
            connection.execute("DELETE FROM prompt_overrides WHERE purpose = %s", (purpose,))
