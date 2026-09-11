from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from dm_assistant_core.adapters.postgres.projection_registry import projection_scope
from dm_assistant_core.application.projection_artifact import ProjectionArtifact
from tests.test_derived_retrieval import query
from tests.test_evidence_comparison import record
from tests.test_projection_registry import fixture


def test_readback_binds_manifest_counts_scope_and_generation():
    registry, connection = fixture()
    generation = uuid4()
    q = query()
    reader = MagicMock()
    reader.read_generation.return_value = ProjectionArtifact(
        generation, projection_scope(q.requester_visibility),
        (record(evidence_binding="bound"),), ())
    connection.execute.return_value.fetchone.return_value = (generation,)
    digest = registry.verify_artifact(generation, q, reader)
    scope = projection_scope(q.requester_visibility)
    reader.read_generation.assert_called_once_with(generation, scope)
    sql, parameters = connection.execute.call_args.args
    assert "manifest_hash=%s" in sql and "node_count=%s" in sql and "edge_count=%s" in sql
    assert parameters == (digest, generation, scope, digest, 1, 0)


@pytest.mark.parametrize("wrong_scope", [True, False])
def test_wrong_identity_never_marks_verified(wrong_scope):
    registry, connection = fixture()
    generation = uuid4()
    q = query()
    reader = MagicMock()
    reader.read_generation.return_value = ProjectionArtifact(
        generation if wrong_scope else uuid4(),
        "wrong" if wrong_scope else projection_scope(q.requester_visibility), (), ())
    with pytest.raises(ValueError, match="mismatch"):
        registry.verify_artifact(generation, q, reader)
    connection.execute.assert_not_called()


def test_hash_mismatch_missing_or_revoked_manifest_cannot_verify():
    registry, connection = fixture()
    q, generation = query(), uuid4()
    reader = MagicMock()
    reader.read_generation.return_value = ProjectionArtifact(
        generation, projection_scope(q.requester_visibility), (), ())
    connection.execute.return_value.fetchone.return_value = None
    with pytest.raises(ValueError, match="does not match"):
        registry.verify_artifact(generation, q, reader)


def test_partial_read_failure_never_marks_verified():
    registry, connection = fixture()
    reader = MagicMock()
    reader.read_generation.side_effect = RuntimeError("incomplete enumeration")
    with pytest.raises(RuntimeError):
        registry.verify_artifact(uuid4(), query(), reader)
    connection.execute.assert_not_called()


def test_publish_and_active_require_artifact_verification():
    registry, connection = fixture()
    registry.active(query().requester_visibility)
    assert "artifact_verified_hash=b.manifest_hash" in connection.execute.call_args.args[0]
    connection.execute.return_value.fetchone.return_value = None
    with pytest.raises(ValueError):
        registry.publish(query().requester_visibility, uuid4(), expected_version=0)
    assert "artifact_verified_hash=manifest_hash" in connection.execute.call_args.args[0]
