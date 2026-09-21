from dm_assistant_core.adapters.postgres.database import PostgresDatabase
from dm_assistant_core.application.template_vocabularies import VocabularyChangeReceipt


class PostgresTemplateVocabularyRepository:
    def __init__(self, database: PostgresDatabase) -> None:
        self._database = database

    def load(self, vocabulary: str) -> dict[str, bool]:
        with self._database.connection() as connection:
            rows = connection.execute(
                "SELECT value, retired FROM template_vocabularies WHERE vocabulary = %s",
                (vocabulary,),
            ).fetchall()
        return {row[0]: bool(row[1]) for row in rows}

    def record(self, receipt: VocabularyChangeReceipt, retired: bool) -> None:
        with self._database.connection() as connection:
            connection.execute(
                "INSERT INTO vocabulary_receipts "
                "(receipt_id, vocabulary, action, value, changed_at) VALUES (%s, %s, %s, %s, %s)",
                (
                    receipt.receipt_id,
                    receipt.vocabulary,
                    receipt.action,
                    receipt.value,
                    receipt.changed_at,
                ),
            )
            connection.execute(
                "INSERT INTO template_vocabularies (vocabulary, value, retired, receipt_id, updated_at) "
                "VALUES (%s, %s, %s, %s, %s) "
                "ON CONFLICT (vocabulary, value) DO UPDATE SET "
                "retired = EXCLUDED.retired, receipt_id = EXCLUDED.receipt_id, "
                "updated_at = EXCLUDED.updated_at",
                (
                    receipt.vocabulary,
                    receipt.value,
                    retired,
                    receipt.receipt_id,
                    receipt.changed_at,
                ),
            )
