"""Transactional PC profile overlays that never rewrite imported source."""

from uuid import UUID, uuid4

from psycopg.types.json import Jsonb

from dm_assistant_core.adapters.postgres.database import PostgresDatabase
from dm_assistant_core.application.pc_profiles import (
    PCProfile,
    PCProfileError,
    PCProfileReceipt,
    ProfileAliasSync,
    UpdatePCProfileCommand,
)

PROFILE_ALIAS_NAMESPACE = "profile"


def _normalize_alias(value: str) -> str:
    return " ".join(value.casefold().split())


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

    def _focal_entity(self, connection, document_id: UUID, canonical_name: str):
        """The one entity whose claims are evidenced by this document.

        Multiple candidates are narrowed by an exact (case-insensitive) name
        match against the profile; persistent ambiguity skips the sync — the
        identity review queue, not a profile save, resolves contested identity.
        """
        rows = connection.execute(
            """
            SELECT DISTINCT e.id, e.canonical_name FROM entities e
            JOIN claims c ON c.subject_entity_id = e.id OR EXISTS (
                SELECT 1 FROM claim_related_entities cre
                WHERE cre.claim_id = c.id AND cre.entity_id = e.id)
            JOIN claim_evidence ce ON ce.claim_id = c.id
            JOIN source_spans ss ON ss.id = ce.source_span_id
            JOIN source_revisions sr ON sr.id = ss.source_revision_id
            WHERE sr.source_document_id = %s
            """,
            (document_id,),
        ).fetchall()
        if not rows:
            return None
        if len(rows) > 1:
            rows = [row for row in rows
                    if _normalize_alias(row[1]) == _normalize_alias(canonical_name)]
        return (rows[0][0], rows[0][1]) if len(rows) == 1 else None

    def _sync_aliases(self, connection, command: UpdatePCProfileCommand,
                      source_revision_id: UUID) -> ProfileAliasSync | None:
        focal = self._focal_entity(connection, command.document_id, command.canonical_name)
        if focal is None:
            return None
        entity_id, entity_name = focal
        desired, seen = [], set()
        for alias in command.aliases:
            trimmed = alias.strip()
            normalized = _normalize_alias(trimmed)
            if trimmed and normalized not in seen:
                seen.add(normalized)
                desired.append((trimmed, normalized))
        desired_norms = {normalized for _, normalized in desired}
        current = connection.execute(
            "SELECT alias, normalized_alias FROM entity_aliases "
            "WHERE entity_id = %s AND namespace = %s",
            (entity_id, PROFILE_ALIAS_NAMESPACE),
        ).fetchall()
        current_norms = {row[1] for row in current}

        applied, removed, skipped = [], [], []
        for alias, normalized in desired:
            if normalized in current_norms:
                continue
            if normalized == _normalize_alias(entity_name):
                continue  # redundant: the canonical name already resolves
            conflict = connection.execute(
                """
                SELECT 1 WHERE EXISTS (
                    SELECT 1 FROM entity_aliases a
                    WHERE a.normalized_alias = %s AND a.entity_id <> %s)
                OR EXISTS (
                    SELECT 1 FROM entities e
                    WHERE lower(e.canonical_name) = lower(%s) AND e.id <> %s)
                """,
                (normalized, entity_id, normalized, entity_id),
            ).fetchone()
            if conflict:
                skipped.append(alias)
                continue
            connection.execute(
                "INSERT INTO entity_aliases (id, entity_id, namespace, alias, "
                "normalized_alias, alias_kind, source_revision_id) "
                "VALUES (%s, %s, %s, %s, %s, 'profile_edit', %s)",
                (uuid4(), entity_id, PROFILE_ALIAS_NAMESPACE, alias, normalized,
                 source_revision_id),
            )
            applied.append(alias)
        for alias, normalized in current:
            if normalized not in desired_norms:
                connection.execute(
                    "DELETE FROM entity_aliases WHERE entity_id = %s AND namespace = %s "
                    "AND normalized_alias = %s",
                    (entity_id, PROFILE_ALIAS_NAMESPACE, normalized),
                )
                removed.append(alias)
        return ProfileAliasSync(entity_id=entity_id, entity_name=entity_name,
                                applied=tuple(applied), removed=tuple(removed),
                                skipped_conflicting=tuple(skipped))

    def update(self, command: UpdatePCProfileCommand) -> PCProfileReceipt:
        payload = command.model_dump(
            mode="json", exclude={"document_id", "source_revision_id", "version", "idempotency_key"}
        )
        with self._database.connection() as connection:
            replay = connection.execute(
                """SELECT id, source_document_id, version, alias_sync
                FROM pc_profile_receipts WHERE idempotency_key = %s""",
                (command.idempotency_key,),
            ).fetchone()
            if replay:
                return PCProfileReceipt(
                    receipt_id=replay[0],
                    document_id=replay[1],
                    version=replay[2],
                    idempotent_replay=True,
                    alias_sync=ProfileAliasSync.model_validate(replay[3])
                    if replay[3] else None,
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
            alias_sync = self._sync_aliases(connection, command, source[0])
            receipt_id = uuid4()
            connection.execute(
                """INSERT INTO pc_profile_receipts
                (id, source_document_id, version, idempotency_key, alias_sync)
                VALUES (%s, %s, %s, %s, %s)""",
                (receipt_id, command.document_id, next_version, command.idempotency_key,
                 Jsonb(alias_sync.model_dump(mode="json")) if alias_sync else None),
            )
        return PCProfileReceipt(
            receipt_id=receipt_id,
            document_id=command.document_id,
            version=next_version,
            idempotent_replay=False,
            alias_sync=alias_sync,
        )
