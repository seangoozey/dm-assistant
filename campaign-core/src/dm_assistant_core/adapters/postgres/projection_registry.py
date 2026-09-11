"""Core-only durable index pointer. Callers publish only fully validated builds.

This stores lifecycle metadata, not an authorization grant or build verification.
Database instances are campaign-isolated; authenticated visibility selects scope.
"""

import hashlib
from uuid import UUID

from dm_assistant_core.adapters.postgres.database import PostgresDatabase
from dm_assistant_core.application.projection_artifact import ProjectionArtifactReader
from dm_assistant_core.application.retrieval import ActiveProjection
from dm_assistant_core.domain.projection_build import validate_manifest
from dm_assistant_core.domain.retrieval import RequesterVisibility, RetrievalQuery, RetrievalRecord
from dm_assistant_core.domain.retrieval_paths import CurrentLink


def projection_scope(visibility: RequesterVisibility) -> str:
    return hashlib.sha256(visibility.model_dump_json().encode()).hexdigest()


class PostgresProjectionRegistry:
    def __init__(self, database: PostgresDatabase) -> None:
        self._database = database

    def active(self, visibility: RequesterVisibility) -> ActiveProjection | None:
        scope = projection_scope(visibility)
        with self._database.connection() as connection:
            row = connection.execute(
                "SELECT r.visibility_json, r.generation, r.version "
                "FROM retrieval_projection_registry r JOIN retrieval_projection_builds b "
                "ON b.generation=r.generation AND b.scope_id=r.scope_id "
                "WHERE r.scope_id = %s AND b.status='validated' "
                "AND b.artifact_verified_hash=b.manifest_hash", (scope,),
            ).fetchone()
        if row is None or row[0] != visibility.model_dump_json() or row[1] is None:
            return None
        # Version prevents switching away and back from reviving an in-flight read.
        return ActiveProjection(scope, f"{row[1]}:{row[2]}", visibility)

    def record_validated_snapshot(
        self, generation: UUID, query: RetrievalQuery,
        records: tuple[RetrievalRecord, ...], links: tuple[CurrentLink, ...],
    ) -> str:
        """Register a Core-owned manifest; never accept these inputs from an index.

        External artifact verification and completeness checks remain producer duties.
        A generation is immutable: retries must reproduce the identical manifest.
        """
        digest = validate_manifest(query, records, links)
        scope = projection_scope(query.requester_visibility)
        with self._database.connection() as connection:
            connection.execute(
                "INSERT INTO retrieval_projection_builds "
                "(generation,scope_id,manifest_hash,node_count,edge_count,status) "
                "VALUES (%s,%s,%s,%s,%s,'validated') ON CONFLICT DO NOTHING",
                (generation, scope, digest, len(records), len(links)),
            )
            row = connection.execute(
                "SELECT scope_id,manifest_hash,status FROM retrieval_projection_builds "
                "WHERE generation=%s FOR SHARE", (generation,),
            ).fetchone()
            if row != (scope, digest, "validated"):
                raise ValueError("generation already has a different or revoked manifest")
        return digest

    def verify_artifact(
        self, generation: UUID, query: RetrievalQuery, reader: ProjectionArtifactReader,
    ) -> str:
        """Compare independent stored-index contents with the immutable Core manifest.

        Reader is a trusted configured adapter, never a caller-provided upload.
        Verification is only durable for sealed generations; mutable indexes need
        a new generation and read-back. Does not prove semantic retrieval quality.
        """
        scope = projection_scope(query.requester_visibility)
        artifact = reader.read_generation(generation, scope)
        if artifact.generation != generation or artifact.scope_id != scope:
            raise ValueError("artifact scope or generation mismatch")
        digest = validate_manifest(query, artifact.records, artifact.links)
        with self._database.connection() as connection:
            row = connection.execute(
                "UPDATE retrieval_projection_builds "
                "SET artifact_verified_hash=%s, artifact_verified_at=now() "
                "WHERE generation=%s AND scope_id=%s AND manifest_hash=%s "
                "AND node_count=%s AND edge_count=%s AND status='validated' "
                "RETURNING generation",
                (digest, generation, scope, digest, len(artifact.records), len(artifact.links)),
            ).fetchone()
            if row is None:
                raise ValueError("artifact does not match a validated manifest")
        return digest

    def publish(
        self, visibility: RequesterVisibility, generation: UUID | None, *, expected_version: int,
    ) -> int:
        """Compare-and-swap pointer, or disable it with None. No automatic retries.

        expected_version=0 creates a scope. Existing rows require their exact
        version. Publishing a prior build creates a new version, preserving ABA
        protection. The build validator is responsible for readiness beforehand.
        """
        if expected_version < 0:
            raise ValueError("expected version cannot be negative")
        scope, encoded = projection_scope(visibility), visibility.model_dump_json()
        with self._database.connection() as connection:
            if generation is not None:
                build = connection.execute(
                    "SELECT generation FROM retrieval_projection_builds "
                    "WHERE generation=%s AND scope_id=%s AND status='validated' "
                    "AND artifact_verified_hash=manifest_hash FOR SHARE",
                    (generation, scope),
                ).fetchone()
                if build is None:
                    raise ValueError("generation has no validated snapshot for this scope")
            if expected_version == 0:
                row = connection.execute(
                    "INSERT INTO retrieval_projection_registry "
                    "(scope_id, visibility_json, generation, version) VALUES (%s, %s, %s, 1) "
                    "ON CONFLICT (scope_id) DO NOTHING RETURNING version",
                    (scope, encoded, generation),
                ).fetchone()
            else:
                row = connection.execute(
                    "UPDATE retrieval_projection_registry SET generation = %s, "
                    "version = version + 1, updated_at = now() "
                    "WHERE scope_id = %s AND visibility_json = %s AND version = %s "
                    "RETURNING version", (generation, scope, encoded, expected_version),
                ).fetchone()
            if row is None:
                raise ValueError("projection registry changed; reload before publishing")
        return int(row[0])
