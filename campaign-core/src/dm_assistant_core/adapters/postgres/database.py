"""Narrow PostgreSQL adapter used by application composition only."""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import psycopg
from psycopg import Connection


class PostgresDatabase:
    """Own PostgreSQL connections behind the Campaign Core boundary."""

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    @contextmanager
    def connection(self) -> Iterator[Connection[Any]]:
        with psycopg.connect(self._dsn) as connection:
            yield connection

    def is_ready(self) -> bool:
        with self.connection() as connection:
            value = connection.execute("SELECT 1").fetchone()
        return value == (1,)

