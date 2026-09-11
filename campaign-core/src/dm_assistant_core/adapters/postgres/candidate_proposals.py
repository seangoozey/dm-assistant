"""PostgreSQL adapter for explicit import-candidate proposal decisions."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any, Literal, cast
from uuid import UUID, uuid4

from psycopg.types.json import Jsonb

from dm_assistant_core.adapters.postgres.database import PostgresDatabase
from dm_assistant_core.application.candidate_proposals import (
    ApproveCandidateProposalCommand,
    CandidateDispositionResult,
    CandidateProposalApproval,
    CandidateProposalError,
    CandidateProposalItem,
    CandidateProposalVersion,
    CreateCandidateProposalCommand,
    CreateClaimDecision,
    CreateEntityDecision,
    DispositionCandidateCommand,
    ProposalCandidateBinding,
    ProposalItemDecision,
    ReviseCandidateProposalCommand,
)
from dm_assistant_core.domain.chronology import compare_same_calendar

_BLOCKED_CLASSIFICATIONS = {"template", "navigation_index", "quarantine"}
_ALLOWED_CLAIM_COORDINATES = {
    ("observed", "real_play"),
    ("established", "explicit_lore"),
    ("intended", "npc_intention"),
    ("prepared", "preparation"),
    ("possible", "brainstorm"),
}
_ALLOWED_AUTHORITY_CORRECTIONS = {
    "real_play": {"real_play"},
    # A human reviewer may recognize durable source wording as an event that
    # occurred during play even when automated import classified it as lore.
    "explicit_lore": {"real_play", "explicit_lore", "preparation", "brainstorm"},
    "npc_intention": {"npc_intention", "brainstorm"},
    "preparation": {"preparation", "brainstorm"},
    "brainstorm": {"brainstorm"},
}


class PostgresCandidateProposalRepository:
    """Persist only exact human decisions and immutable evidence coordinates."""

    def __init__(self, database: PostgresDatabase) -> None:
        self._database = database

    def create(self, command: CreateCandidateProposalCommand) -> CandidateProposalVersion:
        proposal_id = uuid4()
        workflow_id = command.workflow_session_id or uuid4()
        version_id = uuid4()
        now = datetime.now(UTC)
        with self._database.connection() as connection:
            if command.workflow_session_id is not None:
                workflow = connection.execute(
                    "SELECT kind::text, closed_at FROM workflow_sessions WHERE id = %s "
                    "FOR UPDATE",
                    (workflow_id,),
                ).fetchone()
                if workflow is None or str(workflow[0]) != "brainstorm":
                    raise CandidateProposalError("proposal workflow is not a brainstorm session")
                if workflow[1] is not None:
                    raise CandidateProposalError("closed brainstorm cannot create a proposal")
                existing = connection.execute(
                    "SELECT 1 FROM proposals WHERE workflow_session_id = %s "
                    "AND status NOT IN ('rejected', 'superseded') LIMIT 1",
                    (workflow_id,),
                ).fetchone()
                if existing is not None:
                    raise CandidateProposalError("brainstorm already has a promotion proposal")
            prepared = _prepare_items(connection, command.items, workflow_id, None)
            content_hash = _content_hash(prepared)
            if command.workflow_session_id is None:
                connection.execute(
                    "INSERT INTO workflow_sessions (id, kind, started_at) "
                    "VALUES (%s, 'import_review', %s)",
                    (workflow_id, now),
                )
            connection.execute(
                "INSERT INTO proposals (id, workflow_session_id, status, created_at) "
                "VALUES (%s, %s, 'pending', %s)",
                (proposal_id, workflow_id, now),
            )
            _insert_version(
                connection,
                proposal_id=proposal_id,
                version_id=version_id,
                version_number=1,
                content_hash=content_hash,
                supersedes_version_id=None,
                created_at=now,
                prepared=prepared,
            )
            _mark_proposed(connection, prepared, now)
        result = self.get(proposal_id)
        if result is None:
            raise RuntimeError("created proposal could not be loaded")
        return result

    def revise(self, command: ReviseCandidateProposalCommand) -> CandidateProposalVersion:
        version_id = uuid4()
        now = datetime.now(UTC)
        with self._database.connection() as connection:
            proposal = connection.execute(
                "SELECT p.workflow_session_id, p.status, pv.id, pv.version_number "
                "FROM proposals p JOIN proposal_versions pv ON pv.proposal_id = p.id "
                "WHERE p.id = %s ORDER BY pv.version_number DESC LIMIT 1 FOR UPDATE OF p, pv",
                (command.proposal_id,),
            ).fetchone()
            if proposal is None:
                raise CandidateProposalError("proposal does not exist")
            if str(proposal[1]) in {"applied", "rejected", "superseded"}:
                raise CandidateProposalError("closed proposal cannot be revised")
            workflow_id = cast(UUID, proposal[0])
            prior_version_id = cast(UUID, proposal[2])
            version_number = int(proposal[3]) + 1
            prepared = _prepare_items(connection, command.items, workflow_id, command.proposal_id)
            content_hash = _content_hash(prepared)
            _insert_version(
                connection,
                proposal_id=command.proposal_id,
                version_id=version_id,
                version_number=version_number,
                content_hash=content_hash,
                supersedes_version_id=prior_version_id,
                created_at=now,
                prepared=prepared,
            )
            connection.execute(
                "UPDATE approvals SET revoked_at = %s "
                "WHERE proposal_version_id IN "
                "(SELECT id FROM proposal_versions WHERE proposal_id = %s AND id <> %s) "
                "AND revoked_at IS NULL AND NOT EXISTS "
                "(SELECT 1 FROM change_sets cs WHERE cs.approval_id = approvals.id "
                "AND cs.status = 'applied')",
                (now, command.proposal_id, version_id),
            )
            new_candidates = tuple({item.candidate_id for item in prepared})
            connection.execute(
                "UPDATE import_candidates candidate SET review_status = 'pending', updated_at = %s "
                "WHERE candidate.review_status = 'proposed' AND EXISTS "
                "(SELECT 1 FROM proposal_candidate_bindings binding "
                "JOIN proposal_items item ON item.id = binding.proposal_item_id "
                "JOIN proposal_versions version ON version.id = item.proposal_version_id "
                "WHERE binding.candidate_id = candidate.id AND version.proposal_id = %s) "
                "AND NOT (candidate.id = ANY(%s))",
                (now, command.proposal_id, list(new_candidates)),
            )
            _mark_proposed(connection, prepared, now)
        result = self.get(command.proposal_id)
        if result is None:
            raise RuntimeError("revised proposal could not be loaded")
        return result

    def get(self, proposal_id: UUID) -> CandidateProposalVersion | None:
        with self._database.connection() as connection:
            version = connection.execute(
                "SELECT p.workflow_session_id, p.status::text, pv.id, pv.version_number, "
                "pv.content_hash, pv.supersedes_version_id, pv.created_at "
                "FROM proposals p JOIN proposal_versions pv ON pv.proposal_id = p.id "
                "WHERE p.id = %s ORDER BY pv.version_number DESC LIMIT 1",
                (proposal_id,),
            ).fetchone()
            if version is None:
                return None
            rows = connection.execute(
                "SELECT pi.id, pi.sequence, pi.mutation_kind, pi.target_type, pi.target_id, "
                "pi.after_json, pcb.candidate_id, pcb.source_revision_id, pcb.source_span_id, "
                "pcb.candidate_fingerprint FROM proposal_items pi "
                "JOIN proposal_candidate_bindings pcb ON pcb.proposal_item_id = pi.id "
                "WHERE pi.proposal_version_id = %s ORDER BY pi.sequence",
                (version[2],),
            ).fetchall()
        return CandidateProposalVersion(
            proposal_id=proposal_id,
            workflow_session_id=version[0],
            status=str(version[1]),
            version_id=version[2],
            version_number=int(version[3]),
            content_hash=str(version[4]),
            supersedes_version_id=version[5],
            created_at=version[6],
            items=tuple(_proposal_item(row) for row in rows),
        )

    def get_for_candidate(self, candidate_id: UUID) -> CandidateProposalVersion | None:
        with self._database.connection() as connection:
            row = connection.execute(
                "SELECT pv.proposal_id FROM proposal_candidate_bindings pcb "
                "JOIN proposal_items pi ON pi.id = pcb.proposal_item_id "
                "JOIN proposal_versions pv ON pv.id = pi.proposal_version_id "
                "JOIN proposals p ON p.id = pv.proposal_id "
                "WHERE pcb.candidate_id = %s AND p.status = 'pending' "
                "ORDER BY pv.version_number DESC LIMIT 1",
                (candidate_id,),
            ).fetchone()
        return self.get(row[0]) if row else None

    def approve(self, command: ApproveCandidateProposalCommand) -> CandidateProposalApproval:
        if len(set(command.item_ids)) != len(command.item_ids):
            raise CandidateProposalError("approval scope contains duplicate proposal items")
        with self._database.connection() as connection:
            replay = connection.execute(
                "SELECT cs.id, cs.proposal_version_id, cs.approval_id, cs.requested_at, "
                "pv.proposal_id, pv.version_number, pv.content_hash, a.scope_json "
                "FROM change_sets cs JOIN proposal_versions pv ON pv.id = cs.proposal_version_id "
                "JOIN approvals a ON a.id = cs.approval_id WHERE cs.idempotency_key = %s",
                (command.idempotency_key,),
            ).fetchone()
            if replay is not None:
                replay_items = tuple(UUID(value) for value in replay[7])
                if (
                    replay[4] != command.proposal_id
                    or int(replay[5]) != command.reviewed_version
                    or str(replay[6]) != command.content_hash
                    or replay_items != command.item_ids
                ):
                    raise CandidateProposalError(
                        "idempotency key is already bound to another approval"
                    )
                return CandidateProposalApproval(
                    proposal_id=replay[4],
                    proposal_version_id=replay[1],
                    reviewed_version=int(replay[5]),
                    content_hash=str(replay[6]),
                    approval_id=replay[2],
                    change_set_id=replay[0],
                    item_ids=replay_items,
                    idempotency_key=command.idempotency_key,
                    approved_at=replay[3],
                    idempotent_replay=True,
                )
            version = connection.execute(
                "SELECT p.workflow_session_id, p.status::text, pv.id, pv.version_number, "
                "pv.content_hash FROM proposals p JOIN proposal_versions pv ON pv.proposal_id=p.id "
                "WHERE p.id=%s ORDER BY pv.version_number DESC LIMIT 1 FOR UPDATE OF p, pv",
                (command.proposal_id,),
            ).fetchone()
            if version is None:
                raise CandidateProposalError("proposal does not exist")
            if (
                int(version[3]) != command.reviewed_version
                or str(version[4]) != command.content_hash
            ):
                raise CandidateProposalError("reviewed proposal version or content hash is stale")
            if str(version[1]) in {"applied", "rejected", "superseded"}:
                raise CandidateProposalError("closed proposal cannot be approved")
            rows = connection.execute(
                "SELECT id FROM proposal_items WHERE proposal_version_id = %s AND id = ANY(%s)",
                (version[2], list(command.item_ids)),
            ).fetchall()
            if {row[0] for row in rows} != set(command.item_ids):
                raise CandidateProposalError(
                    "approval scope contains an item from another proposal version"
                )
            approval_id = uuid4()
            change_set_id = uuid4()
            approved_at = datetime.now(UTC)
            connection.execute(
                "INSERT INTO approvals (id, proposal_version_id, scope_json, approved_at) "
                "VALUES (%s, %s, %s, %s)",
                (
                    approval_id,
                    version[2],
                    Jsonb([str(item) for item in command.item_ids]),
                    approved_at,
                ),
            )
            connection.execute(
                "INSERT INTO change_sets (id, idempotency_key, workflow_session_id, "
                "proposal_version_id, approval_id, status, requested_at) "
                "VALUES (%s, %s, %s, %s, %s, 'pending', %s)",
                (
                    change_set_id,
                    command.idempotency_key,
                    version[0],
                    version[2],
                    approval_id,
                    approved_at,
                ),
            )
        return CandidateProposalApproval(
            proposal_id=command.proposal_id,
            proposal_version_id=version[2],
            reviewed_version=command.reviewed_version,
            content_hash=command.content_hash,
            approval_id=approval_id,
            change_set_id=change_set_id,
            item_ids=command.item_ids,
            idempotency_key=command.idempotency_key,
            approved_at=approved_at,
            idempotent_replay=False,
        )

    def disposition(self, command: DispositionCandidateCommand) -> CandidateDispositionResult:
        disposition_id = uuid4()
        now = datetime.now(UTC)
        with self._database.connection() as connection:
            row = connection.execute(
                "SELECT status, review_status FROM import_candidates WHERE id = %s FOR UPDATE",
                (command.candidate_id,),
            ).fetchone()
            if row is None:
                raise CandidateProposalError("candidate does not exist")
            if str(row[1]) in {"proposed", "applied"}:
                raise CandidateProposalError(
                    "proposed or applied candidate cannot be dispositioned"
                )
            if str(row[0]) == "source_removed":
                bound = connection.execute(
                    "SELECT 1 FROM proposal_candidate_bindings "
                    "WHERE candidate_id = %s LIMIT 1",
                    (command.candidate_id,),
                ).fetchone()
                if bound is not None:
                    raise CandidateProposalError(
                        "proposal-bound source-removed candidate cannot be dispositioned"
                    )
            if str(row[1]) == command.disposition.value:
                existing = connection.execute(
                    "SELECT id, created_at FROM candidate_dispositions "
                    "WHERE candidate_id = %s AND disposition = %s AND reason = %s "
                    "ORDER BY created_at DESC, id DESC LIMIT 1",
                    (
                        command.candidate_id,
                        command.disposition.value,
                        command.reason,
                    ),
                ).fetchone()
                if existing is not None:
                    return CandidateDispositionResult(
                        disposition_id=existing[0],
                        candidate_id=command.candidate_id,
                        review_status=command.disposition,
                        reason=command.reason,
                        created_at=existing[1],
                    )
            connection.execute(
                "INSERT INTO candidate_dispositions (id, candidate_id, disposition, reason, "
                "created_at) VALUES (%s, %s, %s, %s, %s)",
                (
                    disposition_id,
                    command.candidate_id,
                    command.disposition.value,
                    command.reason,
                    now,
                ),
            )
            connection.execute(
                "UPDATE import_candidates SET review_status = %s, updated_at = %s WHERE id = %s",
                (command.disposition.value, now, command.candidate_id),
            )
        return CandidateDispositionResult(
            disposition_id=disposition_id,
            candidate_id=command.candidate_id,
            review_status=command.disposition,
            reason=command.reason,
            created_at=now,
        )


class _PreparedItem:
    def __init__(
        self,
        *,
        item_id: UUID,
        sequence: int,
        mutation_kind: str,
        target_type: str,
        target_id: UUID,
        after: dict[str, Any],
        candidate_id: UUID,
        source_revision_id: UUID,
        source_span_id: UUID,
        candidate_fingerprint: str,
    ) -> None:
        self.item_id = item_id
        self.sequence = sequence
        self.mutation_kind = mutation_kind
        self.target_type = target_type
        self.target_id = target_id
        self.after = after
        self.candidate_id = candidate_id
        self.source_revision_id = source_revision_id
        self.source_span_id = source_span_id
        self.candidate_fingerprint = candidate_fingerprint


def _prepare_items(
    connection: Any,
    decisions: tuple[ProposalItemDecision, ...],
    workflow_id: UUID,
    revising_proposal_id: UUID | None,
) -> tuple[_PreparedItem, ...]:
    if len({decision.target_id for decision in decisions}) != len(decisions):
        raise CandidateProposalError("proposal contains duplicate immutable target IDs")
    new_entities = {
        decision.target_id: decision.entity_kind.value
        for decision in decisions
        if isinstance(decision, CreateEntityDecision)
    }
    prepared: list[_PreparedItem] = []
    for sequence, decision in enumerate(decisions, start=1):
        candidate = connection.execute(
            "SELECT ic.fingerprint, ic.assertion_text, ic.state::text, ic.authority::text, "
            "ic.visibility, ic.is_conditional, ic.predicts_subject_action, ic.evidence_only, "
            "ic.status, ic.review_status, ice.section_path, ice.start_offset, ice.end_offset, "
            "sr.raw_content, sr.classification FROM import_candidates ic "
            "JOIN import_candidate_evidence ice ON ice.candidate_id = ic.id "
            "JOIN source_revisions sr ON sr.id = ice.source_revision_id "
            "WHERE ic.id = %s AND sr.id = %s FOR UPDATE OF ic",
            (decision.candidate_id, decision.evidence_revision_id),
        ).fetchone()
        if candidate is None:
            raise CandidateProposalError("candidate evidence revision does not exist")
        _validate_candidate_state(
            connection, decision.candidate_id, candidate, revising_proposal_id
        )
        text = bytes(candidate[13]).decode("utf-8")
        start, end = int(candidate[11]), int(candidate[12])
        if end > len(text):
            raise CandidateProposalError("candidate evidence span exceeds its source revision")
        excerpt_hash = sha256(text[start:end].encode("utf-8")).hexdigest()
        span_id = uuid4()
        connection.execute(
            "INSERT INTO source_spans (id, source_revision_id, section_path, start_offset, "
            "end_offset, excerpt_hash) VALUES (%s, %s, %s, %s, %s, %s)",
            (span_id, decision.evidence_revision_id, candidate[10], start, end, excerpt_hash),
        )
        if isinstance(decision, CreateEntityDecision):
            _validate_new_entity(connection, decision)
            target_type = "entity"
            after: dict[str, Any] = {
                "id": str(decision.target_id),
                "record_type": "entity",
                "entity_kind": decision.entity_kind.value,
                "entity_kind_version": 1,
                "entity_type": decision.entity_kind.value,
                "canonical_name": decision.canonical_name,
                "tags": list(decision.tags),
            }
            if decision.rules_element_mechanics is not None:
                after["rules_element_mechanics"] = {
                    "rules_kind": decision.rules_element_mechanics.rules_kind.value,
                    "summary": decision.rules_element_mechanics.summary,
                    "mechanics": decision.rules_element_mechanics.mechanics,
                }
        else:
            _validate_claim(connection, decision, candidate, new_entities, workflow_id)
            target_type = "claim"
            assertion_text = str(candidate[1])
            if decision.candidate_extraction_id is not None:
                extraction = connection.execute(
                    "SELECT assertion_text FROM candidate_extractions "
                    "WHERE id = %s AND candidate_id = %s",
                    (decision.candidate_extraction_id, decision.candidate_id),
                ).fetchone()
                if extraction is None:
                    raise CandidateProposalError(
                        "candidate extraction does not belong to the proposed candidate"
                    )
                assertion_text = str(extraction[0])
            if decision.assertion_text is not None:
                assertion_text = decision.assertion_text
            after = _claim_payload(decision, assertion_text, span_id, workflow_id)
        prepared.append(
            _PreparedItem(
                item_id=uuid4(),
                sequence=sequence,
                mutation_kind=decision.mutation_kind,
                target_type=target_type,
                target_id=decision.target_id,
                after=after,
                candidate_id=decision.candidate_id,
                source_revision_id=decision.evidence_revision_id,
                source_span_id=span_id,
                candidate_fingerprint=str(candidate[0]),
            )
        )
    return tuple(prepared)


def _validate_candidate_state(
    connection: Any,
    candidate_id: UUID,
    candidate: tuple[Any, ...],
    revising_proposal_id: UUID | None,
) -> None:
    if bool(candidate[7]):
        raise CandidateProposalError("evidence-only candidate cannot create a proposal")
    if str(candidate[8]) != "active":
        raise CandidateProposalError("source-removed candidate cannot create a proposal")
    if str(candidate[14]) in _BLOCKED_CLASSIFICATIONS:
        raise CandidateProposalError("quarantine, template, or navigation evidence cannot promote")
    review_status = str(candidate[9])
    if review_status == "pending":
        return
    if review_status == "proposed" and revising_proposal_id is not None:
        bound = connection.execute(
            "SELECT 1 FROM proposal_candidate_bindings binding "
            "JOIN proposal_items item ON item.id = binding.proposal_item_id "
            "JOIN proposal_versions version ON version.id = item.proposal_version_id "
            "WHERE binding.candidate_id = %s AND version.proposal_id = %s LIMIT 1",
            (candidate_id, revising_proposal_id),
        ).fetchone()
        if bound is not None:
            return
    raise CandidateProposalError(f"candidate review status {review_status} cannot be proposed")


def _validate_new_entity(connection: Any, decision: CreateEntityDecision) -> None:
    collision = connection.execute(
        "SELECT 1 FROM entities WHERE id = %s OR "
        "(lower(canonical_name) = lower(%s) AND entity_type = %s) LIMIT 1",
        (decision.target_id, decision.canonical_name, decision.entity_kind.value),
    ).fetchone()
    if collision is not None:
        raise CandidateProposalError("entity target or exact canonical identity already exists")


def _validate_claim(
    connection: Any,
    decision: CreateClaimDecision,
    candidate: tuple[Any, ...],
    new_entities: dict[UUID, str],
    workflow_id: UUID,
) -> None:
    coordinates = (decision.state.value, decision.authority.value)
    if coordinates not in _ALLOWED_CLAIM_COORDINATES:
        raise CandidateProposalError("claim state and authority are not a valid pair")
    authority_allowed = (
        decision.authority.value in _ALLOWED_AUTHORITY_CORRECTIONS[str(candidate[3])]
    )
    if not authority_allowed and str(candidate[3]) == "brainstorm":
        authority_allowed = connection.execute(
            "SELECT 1 FROM brainstorm_thoughts WHERE workflow_session_id = %s "
            "AND candidate_id = %s LIMIT 1",
            (workflow_id, decision.candidate_id),
        ).fetchone() is not None
    if not authority_allowed:
        raise CandidateProposalError("claim authority cannot be strengthened beyond its evidence")
    if decision.state.value == "observed" and decision.observed_at is None:
        raise CandidateProposalError("observed claim requires an observed campaign year")
    planning_states = {"intended", "prepared"}
    if decision.expected_at is not None and decision.state.value not in planning_states:
        raise CandidateProposalError("expected_at is valid only for intended or prepared claims")
    if (
        decision.effective_from is not None
        and decision.effective_until is not None
        and compare_same_calendar(decision.effective_until, decision.effective_from) < 0
    ):
        raise CandidateProposalError("effective_until cannot precede effective_from")
    if (
        decision.effective_from is not None
        and decision.effective_from.year is not None
        and decision.effective_from.year > decision.recorded_at.year
    ):
        if decision.state.value not in planning_states:
            raise CandidateProposalError("future facts must remain intended or prepared")
        if decision.expected_at is None:
            raise CandidateProposalError("future intended or prepared claim requires expected_at")
    subject_type = (
        _entity_type(connection, decision.subject_entity_id, new_entities)
        if decision.subject_entity_id is not None
        else None
    )
    if decision.object_entity_id is not None:
        _entity_type(connection, decision.object_entity_id, new_entities)
        if (
            decision.subject_entity_id is not None
            and decision.object_entity_id == decision.subject_entity_id
        ):
            raise CandidateProposalError("claim subject and object cannot be the same entity")
    for related_entity_id in decision.related_entity_ids:
        _entity_type(connection, related_entity_id, new_entities)
    if subject_type == "pc":
        if decision.predicts_subject_action:
            raise CandidateProposalError("future PC actions cannot be predicted or prescribed")
        if decision.authority.value in {"preparation", "brainstorm"} and (
            decision.state.value not in {"prepared", "possible"}
            or decision.visibility.value != "dm_only"
        ):
            raise CandidateProposalError(
                "PC campaign direction must remain prepared or possible and DM-only"
            )
    if connection.execute("SELECT 1 FROM claims WHERE id = %s", (decision.target_id,)).fetchone():
        raise CandidateProposalError("claim target already exists")
    proposed_assertion = decision.assertion_text or str(candidate[1])
    if decision.subject_entity_id is None:
        existing_claims = connection.execute(
            "SELECT assertion_text, predicate FROM claims "
            "WHERE subject_entity_id IS NULL AND lower(assertion_text) = lower(%s)",
            (proposed_assertion,),
        ).fetchall()
    else:
        existing_claims = connection.execute(
            "SELECT assertion_text, predicate FROM claims WHERE subject_entity_id = %s",
            (decision.subject_entity_id,),
        ).fetchall()
    if any(
        _assertions_require_conflict_review(
            proposed_assertion,
            decision.predicate,
            str(existing[0]),
            str(existing[1]) if existing[1] is not None else None,
        )
        for existing in existing_claims
    ):
        raise CandidateProposalError(
            "existing claim with this subject and overlapping assertion requires conflict review"
        )


def _assertions_require_conflict_review(
    proposed: str,
    proposed_predicate: str | None,
    existing: str,
    existing_predicate: str | None,
) -> bool:
    import re

    def terms(value: str) -> set[str]:
        return {word for word in re.findall(r"[a-z0-9]+", value.casefold()) if len(word) > 2}

    proposed_terms = terms(proposed)
    existing_terms = terms(existing)
    if proposed_terms == existing_terms:
        return True
    if proposed_predicate is None or existing_predicate is None:
        return False
    if proposed_predicate.casefold().strip() != existing_predicate.casefold().strip():
        return False
    union = proposed_terms | existing_terms
    return bool(union) and len(proposed_terms & existing_terms) / len(union) >= 0.35


def _entity_type(connection: Any, entity_id: UUID, new_entities: dict[UUID, str]) -> str:
    if entity_id in new_entities:
        return new_entities[entity_id]
    row = connection.execute(
        "SELECT entity_type FROM entities WHERE id = %s", (entity_id,)
    ).fetchone()
    if row is None:
        raise CandidateProposalError("explicit claim entity target does not exist")
    return str(row[0])


def _claim_payload(
    decision: CreateClaimDecision, assertion_text: str, span_id: UUID, workflow_id: UUID
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": str(decision.target_id),
        "subject_entity_id": (
            str(decision.subject_entity_id) if decision.subject_entity_id else None
        ),
        "predicate": decision.predicate,
        "object_entity_id": str(decision.object_entity_id) if decision.object_entity_id else None,
        "related_entity_ids": [str(entity_id) for entity_id in decision.related_entity_ids],
        "assertion_text": assertion_text,
        "state": decision.state.value,
        "authority": decision.authority.value,
        "confidence": str(decision.confidence),
        "visibility": decision.visibility.value,
        "is_conditional": decision.is_conditional,
        "predicts_subject_action": decision.predicts_subject_action,
        "condition_text": decision.condition_text,
        "condition_reference_type": decision.condition_reference_type,
        "condition_reference_id": (
            str(decision.condition_reference_id) if decision.condition_reference_id else None
        ),
        "recorded_at": decision.recorded_at.isoformat(),
        "session_id": str(workflow_id),
        "source_span_id": str(span_id),
        "evidence_role": "support",
    }
    payload.update(_date_fields("effective_from", decision.effective_from))
    payload.update(_date_fields("effective_until", decision.effective_until))
    payload.update(_date_fields("expected", decision.expected_at))
    payload.update(_date_fields("observed", decision.observed_at))
    return payload


def _date_fields(prefix: str, date: Any) -> dict[str, Any]:
    """Flatten a CampaignDate into the year/month/day/calendar columns the SQL expects."""
    if date is None:
        return {
            f"{prefix}_year": None,
            f"{prefix}_month": None,
            f"{prefix}_day": None,
        }
    calendar_id = getattr(date, "calendar_id", None)
    fields: dict[str, Any] = {
        f"{prefix}_year": getattr(date, "year", None),
        f"{prefix}_month": getattr(date, "month", None),
        f"{prefix}_day": getattr(date, "day", None),
    }
    if prefix == "effective_from":
        fields["campaign_calendar_id"] = calendar_id
    return fields


def _content_hash(prepared: tuple[_PreparedItem, ...]) -> str:
    payload = [
        {
            "item_id": str(item.item_id),
            "sequence": item.sequence,
            "mutation_kind": item.mutation_kind,
            "target_type": item.target_type,
            "target_id": str(item.target_id),
            "after": item.after,
            "candidate_id": str(item.candidate_id),
            "source_revision_id": str(item.source_revision_id),
            "source_span_id": str(item.source_span_id),
            "candidate_fingerprint": item.candidate_fingerprint,
        }
        for item in prepared
    ]
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(encoded).hexdigest()


def _insert_version(
    connection: Any,
    *,
    proposal_id: UUID,
    version_id: UUID,
    version_number: int,
    content_hash: str,
    supersedes_version_id: UUID | None,
    created_at: datetime,
    prepared: tuple[_PreparedItem, ...],
) -> None:
    connection.execute(
        "INSERT INTO proposal_versions (id, proposal_id, version_number, content_hash, "
        "created_at, supersedes_version_id) VALUES (%s, %s, %s, %s, %s, %s)",
        (
            version_id,
            proposal_id,
            version_number,
            content_hash,
            created_at,
            supersedes_version_id,
        ),
    )
    for item in prepared:
        connection.execute(
            "INSERT INTO proposal_items (id, proposal_version_id, sequence, mutation_kind, "
            "target_type, target_id, after_json) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (
                item.item_id,
                version_id,
                item.sequence,
                item.mutation_kind,
                item.target_type,
                item.target_id,
                Jsonb(item.after),
            ),
        )
        connection.execute(
            "INSERT INTO proposal_candidate_bindings (proposal_item_id, candidate_id, "
            "source_revision_id, source_span_id, candidate_fingerprint, created_at) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (
                item.item_id,
                item.candidate_id,
                item.source_revision_id,
                item.source_span_id,
                item.candidate_fingerprint,
                created_at,
            ),
        )


def _mark_proposed(connection: Any, prepared: tuple[_PreparedItem, ...], now: datetime) -> None:
    candidate_ids = list({item.candidate_id for item in prepared})
    connection.execute(
        "UPDATE import_candidates SET review_status = 'proposed', updated_at = %s "
        "WHERE id = ANY(%s)",
        (now, candidate_ids),
    )


def _proposal_item(row: tuple[Any, ...]) -> CandidateProposalItem:
    return CandidateProposalItem(
        item_id=row[0],
        sequence=int(row[1]),
        mutation_kind=cast(Literal["create_entity", "create_claim"], str(row[2])),
        target_type=cast(Literal["entity", "claim"], str(row[3])),
        target_id=row[4],
        after=dict(row[5]),
        evidence=ProposalCandidateBinding(
            candidate_id=row[6],
            source_revision_id=row[7],
            source_span_id=row[8],
            candidate_fingerprint=str(row[9]),
        ),
    )
