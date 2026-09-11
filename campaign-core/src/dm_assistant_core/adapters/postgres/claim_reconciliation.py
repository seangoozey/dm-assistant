# ruff: noqa: E501
"""PostgreSQL audit trail for explicit claim reconciliation decisions."""

import hashlib
import json
import re
from difflib import SequenceMatcher
from typing import Any
from uuid import UUID, uuid4

from psycopg import Connection
from psycopg.types.json import Jsonb

from dm_assistant_core.adapters.postgres.database import PostgresDatabase
from dm_assistant_core.application.claim_reconciliation import (
    ApplyClaimReconciliationCommand,
    ClaimCorrectionReceipt,
    ClaimOverlap,
    ClaimReconciliationError,
    ClaimReconciliationReceipt,
    ClaimReconciliationReview,
    ClaimReplacementReceipt,
    ClaimSnapshot,
    CorrectClaimCommand,
    ReconciliationDecision,
    ReplaceClaimCommand,
)

_CLAIM_SQL = """
SELECT c.id, c.assertion_text, c.state::text, c.authority::text, c.visibility,
       c.recorded_at, cc.trigger_text,
       coalesce(array_agg(DISTINCT sd.original_path) FILTER (WHERE sd.id IS NOT NULL), '{}'),
       coalesce(jsonb_agg(DISTINCT jsonb_build_object(
           'source_span_id', ss.id,
           'source_path', sd.original_path,
           'section_path', ss.section_path,
           'start_offset', ss.start_offset,
           'end_offset', ss.end_offset,
           'evidence_role', ce.evidence_role
       )) FILTER (WHERE ss.id IS NOT NULL), '[]'::jsonb),
       c.effective_from_year, c.effective_from_month, c.effective_from_day,
       c.effective_until_year, c.effective_until_month, c.effective_until_day,
       c.expected_year, c.expected_month, c.expected_day,
       c.observed_year, c.observed_month, c.observed_day,
       NOT EXISTS (SELECT 1 FROM claim_supersessions cs WHERE cs.superseded_claim_id = c.id)
FROM claims c
LEFT JOIN claim_conditions cc ON cc.claim_id = c.id
LEFT JOIN claim_evidence ce ON ce.claim_id = c.id
LEFT JOIN source_spans ss ON ss.id = ce.source_span_id
LEFT JOIN source_revisions sr ON sr.id = ss.source_revision_id
LEFT JOIN source_documents sd ON sd.id = sr.source_document_id
WHERE c.id = %s
GROUP BY c.id, cc.trigger_text
"""


def _snapshot(row: tuple[Any, ...]) -> ClaimSnapshot:
    payload = {
        "claim_id": str(row[0]),
        "assertion_text": str(row[1]),
        "state": str(row[2]),
        "authority": str(row[3]),
        "visibility": str(row[4]),
        "recorded_at": row[5].isoformat(),
        "condition_text": row[6],
        "source_paths": sorted(str(path) for path in row[7]),
        "evidence": sorted(
            row[8],
            key=lambda item: (
                str(item["source_path"]), int(item["start_offset"]), str(item["source_span_id"])
            ),
        ),
        "effective_from": _date_parts(row[9:12]),
        "effective_until": _date_parts(row[12:15]),
        "expected": _date_parts(row[15:18]),
        "observed": _date_parts(row[18:21]),
        "is_current": bool(row[21]),
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return ClaimSnapshot(**payload, snapshot_hash=digest)


def _date_parts(values: tuple[Any, ...]) -> dict[str, int | None] | None:
    if values[0] is None:
        return None
    return {"year": int(values[0]), "month": values[1], "day": values[2]}


def _load(connection: Connection[Any], claim_id: UUID) -> ClaimSnapshot:
    row = connection.execute(_CLAIM_SQL, (claim_id,)).fetchone()
    if row is None:
        raise ClaimReconciliationError(f"claim {claim_id} does not exist")
    return _snapshot(row)


def claim_similarity(left_text: str, right_text: str) -> float:
    """Rank overlap candidates; the reviewer, never this score, decides the outcome."""
    left = re.sub(r"[^a-z0-9]+", " ", left_text.lower()).strip()
    right = re.sub(r"[^a-z0-9]+", " ", right_text.lower()).strip()
    left_words, right_words = set(left.split()), set(right.split())
    union = left_words | right_words
    jaccard = len(left_words & right_words) / len(union) if union else 0.0
    return max(jaccard, SequenceMatcher(None, left, right).ratio())


class PostgresClaimReconciliationRepository:
    def __init__(self, database: PostgresDatabase) -> None:
        self._database = database

    def review(self, superseding: UUID, superseded: UUID) -> ClaimReconciliationReview:
        with self._database.connection() as connection:
            return ClaimReconciliationReview(
                superseding=_load(connection, superseding),
                superseded=_load(connection, superseded),
            )

    def get(self, claim_id: UUID) -> ClaimSnapshot:
        with self._database.connection() as connection:
            return _load(connection, claim_id)

    def discover(self, limit: int) -> tuple[ClaimOverlap, ...]:
        with self._database.connection() as connection:
            rows = connection.execute(
                """
                SELECT DISTINCT newer.id, older.id
                FROM claims newer
                JOIN claims older ON older.subject_entity_id = newer.subject_entity_id
                                  AND older.id <> newer.id
                                  AND (newer.recorded_at, newer.id) > (older.recorded_at, older.id)
                JOIN claim_evidence nce ON nce.claim_id = newer.id
                JOIN source_spans nss ON nss.id = nce.source_span_id
                JOIN source_revisions nsr ON nsr.id = nss.source_revision_id
                JOIN claim_evidence oce ON oce.claim_id = older.id
                JOIN source_spans oss ON oss.id = oce.source_span_id
                JOIN source_revisions osr ON osr.id = oss.source_revision_id
                WHERE nsr.source_document_id = osr.source_document_id
                  AND NOT EXISTS (SELECT 1 FROM claim_supersessions cs WHERE cs.superseded_claim_id = newer.id)
                  AND NOT EXISTS (SELECT 1 FROM claim_supersessions cs WHERE cs.superseded_claim_id = older.id)
                ORDER BY newer.id, older.id
                """
            ).fetchall()
            overlaps: list[ClaimOverlap] = []
            for newer_id, older_id in rows:
                newer, older = _load(connection, newer_id), _load(connection, older_id)
                similarity = claim_similarity(newer.assertion_text, older.assertion_text)
                if similarity >= 0.62:
                    overlaps.append(
                        ClaimOverlap(
                            superseding=newer,
                            superseded=older,
                            similarity=round(similarity, 4),
                        )
                    )
            overlaps.sort(key=lambda item: item.similarity, reverse=True)
            return tuple(overlaps[:limit])

    def apply(self, command: ApplyClaimReconciliationCommand) -> ClaimReconciliationReceipt:
        with self._database.connection() as connection:
            replay = connection.execute(
                "SELECT r.id, cs.id, crd.decision FROM change_sets cs JOIN receipts r ON r.change_set_id=cs.id "
                "JOIN claim_reconciliation_decisions crd ON crd.receipt_id=r.id WHERE cs.idempotency_key=%s",
                (command.idempotency_key,),
            ).fetchone()
            if replay:
                return ClaimReconciliationReceipt(
                    receipt_id=replay[0],
                    change_set_id=replay[1],
                    decision=replay[2],
                    idempotent_replay=True,
                )

            superseding = _load(connection, command.superseding_claim_id)
            superseded = _load(connection, command.superseded_claim_id)
            if (
                superseding.snapshot_hash != command.superseding_snapshot_hash
                or superseded.snapshot_hash != command.superseded_snapshot_hash
            ):
                raise ClaimReconciliationError("claim reconciliation is stale; reload both claims")
            if (
                command.decision is not ReconciliationDecision.RETAIN_BOTH
                and not superseding.is_current
            ):
                raise ClaimReconciliationError("superseding claim is not current")
            if (
                command.decision is not ReconciliationDecision.RETAIN_BOTH
                and not superseded.is_current
            ):
                raise ClaimReconciliationError("superseded claim is already non-current")

            now_row = connection.execute("SELECT clock_timestamp()").fetchone()
            assert now_row is not None
            now = now_row[0]
            workflow_id, proposal_id, version_id, item_id = uuid4(), uuid4(), uuid4(), uuid4()
            approval_id, change_set_id, receipt_id = uuid4(), uuid4(), uuid4()
            payload = command.model_dump(mode="json")
            content_hash = hashlib.sha256(
                json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
            connection.execute(
                "INSERT INTO workflow_sessions(id,kind,started_at,closed_at) VALUES (%s,'lore_entry',%s,%s)",
                (workflow_id, now, now),
            )
            connection.execute(
                "INSERT INTO proposals(id,workflow_session_id,status,created_at,closed_at) VALUES (%s,%s,'applied',%s,%s)",
                (proposal_id, workflow_id, now, now),
            )
            connection.execute(
                "INSERT INTO proposal_versions(id,proposal_id,version_number,content_hash,created_at) VALUES (%s,%s,1,%s,%s)",
                (version_id, proposal_id, content_hash, now),
            )
            connection.execute(
                "INSERT INTO proposal_items(id,proposal_version_id,sequence,mutation_kind,target_type,target_id,before_json,after_json) VALUES (%s,%s,1,'reconcile_claim','claim',%s,%s,%s)",
                (
                    item_id,
                    version_id,
                    command.superseded_claim_id,
                    Jsonb(superseded.model_dump(mode="json")),
                    Jsonb(payload),
                ),
            )
            connection.execute(
                "INSERT INTO approvals(id,proposal_version_id,scope_json,approved_at) VALUES (%s,%s,%s,%s)",
                (approval_id, version_id, Jsonb([str(item_id)]), now),
            )
            connection.execute(
                "INSERT INTO change_sets(id,idempotency_key,workflow_session_id,proposal_version_id,status,requested_at,applied_at,approval_id) VALUES (%s,%s,%s,%s,'applied',%s,%s,%s)",
                (
                    change_set_id,
                    command.idempotency_key,
                    workflow_id,
                    version_id,
                    now,
                    now,
                    approval_id,
                ),
            )
            if command.decision is not ReconciliationDecision.RETAIN_BOTH:
                if command.decision is ReconciliationDecision.DUPLICATE:
                    connection.execute(
                        "INSERT INTO claim_evidence(claim_id,source_span_id,evidence_role) "
                        "SELECT %s,source_span_id,evidence_role FROM claim_evidence "
                        "WHERE claim_id=%s ON CONFLICT DO NOTHING",
                        (
                            command.superseding_claim_id,
                            command.superseded_claim_id,
                        ),
                    )
                connection.execute(
                    "INSERT INTO claim_supersessions(superseding_claim_id,superseded_claim_id,resolution_change_set_id,reason) VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                    (
                        command.superseding_claim_id,
                        command.superseded_claim_id,
                        change_set_id,
                        command.reason,
                    ),
                )
            connection.execute(
                "INSERT INTO change_set_items(id,change_set_id,proposal_item_id,outcome,before_json,after_json) VALUES (%s,%s,%s,'applied',%s,%s)",
                (
                    uuid4(),
                    change_set_id,
                    item_id,
                    Jsonb(superseded.model_dump(mode="json")),
                    Jsonb(payload),
                ),
            )
            connection.execute(
                "INSERT INTO receipts(id,change_set_id,decision_json,conflict_json,outcome,issued_at) VALUES (%s,%s,%s,'{}','applied',%s)",
                (receipt_id, change_set_id, Jsonb(payload), now),
            )
            connection.execute(
                "INSERT INTO claim_reconciliation_decisions(id,superseding_claim_id,superseded_claim_id,decision,superseding_snapshot_hash,superseded_snapshot_hash,reason,receipt_id,created_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    uuid4(),
                    command.superseding_claim_id,
                    command.superseded_claim_id,
                    command.decision.value,
                    command.superseding_snapshot_hash,
                    command.superseded_snapshot_hash,
                    command.reason,
                    receipt_id,
                    now,
                ),
            )
        return ClaimReconciliationReceipt(
            receipt_id=receipt_id,
            change_set_id=change_set_id,
            decision=command.decision,
            idempotent_replay=False,
        )

    def correct(self, command: CorrectClaimCommand) -> ClaimCorrectionReceipt:
        with self._database.connection() as connection:
            original = _load(connection, command.claim_id)
            if original.snapshot_hash != command.snapshot_hash:
                raise ClaimReconciliationError("claim correction is stale; reload the claim")
            if not original.is_current:
                raise ClaimReconciliationError("only a current claim can be corrected")
            if original.assertion_text.strip() == command.assertion_text.strip():
                raise ClaimReconciliationError("claim correction does not change the assertion")
            row = connection.execute(
                "SELECT * FROM correct_canonical_claim(%s,%s,%s,%s)",
                (command.claim_id, command.assertion_text, command.reason, command.idempotency_key),
            ).fetchone()
            assert row is not None
            if not row[4]:
                replacement = _load(connection, row[3])
                connection.execute(
                    "INSERT INTO claim_reconciliation_decisions "
                    "(id,superseding_claim_id,superseded_claim_id,decision," 
                    "superseding_snapshot_hash,superseded_snapshot_hash,reason,receipt_id) "
                    "VALUES (%s,%s,%s,'supersede',%s,%s,%s,%s)",
                    (uuid4(), row[3], row[2], replacement.snapshot_hash,
                     original.snapshot_hash, command.reason, row[0]),
                )
        return ClaimCorrectionReceipt(
            receipt_id=row[0], change_set_id=row[1], original_claim_id=row[2],
            replacement_claim_id=row[3], idempotent_replay=bool(row[4]),
        )

    def replace(self, command: ReplaceClaimCommand) -> ClaimReplacementReceipt:
        with self._database.connection() as connection:
            replay = connection.execute(
                "SELECT r.id,cs.id,r.decision_json FROM change_sets cs "
                "JOIN receipts r ON r.change_set_id=cs.id WHERE cs.idempotency_key=%s",
                (command.idempotency_key,),
            ).fetchone()
            if replay:
                return ClaimReplacementReceipt(
                    receipt_id=replay[0], change_set_id=replay[1],
                    original_claim_id=UUID(replay[2]["original_claim_id"]),
                    replacement_claim_ids=tuple(
                        UUID(value) for value in replay[2]["replacement_claim_ids"]
                    ),
                    idempotent_replay=True,
                )

            original = _load(connection, command.claim_id)
            if original.snapshot_hash != command.snapshot_hash:
                raise ClaimReconciliationError("claim replacement is stale; reload the claim")
            if not original.is_current:
                raise ClaimReconciliationError("only a current claim can be replaced")

            now_row = connection.execute("SELECT clock_timestamp()").fetchone()
            assert now_row is not None
            now = now_row[0]
            workflow_id, proposal_id, version_id = uuid4(), uuid4(), uuid4()
            approval_id, change_set_id, receipt_id = uuid4(), uuid4(), uuid4()
            replacement_ids = tuple(uuid4() for _ in command.replacements)
            payload = command.model_dump(mode="json") | {
                "replacement_claim_ids": [str(value) for value in replacement_ids]
            }
            content_hash = hashlib.sha256(
                json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
            connection.execute(
                "INSERT INTO workflow_sessions(id,kind,started_at,closed_at) "
                "VALUES (%s,'lore_entry',%s,%s)", (workflow_id, now, now),
            )
            connection.execute(
                "INSERT INTO proposals(id,workflow_session_id,status,created_at,closed_at) "
                "VALUES (%s,%s,'applied',%s,%s)", (proposal_id, workflow_id, now, now),
            )
            connection.execute(
                "INSERT INTO proposal_versions(id,proposal_id,version_number,content_hash,created_at) "
                "VALUES (%s,%s,1,%s,%s)", (version_id, proposal_id, content_hash, now),
            )

            item_ids: list[UUID] = []
            for sequence, (replacement_id, draft) in enumerate(
                zip(replacement_ids, command.replacements, strict=True), start=1
            ):
                item_id = uuid4()
                item_ids.append(item_id)
                after = draft.model_dump(mode="json") | {
                    "id": str(replacement_id), "original_claim_id": str(command.claim_id)
                }
                connection.execute(
                    "INSERT INTO proposal_items(id,proposal_version_id,sequence,mutation_kind,"
                    "target_type,target_id,before_json,after_json) "
                    "VALUES (%s,%s,%s,'replace_claim','claim',%s,%s,%s)",
                    (item_id, version_id, sequence, replacement_id,
                     Jsonb(original.model_dump(mode="json")), Jsonb(after)),
                )

            connection.execute(
                "INSERT INTO approvals(id,proposal_version_id,scope_json,approved_at) "
                "VALUES (%s,%s,%s,%s)",
                (approval_id, version_id, Jsonb([str(value) for value in item_ids]), now),
            )
            connection.execute(
                "INSERT INTO change_sets(id,idempotency_key,workflow_session_id,proposal_version_id,"
                "status,requested_at,applied_at,approval_id) "
                "VALUES (%s,%s,%s,%s,'applied',%s,%s,%s)",
                (change_set_id, command.idempotency_key, workflow_id, version_id,
                 now, now, approval_id),
            )

            for item_id, replacement_id, draft in zip(
                item_ids, replacement_ids, command.replacements, strict=True
            ):
                connection.execute(
                    "SELECT create_replacement_claim(%s,%s,%s,%s,%s)",
                    (
                        command.claim_id,
                        replacement_id,
                        Jsonb(draft.model_dump(mode="json")),
                        workflow_id,
                        now,
                    ),
                )
                if draft.condition_text:
                    connection.execute(
                        "INSERT INTO claim_conditions(claim_id,trigger_text) VALUES (%s,%s)",
                        (replacement_id, draft.condition_text.strip()),
                    )
                connection.execute(
                    "INSERT INTO claim_evidence(claim_id,source_span_id,evidence_role) "
                    "SELECT %s,source_span_id,evidence_role FROM claim_evidence WHERE claim_id=%s",
                    (replacement_id, command.claim_id),
                )
                connection.execute(
                    "INSERT INTO claim_supersessions(superseding_claim_id,superseded_claim_id,"
                    "resolution_change_set_id,reason) VALUES (%s,%s,%s,%s)",
                    (replacement_id, command.claim_id, change_set_id, command.reason.strip()),
                )
                after = draft.model_dump(mode="json") | {"id": str(replacement_id)}
                connection.execute(
                    "INSERT INTO change_set_items(id,change_set_id,proposal_item_id,outcome,"
                    "before_json,after_json) VALUES (%s,%s,%s,'applied',%s,%s)",
                    (uuid4(), change_set_id, item_id,
                     Jsonb(original.model_dump(mode="json")), Jsonb(after)),
                )

            decision = {
                "original_claim_id": str(command.claim_id),
                "replacement_claim_ids": [str(value) for value in replacement_ids],
                "reason": command.reason.strip(),
            }
            connection.execute(
                "INSERT INTO receipts(id,change_set_id,decision_json,conflict_json,outcome,issued_at) "
                "VALUES (%s,%s,%s,'{}','applied',%s)",
                (receipt_id, change_set_id, Jsonb(decision), now),
            )
        return ClaimReplacementReceipt(
            receipt_id=receipt_id, change_set_id=change_set_id,
            original_claim_id=command.claim_id, replacement_claim_ids=replacement_ids,
            idempotent_replay=False,
        )
