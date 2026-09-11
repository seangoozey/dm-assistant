from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any
from uuid import UUID

from dm_assistant_core.adapters.postgres.entity_lookup import PostgresEntityLookupRepository


class Result:
    def fetchall(self) -> list[tuple[Any, ...]]:
        return [
            (
                UUID("11111111-1111-1111-1111-111111111111"),
                "Ruhrogue",
                "pc",
                "alias",
                "Ash",
            )
        ]


class Connection:
    sql = ""
    parameters: tuple[Any, ...] = ()

    def execute(self, sql: str, parameters: tuple[Any, ...]) -> Result:
        self.sql = sql
        self.parameters = parameters
        return Result()


class Database:
    def __init__(self) -> None:
        self.connection_value = Connection()

    @contextmanager
    def connection(self) -> Iterator[Connection]:
        yield self.connection_value


def test_entity_lookup_resolves_exact_aliases_with_match_provenance() -> None:
    database = Database()
    repository = PostgresEntityLookupRepository(database)  # type: ignore[arg-type]

    matches = repository.search("Ash", 10)

    assert matches[0].canonical_name == "Ruhrogue"
    assert matches[0].match_kind == "alias"
    assert matches[0].matched_name == "Ash"
    assert "FROM entity_aliases" in database.connection_value.sql
    assert "lower(a.normalized_alias)" in database.connection_value.sql
