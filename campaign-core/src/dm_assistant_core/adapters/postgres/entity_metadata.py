"""PostgreSQL exact proposal path for entity kind and tag changes."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from hashlib import sha256
from uuid import UUID, uuid4

from psycopg.types.json import Jsonb

from dm_assistant_core.adapters.postgres.candidate_proposals import (
    PostgresCandidateProposalRepository,
)
from dm_assistant_core.adapters.postgres.database import PostgresDatabase
from dm_assistant_core.application import (
    ApproveCandidateProposalCommand,
    CandidateProposalApproval,
)
from dm_assistant_core.application.entity_metadata import (
    EntityMetadataProposalError,
    EntityMetadataProposalItem,
    EntityMetadataProposalVersion,
    ProposeEntityMetadataCommand,
)


class PostgresEntityMetadataProposalRepository:
    def __init__(self, database: PostgresDatabase) -> None:
        self._database = database
        self._approval_repository = PostgresCandidateProposalRepository(database)

    def create(self, command: ProposeEntityMetadataCommand) -> EntityMetadataProposalVersion:
        proposal_id, workflow_id, version_id, item_id = uuid4(), uuid4(), uuid4(), uuid4()
        created_at = datetime.now(UTC)
        with self._database.connection() as connection:
            row = connection.execute(
                """
                SELECT e.canonical_name, e.entity_type, kd.canonical_key,
                       (SELECT max(version) FROM kind_versions WHERE kind_id = kd.id),
                       ARRAY(SELECT normalized_name FROM current_entity_tags
                             WHERE entity_id = e.id ORDER BY normalized_name)
                FROM entities e
                LEFT JOIN kind_definitions kd ON kd.id = e.entity_kind_id
                WHERE e.id = %s
                FOR UPDATE OF e
                """,
                (command.entity_id,),
            ).fetchone()
            if row is None:
                raise EntityMetadataProposalError("entity does not exist")
            target_kind = connection.execute(
                """
                SELECT kd.id, max(kv.version)
                FROM kind_definitions kd
                JOIN kind_versions kv ON kv.kind_id = kd.id
                WHERE kd.namespace = 'entity' AND kd.canonical_key = %s
                  AND kd.status = 'active'
                GROUP BY kd.id
                """,
                (command.entity_kind.value,),
            ).fetchone()
            if target_kind is None:
                raise EntityMetadataProposalError("requested entity kind is not active")
            current_kind = str(row[2] or row[1])
            if current_kind in {"pc", "npc"} and command.entity_kind.value != current_kind:
                raise EntityMetadataProposalError("PC and NPC agency kinds cannot be reclassified")
            before = _metadata_payload(
                command.entity_id,
                canonical_name=str(row[0]),
                entity_kind=current_kind,
                entity_kind_version=int(row[3]) if row[3] is not None else None,
                tags=tuple(str(tag) for tag in row[4]),
            )
            after = _metadata_payload(
                command.entity_id,
                canonical_name=str(row[0]),
                entity_kind=command.entity_kind.value,
                entity_kind_version=int(target_kind[1]),
                tags=command.tags,
            )
            if before == after:
                raise EntityMetadataProposalError("entity metadata is unchanged")
            content_hash = _content_hash(item_id, command.entity_id, before, after)
            connection.execute(
                "INSERT INTO workflow_sessions (id, kind, started_at) "
                "VALUES (%s, 'lore_entry', %s)",
                (workflow_id, created_at),
            )
            connection.execute(
                "INSERT INTO proposals (id, workflow_session_id, status, created_at) "
                "VALUES (%s, %s, 'pending', %s)",
                (proposal_id, workflow_id, created_at),
            )
            connection.execute(
                "INSERT INTO proposal_versions "
                "(id, proposal_id, version_number, content_hash, created_at) "
                "VALUES (%s, %s, 1, %s, %s)",
                (version_id, proposal_id, content_hash, created_at),
            )
            connection.execute(
                "INSERT INTO proposal_items "
                "(id, proposal_version_id, sequence, mutation_kind, target_type, target_id, "
                "before_json, after_json) "
                "VALUES (%s, %s, 1, 'update_entity_metadata', 'entity', %s, %s, %s)",
                (item_id, version_id, command.entity_id, Jsonb(before), Jsonb(after)),
            )
        result = self.get(proposal_id)
        if result is None:
            raise RuntimeError("entity metadata proposal could not be loaded")
        return result

    def get(self, proposal_id: UUID) -> EntityMetadataProposalVersion | None:
        with self._database.connection() as connection:
            row = connection.execute(
                """
                SELECT p.workflow_session_id, p.status::text, pv.id, pv.version_number,
                       pv.content_hash, pv.created_at, pi.id, pi.target_id,
                       pi.before_json, pi.after_json
                FROM proposals p
                JOIN proposal_versions pv ON pv.proposal_id = p.id
                JOIN proposal_items pi ON pi.proposal_version_id = pv.id
                WHERE p.id = %s AND pi.mutation_kind = 'update_entity_metadata'
                ORDER BY pv.version_number DESC LIMIT 1
                """,
                (proposal_id,),
            ).fetchone()
        if row is None:
            return None
        return EntityMetadataProposalVersion(
            proposal_id=proposal_id,
            workflow_session_id=row[0],
            status=str(row[1]),
            version_id=row[2],
            version_number=int(row[3]),
            content_hash=str(row[4]),
            created_at=row[5].isoformat(),
            item=EntityMetadataProposalItem(
                item_id=row[6], target_id=row[7], before=dict(row[8]), after=dict(row[9])
            ),
        )

    def approve(self, command: ApproveCandidateProposalCommand) -> CandidateProposalApproval:
        return self._approval_repository.approve(command)


def _metadata_payload(
    entity_id: UUID,
    *,
    canonical_name: str,
    entity_kind: str,
    entity_kind_version: int | None,
    tags: tuple[str, ...],
) -> dict[str, object]:
    return {
        "id": str(entity_id),
        "record_type": "entity",
        "entity_kind": entity_kind,
        "entity_kind_version": entity_kind_version,
        "entity_type": entity_kind,
        "canonical_name": canonical_name,
        "tags": list(tags),
    }


def _content_hash(
    item_id: UUID, entity_id: UUID, before: dict[str, object], after: dict[str, object]
) -> str:
    payload = {
        "item_id": str(item_id),
        "sequence": 1,
        "mutation_kind": "update_entity_metadata",
        "target_type": "entity",
        "target_id": str(entity_id),
        "before": before,
        "after": after,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return sha256(encoded).hexdigest()
