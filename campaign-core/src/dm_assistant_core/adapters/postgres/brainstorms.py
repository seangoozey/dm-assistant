"""PostgreSQL persistence for Brainstorm workflow sessions."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from psycopg.types.json import Jsonb

from dm_assistant_core.adapters.postgres.database import PostgresDatabase
from dm_assistant_core.application.brainstorms import (
    BrainstormError,
    BrainstormEvidencePin,
    BrainstormPin,
    BrainstormSession,
    BrainstormThought,
    CloseBrainstormCommand,
    StartBrainstormCommand,
)
from dm_assistant_core.application.direct_capture import DirectInputMention
from dm_assistant_core.domain import RetrievalResult, RetrievedEvidence


class PostgresBrainstormRepository:
    def __init__(self, database: PostgresDatabase) -> None:
        self._database = database

    def start(self, command: StartBrainstormCommand) -> BrainstormSession:
        with self._database.connection() as connection:
            replay = connection.execute(
                "SELECT workflow_session_id FROM brainstorm_sessions WHERE idempotency_key = %s",
                (command.idempotency_key,),
            ).fetchone()
            if replay is not None:
                result = self._get(connection, replay[0])
                assert result is not None
                return result
            existing = connection.execute(
                "SELECT bs.workflow_session_id FROM brainstorm_sessions bs "
                "JOIN workflow_sessions ws ON ws.id = bs.workflow_session_id "
                "WHERE ws.closed_at IS NULL ORDER BY ws.started_at DESC LIMIT 1 FOR UPDATE OF ws"
            ).fetchone()
            if existing is not None:
                result = self._get(connection, existing[0])
                assert result is not None
                return result
            session_id = uuid4()
            started_at = datetime.now(UTC)
            connection.execute(
                "INSERT INTO workflow_sessions(id, kind, started_at) VALUES (%s, 'brainstorm', %s)",
                (session_id, started_at),
            )
            connection.execute(
                "INSERT INTO brainstorm_sessions(workflow_session_id, title, idempotency_key) "
                "VALUES (%s, %s, %s)",
                (session_id, command.title.strip(), command.idempotency_key),
            )
            result = self._get(connection, session_id)
            assert result is not None
            return result

    def get(self, session_id: UUID) -> BrainstormSession | None:
        with self._database.connection() as connection:
            return self._get(connection, session_id)

    def list_sessions(self) -> list[tuple[object, ...]]:
        with self._database.connection() as connection:
            return [
                tuple(row)
                for row in connection.execute(
                    "SELECT bs.workflow_session_id, bs.title, ws.closed_at, "
                    "(SELECT count(*) FROM brainstorm_thoughts bt "
                    " WHERE bt.workflow_session_id = bs.workflow_session_id) "
                    "FROM brainstorm_sessions bs "
                    "JOIN workflow_sessions ws ON ws.id = bs.workflow_session_id "
                    "ORDER BY ws.closed_at IS NULL DESC, ws.started_at DESC"
                ).fetchall()
            ]

    def get_open(self) -> BrainstormSession | None:
        with self._database.connection() as connection:
            row = connection.execute(
                "SELECT bs.workflow_session_id FROM brainstorm_sessions bs "
                "JOIN workflow_sessions ws ON ws.id = bs.workflow_session_id "
                "WHERE ws.closed_at IS NULL ORDER BY ws.started_at DESC LIMIT 1"
            ).fetchone()
            return self._get(connection, row[0]) if row is not None else None

    def add_thought(
        self,
        *,
        session_id: UUID,
        thought_id: UUID,
        text: str,
        source_document_id: UUID,
        source_revision_id: UUID,
        candidate_id: UUID,
        evidence: RetrievalResult,
        mentions: tuple[DirectInputMention, ...],
        idempotency_key: str,
        captured_at: datetime,
    ) -> BrainstormSession:
        with self._database.connection() as connection:
            replay = connection.execute(
                "SELECT workflow_session_id FROM brainstorm_thoughts WHERE idempotency_key = %s",
                (idempotency_key,),
            ).fetchone()
            if replay is not None:
                if replay[0] != session_id:
                    raise BrainstormError("thought idempotency key belongs to another brainstorm")
                result = self._get(connection, session_id)
                assert result is not None
                return result
            row = connection.execute(
                "SELECT closed_at FROM workflow_sessions WHERE id = %s AND kind = 'brainstorm' "
                "FOR UPDATE",
                (session_id,),
            ).fetchone()
            if row is None:
                raise BrainstormError("brainstorm session does not exist")
            if row[0] is not None:
                raise BrainstormError("closed brainstorm cannot accept new thoughts")
            for mention in mentions:
                identity = connection.execute(
                    "SELECT canonical_name FROM entities WHERE id = %s", (mention.entity_id,)
                ).fetchone()
                if identity is None:
                    raise BrainstormError("brainstorm mention references an unknown entity")
                if str(identity[0]) != mention.display_name:
                    raise BrainstormError("brainstorm mention must use the canonical entity name")
            sequence_row = connection.execute(
                "SELECT coalesce(max(sequence), 0) + 1 FROM brainstorm_thoughts "
                "WHERE workflow_session_id = %s",
                (session_id,),
            ).fetchone()
            assert sequence_row is not None
            sequence = int(sequence_row[0])
            connection.execute(
                "INSERT INTO brainstorm_thoughts "
                "(id, workflow_session_id, sequence, source_document_id, source_revision_id, "
                "candidate_id, thought_text, evidence_json, mentions_json, "
                "idempotency_key, captured_at) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    thought_id,
                    session_id,
                    sequence,
                    source_document_id,
                    source_revision_id,
                    candidate_id,
                    text,
                    Jsonb(evidence.model_dump(mode="json")),
                    Jsonb([mention.model_dump(mode="json") for mention in mentions]),
                    idempotency_key,
                    captured_at,
                ),
            )
            result = self._get(connection, session_id)
            assert result is not None
            return result

    def pin(self, session_id: UUID, entity_id: UUID) -> BrainstormSession:
        with self._database.connection() as connection:
            self._validate_open(connection, session_id)
            entity = connection.execute(
                "SELECT 1 FROM entities WHERE id = %s", (entity_id,)
            ).fetchone()
            if entity is None:
                raise BrainstormError("cannot pin an unknown entity")
            position_row = connection.execute(
                "SELECT coalesce(max(position), 0) + 1 FROM brainstorm_pins "
                "WHERE workflow_session_id = %s",
                (session_id,),
            ).fetchone()
            assert position_row is not None
            connection.execute(
                "INSERT INTO brainstorm_pins(workflow_session_id, entity_id, position, pinned_at) "
                "VALUES (%s, %s, %s, %s) ON CONFLICT (workflow_session_id, entity_id) DO NOTHING",
                (session_id, entity_id, int(position_row[0]), datetime.now(UTC)),
            )
            result = self._get(connection, session_id)
            assert result is not None
            return result

    def unpin(self, session_id: UUID, entity_id: UUID) -> BrainstormSession:
        with self._database.connection() as connection:
            self._validate_open(connection, session_id)
            connection.execute(
                "DELETE FROM brainstorm_pins WHERE workflow_session_id = %s AND entity_id = %s",
                (session_id, entity_id),
            )
            result = self._get(connection, session_id)
            assert result is not None
            return result

    def pin_evidence(
        self, session_id: UUID, evidence: RetrievedEvidence
    ) -> BrainstormSession:
        with self._database.connection() as connection:
            self._validate_open(connection, session_id)
            position_row = connection.execute(
                "SELECT coalesce(max(position), 0) + 1 FROM brainstorm_evidence_pins "
                "WHERE workflow_session_id = %s",
                (session_id,),
            ).fetchone()
            assert position_row is not None
            connection.execute(
                "INSERT INTO brainstorm_evidence_pins("
                "workflow_session_id, record_id, assertion, citation, entity_id, "
                "position, pinned_at) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s) "
                "ON CONFLICT (workflow_session_id, record_id) DO NOTHING",
                (
                    session_id, evidence.record_id, evidence.assertion, evidence.citation,
                    evidence.entity_id, int(position_row[0]), datetime.now(UTC),
                ),
            )
            result = self._get(connection, session_id)
            assert result is not None
            return result

    def unpin_evidence(self, session_id: UUID, record_id: str) -> BrainstormSession:
        with self._database.connection() as connection:
            self._validate_open(connection, session_id)
            connection.execute(
                "DELETE FROM brainstorm_evidence_pins "
                "WHERE workflow_session_id = %s AND record_id = %s",
                (session_id, record_id),
            )
            result = self._get(connection, session_id)
            assert result is not None
            return result

    @staticmethod
    def _validate_open(connection: Any, session_id: UUID) -> None:
        row = connection.execute(
            "SELECT ws.closed_at FROM workflow_sessions ws JOIN brainstorm_sessions bs "
            "ON bs.workflow_session_id = ws.id WHERE ws.id = %s FOR UPDATE OF ws",
            (session_id,),
        ).fetchone()
        if row is None:
            raise BrainstormError("brainstorm session does not exist")
        if row[0] is not None:
            raise BrainstormError("closed brainstorm context cannot be changed")

    def close(self, session_id: UUID, command: CloseBrainstormCommand) -> BrainstormSession:
        with self._database.connection() as connection:
            row = connection.execute(
                "SELECT ws.closed_at, p.id FROM workflow_sessions ws "
                "JOIN brainstorm_sessions bs ON bs.workflow_session_id = ws.id "
                "LEFT JOIN proposals p ON p.workflow_session_id = ws.id AND p.id = %s "
                "WHERE ws.id = %s FOR UPDATE OF ws",
                (command.proposal_id, session_id),
            ).fetchone()
            if row is None:
                raise BrainstormError("brainstorm session does not exist")
            if row[1] is None:
                raise BrainstormError("closing proposal does not belong to this brainstorm")
            if row[0] is None:
                connection.execute(
                    "UPDATE workflow_sessions SET closed_at = %s WHERE id = %s",
                    (datetime.now(UTC), session_id),
                )
            result = self._get(connection, session_id)
            assert result is not None
            return result

    @staticmethod
    def _get(connection: Any, session_id: UUID) -> BrainstormSession | None:
        session = connection.execute(
            "SELECT ws.id, bs.title, ws.started_at, ws.closed_at, "
            "(SELECT p.id FROM proposals p WHERE p.workflow_session_id = ws.id "
            " ORDER BY p.created_at DESC LIMIT 1) "
            "FROM workflow_sessions ws JOIN brainstorm_sessions bs ON bs.workflow_session_id=ws.id "
            "WHERE ws.id=%s",
            (session_id,),
        ).fetchone()
        if session is None:
            return None
        rows = connection.execute(
            "SELECT id, sequence, thought_text, source_document_id, source_revision_id, "
            "candidate_id, captured_at, evidence_json, mentions_json FROM brainstorm_thoughts "
            "WHERE workflow_session_id=%s ORDER BY sequence",
            (session_id,),
        ).fetchall()
        pin_rows = connection.execute(
            "SELECT bp.entity_id, e.canonical_name, coalesce(kd.canonical_key, e.entity_type), "
            "bp.position, bp.pinned_at FROM brainstorm_pins bp "
            "JOIN entities e ON e.id=bp.entity_id "
            "LEFT JOIN kind_definitions kd ON kd.id=e.entity_kind_id "
            "WHERE bp.workflow_session_id=%s ORDER BY bp.position",
            (session_id,),
        ).fetchall()
        evidence_pin_rows = connection.execute(
            "SELECT record_id, assertion, citation, entity_id, position, pinned_at "
            "FROM brainstorm_evidence_pins WHERE workflow_session_id=%s ORDER BY position",
            (session_id,),
        ).fetchall()
        return BrainstormSession(
            session_id=session[0],
            title=str(session[1]),
            status="closed" if session[3] is not None else "open",
            started_at=session[2],
            closed_at=session[3],
            proposal_id=session[4],
            thoughts=tuple(
                BrainstormThought(
                    thought_id=row[0],
                    sequence=int(row[1]),
                    text=str(row[2]),
                    source_document_id=row[3],
                    source_revision_id=row[4],
                    candidate_id=row[5],
                    captured_at=row[6],
                    evidence=RetrievalResult.model_validate(row[7]),
                    mentions=tuple(DirectInputMention.model_validate(item) for item in row[8]),
                )
                for row in rows
            ),
            pins=tuple(
                BrainstormPin(
                    entity_id=row[0], canonical_name=str(row[1]), entity_kind=str(row[2]),
                    position=int(row[3]), pinned_at=row[4]
                )
                for row in pin_rows
            ),
            evidence_pins=tuple(
                BrainstormEvidencePin(
                    record_id=str(row[0]), assertion=str(row[1]), citation=str(row[2]),
                    entity_id=row[3], position=int(row[4]), pinned_at=row[5]
                )
                for row in evidence_pin_rows
            ),
        )
