"""PostgreSQL proposals and reads for first-class plans."""

# SQL and canonical comparison payloads are kept visibly complete at their call sites.
# ruff: noqa: E501

from __future__ import annotations

import json
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any
from uuid import UUID, uuid4

from psycopg.types.json import Jsonb

from dm_assistant_core.adapters.postgres.candidate_proposals import (
    PostgresCandidateProposalRepository,
)
from dm_assistant_core.adapters.postgres.database import PostgresDatabase
from dm_assistant_core.application.candidate_proposals import (
    ApproveCandidateProposalCommand,
    CandidateProposalApproval,
)
from dm_assistant_core.application.plans import (
    CreatePlanCommand,
    PlanProjectionContext,
    PlanProposalError,
    PlanProposalItem,
    PlanProposalVersion,
    PlanRecord,
    TransitionPlanCommand,
)
from dm_assistant_core.domain import PlanKind, PlanLifecycle, knowledge_boundary_for


class PostgresPlanRepository:
    def __init__(self, database: PostgresDatabase) -> None:
        self._database = database
        self._approval_repository = PostgresCandidateProposalRepository(database)

    def create(self, command: CreatePlanCommand) -> PlanProposalVersion:
        payload: dict[str, Any] = {
            "id": str(command.target_id),
            "record_type": "plan",
            "plan_kind": command.plan_kind.value,
            "plan_kind_version": 1,
            "canonical_name": command.canonical_name,
            "summary": command.summary,
            "objective": command.objective,
            "mechanism": command.mechanism,
            "intended_outcome": command.intended_outcome,
            "lifecycle": PlanLifecycle.ACTIVE.value,
            "knowledge_boundary": knowledge_boundary_for(command.plan_kind).value,
            "visibility": command.visibility.value,
            "owner_record_id": str(command.owner_record_id) if command.owner_record_id else None,
            "player_attribution": command.player_attribution,
            "communicated_at": command.communicated_at.isoformat()
            if command.communicated_at
            else None,
            "evidence_source_span_ids": [str(value) for value in command.evidence_source_span_ids],
            "related_plan_ids": [str(value) for value in command.related_plan_ids],
            "supporting_claim_ids": [],
        }
        with self._database.connection() as connection:
            if connection.execute(
                "SELECT 1 FROM records WHERE id = %s", (command.target_id,)
            ).fetchone():
                raise PlanProposalError("plan target ID already exists")
            self._validate_create_references(connection, command)
            proposal_id = self._insert_proposal(
                connection, "create_plan", command.target_id, None, payload
            )
        return self._required_proposal(proposal_id)

    def transition(self, command: TransitionPlanCommand) -> PlanProposalVersion:
        with self._database.connection() as connection:
            before = self._load_payload(connection, command.plan_id, lock=True)
            if before is None:
                raise PlanProposalError("plan does not exist")
            if before["lifecycle"] == command.lifecycle.value:
                raise PlanProposalError("plan lifecycle is unchanged")
            if command.lifecycle in {PlanLifecycle.COMPLETED, PlanLifecycle.FAILED}:
                count_row = connection.execute(
                    "SELECT count(*) FROM claims WHERE id = ANY(%s) AND state = 'observed'",
                    (list(command.supporting_claim_ids),),
                ).fetchone()
                if count_row is None:
                    raise RuntimeError("observed claim validation returned no result")
                count = int(count_row[0])
                if count != len(command.supporting_claim_ids):
                    raise PlanProposalError(
                        "completion or failure requires separate observed claims"
                    )
            after = dict(before)
            after["lifecycle"] = command.lifecycle.value
            after["supporting_claim_ids"] = [str(value) for value in command.supporting_claim_ids]
            proposal_id = self._insert_proposal(
                connection, "transition_plan", command.plan_id, before, after
            )
        return self._required_proposal(proposal_id)

    def get_proposal(self, proposal_id: UUID) -> PlanProposalVersion | None:
        with self._database.connection() as connection:
            row = connection.execute(
                """
                SELECT p.workflow_session_id, p.status::text, pv.id, pv.version_number,
                       pv.content_hash, pv.created_at, pi.id, pi.mutation_kind,
                       pi.target_id, pi.before_json, pi.after_json
                  FROM proposals p
                  JOIN proposal_versions pv ON pv.proposal_id = p.id
                  JOIN proposal_items pi ON pi.proposal_version_id = pv.id
                 WHERE p.id = %s AND pi.mutation_kind IN ('create_plan', 'transition_plan')
                 ORDER BY pv.version_number DESC LIMIT 1
                """,
                (proposal_id,),
            ).fetchone()
        if row is None:
            return None
        return PlanProposalVersion(
            proposal_id=proposal_id,
            workflow_session_id=row[0],
            status=str(row[1]),
            version_id=row[2],
            version_number=int(row[3]),
            content_hash=str(row[4]),
            created_at=row[5],
            item=PlanProposalItem.model_validate(
                {
                    "item_id": row[6],
                    "mutation_kind": str(row[7]),
                    "target_id": row[8],
                    "before": dict(row[9]) if row[9] is not None else None,
                    "after": dict(row[10]),
                }
            ),
        )

    def approve(self, command: ApproveCandidateProposalCommand) -> CandidateProposalApproval:
        return self._approval_repository.approve(command)

    def get(self, plan_id: UUID) -> PlanRecord | None:
        with self._database.connection() as connection:
            payload = self._load_payload(connection, plan_id)
        return PlanRecord.model_validate(payload) if payload is not None else None

    def list(
        self, plan_kind: PlanKind | None, lifecycle: PlanLifecycle | None
    ) -> tuple[PlanRecord, ...]:
        clauses, params = [], []
        if plan_kind is not None:
            clauses.append("kd.canonical_key = %s")
            params.append(plan_kind.value)
        if lifecycle is not None:
            clauses.append("p.lifecycle = %s")
            params.append(lifecycle.value)
        where = "WHERE " + " AND ".join(clauses) if clauses else ""
        with self._database.connection() as connection:
            ids = connection.execute(
                f"SELECT p.id FROM plans p JOIN kind_definitions kd ON kd.id = p.plan_kind_id {where} ORDER BY lower(p.canonical_name), p.id",
                params,
            ).fetchall()
            payloads = [self._load_payload(connection, row[0]) for row in ids]
        return tuple(PlanRecord.model_validate(value) for value in payloads if value is not None)

    def projection_context(self, plan_id: UUID) -> PlanProjectionContext:
        record = self.get(plan_id)
        if record is None:
            raise PlanProposalError("plan does not exist")
        if (
            record.plan_kind is not PlanKind.IN_WORLD_PLAN
            or record.lifecycle is not PlanLifecycle.ACTIVE
        ):
            raise PlanProposalError("projections require an active in-world NPC or faction plan")
        if not record.evidence_source_span_ids:
            raise PlanProposalError("projection source plan lacks recorded evidence")
        return PlanProjectionContext(
            source_plan_id=record.id,
            source_plan_name=record.canonical_name,
            evidence_source_span_ids=record.evidence_source_span_ids,
        )

    def _required_proposal(self, proposal_id: UUID) -> PlanProposalVersion:
        result = self.get_proposal(proposal_id)
        if result is None:
            raise RuntimeError("plan proposal could not be loaded")
        return result

    @staticmethod
    def _validate_create_references(connection: Any, command: CreatePlanCommand) -> None:
        if command.owner_record_id is not None:
            owner = connection.execute(
                "SELECT e.entity_type FROM entities e WHERE e.id = %s", (command.owner_record_id,)
            ).fetchone()
            allowed = {"npc", "faction"} if command.plan_kind is PlanKind.IN_WORLD_PLAN else {"pc"}
            if owner is None or owner[0] not in allowed:
                raise PlanProposalError(
                    f"{command.plan_kind.value} owner must be one of {sorted(allowed)}"
                )
        if command.evidence_source_span_ids:
            count = connection.execute(
                "SELECT count(*) FROM source_spans WHERE id = ANY(%s)",
                (list(command.evidence_source_span_ids),),
            ).fetchone()[0]
            if count != len(command.evidence_source_span_ids):
                raise PlanProposalError("plan evidence contains an unknown source span")
        if command.related_plan_ids:
            count = connection.execute(
                "SELECT count(*) FROM plans WHERE id = ANY(%s)", (list(command.related_plan_ids),)
            ).fetchone()[0]
            if count != len(command.related_plan_ids):
                raise PlanProposalError("related plan does not exist")

    @staticmethod
    def _insert_proposal(
        connection: Any,
        mutation_kind: str,
        target_id: UUID,
        before: dict[str, Any] | None,
        after: dict[str, Any],
    ) -> UUID:
        proposal_id, workflow_id, version_id, item_id = uuid4(), uuid4(), uuid4(), uuid4()
        created_at = datetime.now(UTC)
        content_hash = _content_hash(item_id, mutation_kind, target_id, before, after)
        connection.execute(
            "INSERT INTO workflow_sessions (id, kind, started_at) VALUES (%s, 'lore_entry', %s)",
            (workflow_id, created_at),
        )
        connection.execute(
            "INSERT INTO proposals (id, workflow_session_id, status, created_at) VALUES (%s, %s, 'pending', %s)",
            (proposal_id, workflow_id, created_at),
        )
        connection.execute(
            "INSERT INTO proposal_versions (id, proposal_id, version_number, content_hash, created_at) VALUES (%s, %s, 1, %s, %s)",
            (version_id, proposal_id, content_hash, created_at),
        )
        connection.execute(
            "INSERT INTO proposal_items (id, proposal_version_id, sequence, mutation_kind, target_type, target_id, before_json, after_json) VALUES (%s, %s, 1, %s, 'plan', %s, %s, %s)",
            (
                item_id,
                version_id,
                mutation_kind,
                target_id,
                Jsonb(before) if before else None,
                Jsonb(after),
            ),
        )
        return proposal_id

    @staticmethod
    def _load_payload(connection: Any, plan_id: UUID, lock: bool = False) -> dict[str, Any] | None:
        suffix = " FOR UPDATE OF p" if lock else ""
        row = connection.execute(
            """
            SELECT p.id, kd.canonical_key, (SELECT max(version) FROM kind_versions WHERE kind_id = kd.id),
                   p.canonical_name, p.summary, p.objective, p.mechanism, p.intended_outcome,
                   p.lifecycle::text, p.knowledge_boundary, p.visibility, p.owner_record_id,
                   owner.entity_type, owner.canonical_name, p.player_attribution, p.communicated_at,
                   ARRAY(SELECT source_span_id FROM plan_evidence pe WHERE pe.plan_id = p.id ORDER BY source_span_id),
                   ARRAY(SELECT related_plan_id FROM plan_relationships pr WHERE pr.plan_id = p.id ORDER BY related_plan_id),
                   ARRAY(
                       SELECT ple.claim_id FROM plan_lifecycle_evidence ple
                       JOIN plan_lifecycle_events latest ON latest.id = ple.lifecycle_event_id
                       WHERE latest.plan_id = p.id AND latest.to_lifecycle = p.lifecycle
                       ORDER BY latest.changed_at DESC, ple.claim_id
                   )
              FROM plans p JOIN kind_definitions kd ON kd.id = p.plan_kind_id
              LEFT JOIN entities owner ON owner.id = p.owner_record_id
             WHERE p.id = %s
            """
            + suffix,
            (plan_id,),
        ).fetchone()
        if row is None:
            return None
        return {
            "id": str(row[0]),
            "record_type": "plan",
            "plan_kind": row[1],
            "plan_kind_version": int(row[2]),
            "canonical_name": row[3],
            "summary": row[4],
            "objective": row[5],
            "mechanism": row[6],
            "intended_outcome": row[7],
            "lifecycle": row[8],
            "knowledge_boundary": row[9],
            "visibility": row[10],
            "owner_record_id": str(row[11]) if row[11] else None,
            "owner_kind": row[12],
            "owner_name": row[13],
            "player_attribution": row[14],
            "communicated_at": row[15].isoformat() if row[15] else None,
            "evidence_source_span_ids": [str(value) for value in row[16]],
            "related_plan_ids": [str(value) for value in row[17]],
            "supporting_claim_ids": [str(value) for value in row[18]],
        }


def _content_hash(
    item_id: UUID,
    mutation_kind: str,
    target_id: UUID,
    before: dict[str, Any] | None,
    after: dict[str, Any],
) -> str:
    payload = {
        "item_id": str(item_id),
        "sequence": 1,
        "mutation_kind": mutation_kind,
        "target_type": "plan",
        "target_id": str(target_id),
        "before": before,
        "after": after,
    }
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
