"""PostgreSQL write for the orphan no-owner disposition (TKT-0138 slice 2)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import psycopg

from dm_assistant_core.adapters.postgres.database import PostgresDatabase


class OrphanDispositionError(ValueError):
    """The disposition was refused; the message is user-facing."""


class PostgresOrphanDispositionRepository:
    """Call the migration-owned dispose_claim_owner function (0074)."""

    def __init__(self, database: PostgresDatabase) -> None:
        self._database = database

    def dispose(self, claim_id: UUID, reason: str) -> dict[str, Any]:
        try:
            with self._database.connection() as connection:
                row = connection.execute(
                    "SELECT dispose_claim_owner(%s, %s)", (claim_id, reason)
                ).fetchone()
        except psycopg.DatabaseError as error:
            if error.sqlstate == "P0001":
                raise OrphanDispositionError(str(error).splitlines()[0]) from error
            raise
        if row is None:
            raise RuntimeError("dispose_claim_owner returned no result")
        return dict(row[0])
