from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from dm_assistant_core.adapters.postgres.projection_registry import (
    PostgresProjectionRegistry,
    projection_scope,
)
from dm_assistant_core.domain.retrieval import RequesterVisibility


def fixture():
    database = MagicMock()
    connection = database.connection.return_value.__enter__.return_value
    return PostgresProjectionRegistry(database), connection


def test_scopes_separate_dm_party_and_characters():
    scopes = [RequesterVisibility(role="dm"), RequesterVisibility(role="party"),
              RequesterVisibility(role="character", character_id="a"),
              RequesterVisibility(role="character", character_id="b")]
    assert len({projection_scope(v) for v in scopes}) == 4


@pytest.mark.parametrize("row", [None, ("wrong", uuid4(), 1), ('{"role":"dm"}', None, 2)])
def test_missing_disabled_or_mismatched_scope_returns_nothing(row):
    registry, connection = fixture()
    connection.execute.return_value.fetchone.return_value = row
    assert registry.active(RequesterVisibility(role="dm")) is None


def test_generation_identity_includes_monotonic_version():
    registry, connection = fixture()
    visibility = RequesterVisibility(role="dm")
    generation = uuid4()
    connection.execute.return_value.fetchone.side_effect = [
        (visibility.model_dump_json(), generation, 1),
        (visibility.model_dump_json(), generation, 3)]
    assert registry.active(visibility) != registry.active(visibility)


@pytest.mark.parametrize("version", [0, 1])
def test_publish_is_parameterized_compare_and_swap(version):
    registry, connection = fixture()
    connection.execute.return_value.fetchone.return_value = (version + 1,)
    assert registry.publish(RequesterVisibility(role="party"), None,
                            expected_version=version) == version + 1
    sql = connection.execute.call_args.args[0]
    assert "DO NOTHING" in sql if version == 0 else "version = %s" in sql


def test_lost_publish_race_fails():
    registry, connection = fixture()
    connection.execute.return_value.fetchone.return_value = None
    with pytest.raises(ValueError, match="changed"):
        registry.publish(RequesterVisibility(role="dm"), None, expected_version=4)


def test_unvalidated_build_cannot_publish():
    registry, connection = fixture()
    connection.execute.return_value.fetchone.return_value = None
    with pytest.raises(ValueError, match="no validated"):
        registry.publish(RequesterVisibility(role="party"), uuid4(), expected_version=0)
    connection.execute.assert_called_once()
