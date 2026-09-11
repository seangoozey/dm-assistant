from unittest.mock import MagicMock

import pytest

from dm_assistant_core.application.retrieval import ActiveProjection, PathRetrievalService
from tests.test_derived_retrieval import query
from tests.test_retrieval_paths import setup_path


def setup_service():
    records, links, path = setup_path()
    repository, registry = MagicMock(), MagicMock()
    repository.current_paths.return_value = records, links
    registry.active.return_value = ActiveProjection(
        "party", "v1", query("party").requester_visibility)
    return PathRetrievalService(repository, registry), repository, registry, path


def test_loaded_path_returns_target_as_context_never_answer():
    service, repository, registry, path = setup_service()
    result = service.query(query("party"), (path,), seed_ids=frozenset({"a"}))
    assert [e.record_id for e in result.evidence] == ["c"]
    assert result.evidence[0].role == "context"
    assert result.answer_mode == "insufficient_evidence"
    repository.current_paths.assert_called_once_with(query("party"), ("a", "b", "c"))
    assert registry.active.call_count == 2


@pytest.mark.parametrize("change", [{"scope_id": "dm"}, {"generation": "old"}])
def test_index_cannot_select_scope_or_generation(change):
    service, repository, _, path = setup_service()
    assert not service.query(query("party"), (path.model_copy(update=change),),
                             seed_ids=frozenset({"a"})).evidence
    repository.current_paths.assert_not_called()


def test_disabled_and_wrong_visibility_registry_fail_closed():
    service, repository, registry, path = setup_service()
    for active in (None, ActiveProjection("party", "v1", query().requester_visibility)):
        registry.active.return_value = active
        assert not service.query(query("party"), (path,), seed_ids=frozenset({"a"})).evidence
    repository.current_paths.assert_not_called()


def test_generation_switch_during_read_discards_result():
    service, _, registry, path = setup_service()
    registry.active.side_effect = [registry.active.return_value, None]
    assert not service.query(query("party"), (path,), seed_ids=frozenset({"a"})).evidence


def test_target_facets_applied_after_path_authorization():
    service, _, _, path = setup_service()
    q = query("party").model_copy(update={"tags": ("no-match",)})
    assert not service.query(q, (path,), seed_ids=frozenset({"a"})).evidence


def test_hidden_intermediate_cannot_be_bypassed_by_service():
    service, repository, _, path = setup_service()
    records, links = repository.current_paths.return_value
    repository.current_paths.return_value = tuple(r for r in records if r.record_id != "b"), links
    assert not service.query(query("party"), (path,), seed_ids=frozenset({"a"})).evidence


def test_empty_and_oversized_requests_do_not_read():
    service, repository, _, path = setup_service()
    assert not service.query(query("party"), (), seed_ids=frozenset({"a"})).evidence
    with pytest.raises(ValueError):
        service.query(query("party"), (path,) * 101, seed_ids=frozenset({"a"}))
    repository.current_paths.assert_not_called()
