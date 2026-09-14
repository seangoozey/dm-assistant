"""PostgreSQL entity profile overlays with alias sync (TKT-0106)."""

from __future__ import annotations

from uuid import UUID, uuid4

from psycopg.types.json import Jsonb

from dm_assistant_core.adapters.postgres.database import PostgresDatabase
from dm_assistant_core.application.entity_profiles import (
    EntityProfile,
    EntityProfileAliasSync,
    EntityProfileError,
    EntityProfileReceipt,
    UpdateEntityProfileCommand,
)

PROFILE_NAMESPACE = "profile"


def _normalize_alias(value: str) -> str:
    return " ".join(value.casefold().split())


class PostgresEntityProfileRepository:
    def __init__(self, database: PostgresDatabase) -> None:
        self._database = database

    def get(self, entity_id: UUID) -> EntityProfile | None:
        with self._database.connection() as connection:
            row = connection.execute(
                "SELECT version, profile_json FROM entity_profiles WHERE entity_id = %s",
                (entity_id,),
            ).fetchone()
        if row is None:
            return None
        return EntityProfile(entity_id=entity_id, version=row[0], **row[1])

    def update(self, command: UpdateEntityProfileCommand) -> EntityProfileReceipt:
        payload = command.model_dump(
            mode="json", exclude={"entity_id", "version", "idempotency_key"})
        with self._database.connection() as connection:
            replay = connection.execute(
                "SELECT id, entity_id, version, alias_sync FROM entity_profile_receipts "
                "WHERE idempotency_key = %s", (command.idempotency_key,)).fetchone()
            if replay:
                return EntityProfileReceipt(
                    receipt_id=replay[0], entity_id=replay[1], version=replay[2],
                    idempotent_replay=True,
                    alias_sync=EntityProfileAliasSync.model_validate(replay[3])
                    if replay[3] else None)
            entity = connection.execute(
                "SELECT canonical_name FROM entities WHERE id = %s FOR UPDATE",
                (command.entity_id,)).fetchone()
            if entity is None:
                raise EntityProfileError("no identity matches that entity")
            current = connection.execute(
                "SELECT version FROM entity_profiles WHERE entity_id = %s FOR UPDATE",
                (command.entity_id,)).fetchone()
            current_version = int(current[0]) if current else 0
            if current_version != command.version:
                raise EntityProfileError("profile version changed; reload before saving")
            next_version = current_version + 1
            connection.execute(
                "INSERT INTO entity_profiles (entity_id, version, profile_json) "
                "VALUES (%s, %s, %s) ON CONFLICT (entity_id) DO UPDATE SET "
                "version = excluded.version, profile_json = excluded.profile_json, "
                "updated_at = now()",
                (command.entity_id, next_version, Jsonb(payload)))
            connection.execute(
                "INSERT INTO entity_profile_revisions (entity_id, version, profile_json) "
                "VALUES (%s, %s, %s)",
                (command.entity_id, next_version, Jsonb(payload)))
            alias_sync = self._sync_aliases(connection, command, str(entity[0]))
            receipt_id = uuid4()
            connection.execute(
                "INSERT INTO entity_profile_receipts (id, entity_id, version, "
                "idempotency_key, alias_sync) VALUES (%s, %s, %s, %s, %s)",
                (receipt_id, command.entity_id, next_version, command.idempotency_key,
                 Jsonb(alias_sync.model_dump(mode="json")) if alias_sync else None))
        return EntityProfileReceipt(
            receipt_id=receipt_id, entity_id=command.entity_id, version=next_version,
            idempotent_replay=False, alias_sync=alias_sync)

    @staticmethod
    def _sync_aliases(connection, command: UpdateEntityProfileCommand,
                      entity_name: str) -> EntityProfileAliasSync | None:
        """The profile editor manages its own 'profile' namespace, matching the
        PC-profile precedent: removals drop only this namespace's rows; names
        owned by other identities are skipped, never stolen."""
        desired, seen = [], set()
        for alias in command.aliases:
            trimmed = alias.strip()
            normalized = _normalize_alias(trimmed)
            if trimmed and normalized not in seen:
                seen.add(normalized)
                desired.append((trimmed, normalized))
        desired_norms = {normalized for _, normalized in desired}
        # The profile editor owns its own namespace plus manual declarations
        # made during identity creation — both are owner-named aliases.
        # Evidence-based queue aliases (queue_decision) are never touched here.
        current = connection.execute(
            "SELECT alias, normalized_alias FROM entity_aliases "
            "WHERE entity_id = %s AND (namespace = %s OR alias_kind = 'manual_declaration')",
            (command.entity_id, PROFILE_NAMESPACE)).fetchall()
        current_norms = {row[1] for row in current}

        applied, removed, skipped = [], [], []
        for alias, normalized in desired:
            if normalized in current_norms or normalized == _normalize_alias(entity_name):
                continue
            # A name this identity already owns in another namespace (an
            # evidence-based queue alias) is already resolved; never duplicate it.
            owned = connection.execute(
                "SELECT 1 FROM entity_aliases WHERE entity_id = %s AND "
                "normalized_alias = %s", (command.entity_id, normalized)).fetchone()
            if owned:
                continue
            conflict = connection.execute(
                "SELECT 1 WHERE EXISTS (SELECT 1 FROM entity_aliases a "
                "WHERE a.normalized_alias = %s AND a.entity_id <> %s) "
                "OR EXISTS (SELECT 1 FROM entities e "
                "WHERE lower(e.canonical_name) = %s AND e.id <> %s)",
                (normalized, command.entity_id, normalized, command.entity_id),
            ).fetchone()
            if conflict:
                skipped.append(alias)
                continue
            revision = connection.execute(
                "SELECT ss.source_revision_id FROM claims c "
                "JOIN claim_evidence ce ON ce.claim_id = c.id "
                "JOIN source_spans ss ON ss.id = ce.source_span_id "
                "JOIN claim_related_entities cre ON cre.claim_id = c.id "
                "WHERE cre.entity_id = %s LIMIT 1", (command.entity_id,)).fetchone()
            if revision is None:
                # An alias must carry evidence provenance; an identity with no
                # linked claims has none to source it from yet.
                skipped.append(alias)
                continue
            connection.execute(
                "INSERT INTO entity_aliases (id, entity_id, namespace, alias, "
                "normalized_alias, alias_kind, source_revision_id) "
                "VALUES (%s, %s, %s, %s, %s, 'profile_edit', %s)",
                (uuid4(), command.entity_id, PROFILE_NAMESPACE, alias, normalized,
                 revision[0]))
            current_norms.add(normalized)
            applied.append(alias)
        for alias, normalized in current:
            if normalized not in desired_norms:
                connection.execute(
                    "DELETE FROM entity_aliases WHERE entity_id = %s "
                    "AND (namespace = %s OR alias_kind = 'manual_declaration') "
                    "AND normalized_alias = %s",
                    (command.entity_id, PROFILE_NAMESPACE, normalized))
                removed.append(alias)
        if not (applied or removed or skipped):
            return None
        return EntityProfileAliasSync(entity_name=entity_name, applied=tuple(applied),
                                      removed=tuple(removed),
                                      skipped_conflicting=tuple(skipped))
