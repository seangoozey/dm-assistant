from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from dm_assistant_core.adapters.postgres.retrieval import PostgresRetrievalRepository
from dm_assistant_core.application.retrieval import DerivedRetrievalService
from tests.test_derived_retrieval import query, suggestion
from tests.test_evidence_comparison import record


def test_service_reloads_records_and_rejects_changed_snapshot():
    original = record()
    repository = MagicMock()
    repository.current_records.side_effect = [(original,), (original.model_copy(
        update={"assertion": "Corrected fact"}),)]
    service = DerivedRetrievalService(repository)
    assert service.query(query(), (suggestion(original),)).evidence
    assert not service.query(query(), (suggestion(original),)).evidence
    assert repository.current_records.call_count == 2


def test_empty_and_oversize_do_not_read_database():
    repository = MagicMock()
    service = DerivedRetrievalService(repository)
    assert not service.query(query(), ()).evidence
    with pytest.raises(ValueError):
        service.query(query(), (suggestion(record()),) * 101)
    repository.current_records.assert_not_called()


def test_exact_reader_single_parameterized_snapshot_and_filters(monkeypatch):
    database = MagicMock()
    connection = database.connection.return_value.__enter__.return_value
    public = record(str(uuid4()))
    hidden = record(str(uuid4()), visibility="dm")
    retired = record(str(uuid4()), state="superseded")
    unrelated = record(str(uuid4()))
    connection.execute.return_value.fetchall.return_value = [(r, "binding") for r in
                                                            (public, hidden, retired, unrelated)]
    repository = PostgresRetrievalRepository(database)
    monkeypatch.setattr(repository, "_to_record", lambda row: row[0])
    ids = (public.record_id, hidden.record_id, retired.record_id)
    assert repository.current_records(query("party"), ids) == (
        public.model_copy(update={"evidence_binding": "binding"}),)
    connection.execute.assert_called_once()
    sql, params = connection.execute.call_args.args
    assert "ANY(%s::uuid[])" in sql
    assert public.record_id not in sql
    assert "claim_supersessions" in sql
    assert "import_candidates" not in sql
    assert len(params[0]) == 3


def test_invalid_ids_fail_before_sql():
    database = MagicMock()
    repository = PostgresRetrievalRepository(database)
    with pytest.raises(ValueError):
        repository.current_records(query(), ("not-a-uuid",))
    database.connection.assert_not_called()
