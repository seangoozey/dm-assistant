"""PostgreSQL implementation of atomic change-set application."""

from typing import Any, cast

import psycopg

from dm_assistant_core.adapters.postgres.database import PostgresDatabase
from dm_assistant_core.domain.change_sets import (
    ApplyChangeSetCommand,
    ChangeSetReceipt,
    ChangeSetRejectedError,
)


class PostgresChangeSetRepository:
    """Call the database's single transaction-bound canonical write function."""

    def __init__(self, database: PostgresDatabase) -> None:
        self._database = database

    def apply(self, command: ApplyChangeSetCommand) -> ChangeSetReceipt:
        try:
            with self._database.connection() as connection:
                row = connection.execute(
                    "SELECT apply_change_set(%s, %s, %s, %s)",
                    (
                        command.change_set_id,
                        command.reviewed_version,
                        command.approval_id,
                        command.content_hash,
                    ),
                ).fetchone()
        except psycopg.DatabaseError as error:
            if error.sqlstate == "P0001":
                raise ChangeSetRejectedError(str(error).splitlines()[0]) from error
            raise

        if row is None:
            raise RuntimeError("apply_change_set returned no receipt")
        payload = cast(dict[str, Any], row[0])
        return ChangeSetReceipt.model_validate(payload)
