from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from dm_assistant_core.adapters.postgres.retrieval import PostgresRetrievalRepository
from tests.test_derived_retrieval import query
from tests.test_evidence_comparison import record


def test_links_and_records_share_read_only_repeatable_snapshot(monkeypatch):
    database = MagicMock()
    connection = database.connection.return_value.__enter__.return_value
    a, b, hidden, span = (str(uuid4()) for _ in range(4))
    repository = PostgresRetrievalRepository(database)
    seen = []

    def current(q, ids, conn):
        seen.append(conn)
        assert not q.tags
        assert "REPEATABLE READ READ ONLY" in conn.execute.call_args.args[0]
        return (record(a), record(b))

    monkeypatch.setattr(repository, "_current_records", current)
    connection.execute.return_value.fetchall.return_value = [(a, b, span), (a, hidden, span)]
    records, links = repository.current_paths(query(), (a, b, hidden))
    assert seen == [connection]
    assert len(records) == 2
    assert len(links) == 1
    assert links[0].edge_id == f"shared-span:{span}:{a}:{b}"
    assert {s.record_id for s in links[0].evidence} == {a, b}
    database.connection.assert_called_once()
    assert "ANY(%s::uuid[])" in connection.execute.call_args.args[0]


@pytest.mark.parametrize("ids", [(), ("bad",), (str(uuid4()),) * 2001])
def test_invalid_or_empty_path_request_never_connects(ids):
    database = MagicMock()
    repository = PostgresRetrievalRepository(database)
    if ids:
        with pytest.raises(ValueError):
            repository.current_paths(query(), ids)
    else:
        assert repository.current_paths(query(), ids) == ((), ())
    database.connection.assert_not_called()
