"""Transactional PC profile overlays that never rewrite imported source."""

from uuid import UUID, uuid4

from psycopg.types.json import Jsonb

from dm_assistant_core.adapters.postgres.database import PostgresDatabase
from dm_assistant_core.application.pc_profiles import (
    PCProfile,
    PCProfileError,
    PCProfileReceipt,
    UpdatePCProfileCommand,
)


class PostgresPCProfileRepository:
    def __init__(self, database: PostgresDatabase) -> None:
        self._database = database

    def get(self, document_id: UUID) -> PCProfile | None:
        with self._database.connection() as connection:
            row = connection.execute(
                "SELECT source_revision_id, version, profile_json FROM pc_document_profiles "
                "WHERE source_document_id = %s",
                (document_id,),
            ).fetchone()
        if row is None:
            return None
        return PCProfile(
            document_id=document_id, source_revision_id=row[0], version=row[1], **row[2]
        )

    def update(self, command: UpdatePCProfileCommand) -> PCProfileReceipt:
        payload = command.model_dump(
            mode="json", exclude={"document_id", "source_revision_id", "version", "idempotency_key"}
        )
        with self._database.connection() as connection:
            replay = connection.execute(
                "SELECT id, source_document_id, version FROM pc_profile_receipts "
                "WHERE idempotency_key = %s",
                (command.idempotency_key,),
            ).fetchone()
            if replay:
                return PCProfileReceipt(
                    receipt_id=replay[0],
                    document_id=replay[1],
                    version=replay[2],
                    idempotent_replay=True,
                )
            source = connection.execute(
                """
                SELECT sr.id, sr.frontmatter_json->>'type'
                FROM source_documents sd
                JOIN LATERAL (
                    SELECT id, frontmatter_json FROM source_revisions
                    WHERE source_document_id = sd.id
                    ORDER BY captured_at DESC, id DESC LIMIT 1
                ) sr ON true
                WHERE sd.id = %s FOR UPDATE OF sd
                """,
                (command.document_id,),
            ).fetchone()
            if source is None or source[1] not in {"pc", "npc"}:
                raise PCProfileError("editable profile requires a PC or NPC source document")
            if source[1] == "pc" and not command.player:
                raise PCProfileError("a PC profile requires its player")
            if source[0] != command.source_revision_id:
                raise PCProfileError("source revision changed; reload before saving")
            current = connection.execute(
                "SELECT version FROM pc_document_profiles WHERE source_document_id=%s FOR UPDATE",
                (command.document_id,),
            ).fetchone()
            current_version = int(current[0]) if current else 0
            if current_version != command.version:
                raise PCProfileError("profile version changed; reload before saving")
            next_version = current_version + 1
            connection.execute(
                """
                INSERT INTO pc_document_profiles
                    (source_document_id, source_revision_id, version, profile_json)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (source_document_id) DO UPDATE SET
                    source_revision_id = excluded.source_revision_id,
                    version = excluded.version,
                    profile_json = excluded.profile_json,
                    updated_at = now()
                """,
                (command.document_id, command.source_revision_id, next_version, Jsonb(payload)),
            )
            connection.execute(
                """INSERT INTO pc_profile_revisions
                (source_document_id, source_revision_id, version, profile_json)
                VALUES (%s, %s, %s, %s)""",
                (command.document_id, command.source_revision_id, next_version, Jsonb(payload)),
            )
            receipt_id = uuid4()
            connection.execute(
                """INSERT INTO pc_profile_receipts
                (id, source_document_id, version, idempotency_key)
                VALUES (%s, %s, %s, %s)""",
                (receipt_id, command.document_id, next_version, command.idempotency_key),
            )
        return PCProfileReceipt(
            receipt_id=receipt_id,
            document_id=command.document_id,
            version=next_version,
            idempotent_replay=False,
        )
