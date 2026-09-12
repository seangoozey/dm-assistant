"""PostgreSQL identity review queue (TKT-0106 Phase 1)."""

from __future__ import annotations

from uuid import UUID, uuid4

import psycopg

from dm_assistant_core.adapters.postgres.database import PostgresDatabase
from dm_assistant_core.application.identity_gaps import (
    QUEUE_NAMESPACE,
    AddAliasDecision,
    CreateEntityDecision,
    GapAliasCandidate,
    IdentityDecisionReceipt,
    IdentityGap,
    IdentityGapQueue,
    IdentityQueueError,
    SurfaceDecision,
    mine_gaps,
    normalize_surface,
    related_surfaces,
    role_hint_surfaces,
)

CURRENT_CLAIMS_SQL = """
SELECT c.id, c.assertion_text FROM claims c
WHERE c.state IN ('established','observed','intended','prepared')
AND NOT EXISTS (SELECT 1 FROM claim_supersessions cs WHERE cs.superseded_claim_id=c.id)
"""

EVIDENCE_REVISION_SQL = """
SELECT ss.source_revision_id FROM claims c
JOIN claim_evidence ce ON ce.claim_id = c.id
JOIN source_spans ss ON ss.id = ce.source_span_id
WHERE c.id = (SELECT c2.id FROM claims c2
              WHERE c2.state IN ('established','observed','intended','prepared')
              AND NOT EXISTS (SELECT 1 FROM claim_supersessions cs2
                              WHERE cs2.superseded_claim_id=c2.id)
              AND lower(c2.assertion_text) LIKE %s
              ORDER BY c2.recorded_at, c2.id LIMIT 1)
LIMIT 1
"""


class PostgresIdentityQueueRepository:
    def __init__(self, database: PostgresDatabase) -> None:
        self._database = database

    def queue(self, limit: int) -> IdentityGapQueue:
        with self._database.connection() as connection:
            claims = [(row[0], row[1]) for row in
                      connection.execute(CURRENT_CLAIMS_SQL).fetchall()]
            known_rows = connection.execute(
                "SELECT e.id, lower(e.canonical_name), coalesce((SELECT array_agg("
                "lower(a.normalized_alias)) FROM entity_aliases a WHERE a.entity_id=e.id), "
                "'{}') FROM entities e").fetchall()
            decided = {row[0] for row in connection.execute(
                "SELECT normalized_surface FROM identity_decisions "
                "WHERE kind IN ('dismiss','mark_role')").fetchall()}
            role_marked = [row[0] for row in connection.execute(
                "SELECT normalized_surface FROM identity_decisions "
                "WHERE kind = 'mark_role'").fetchall()]
            demand = {row[0]: int(row[1]) for row in connection.execute(
                "SELECT normalized_surface, occurrences FROM identity_demand_log").fetchall()}
        known_names = set()
        entity_by_name: dict[str, UUID] = {}
        for entity_id, canonical, aliases in known_rows:
            known_names.add(canonical)
            known_names.update(aliases)
            entity_by_name.setdefault(canonical, entity_id)

        candidates = mine_gaps(claims, known_names)
        open_gaps = [gap for gap in candidates
                     if gap.normalized_surface not in decided]
        related = related_surfaces(open_gaps)
        role_finals = role_hint_surfaces(role_marked)
        ranked = sorted(
            open_gaps,
            key=lambda gap: (-demand.get(gap.normalized_surface, 0),
                             -gap.claims_with_phrase, -gap.total_mentions,
                             gap.normalized_surface))
        total = len(ranked)
        gaps = []
        for gap in ranked:
            # Surfaces that now resolve were handled by create/alias decisions.
            alias_candidates = sorted(
                name for name in known_names
                if len(name) > 3 and len(gap.normalized_surface) > 3
                and (name in gap.normalized_surface or gap.normalized_surface in name)
                and name in entity_by_name)
            content = [word for word in gap.normalized_surface.split()
                       if word not in ("of", "the", "de", "le", "la", "von", "van")]
            gaps.append(gap.model_copy(update={
                "retrieval_demand": demand.get(gap.normalized_surface, 0),
                "role_hint": bool(content and content[-1] in role_finals),
                "related_surfaces": related.get(gap.normalized_surface, ()),
                "alias_candidates": tuple(
                    GapAliasCandidate(entity_id=entity_by_name[name], canonical_name=name)
                    for name in alias_candidates)}))
            if len(gaps) >= limit:
                break
        return IdentityGapQueue(gaps=tuple(gaps), total_candidates=total)

    def record_demand(self, surface: str, source: str) -> None:
        """Best-effort demand telemetry: a lookup reached for an unresolving name.

        Names that already resolve are not demand. Failures never break the
        calling read path.
        """
        trimmed = surface.strip()
        normalized = normalize_surface(trimmed)
        if len(normalized) < 3:
            return
        try:
            with self._database.connection() as connection:
                resolves = connection.execute(
                    "SELECT 1 FROM entities e WHERE lower(e.canonical_name) = %s "
                    "UNION SELECT 1 FROM entity_aliases a WHERE a.normalized_alias = %s "
                    "LIMIT 1",
                    (normalized, normalized)).fetchone()
                if resolves:
                    return
                connection.execute(
                    "INSERT INTO identity_demand_log (normalized_surface, surface, source, "
                    "occurrences) VALUES (%s, %s, %s, 1) "
                    "ON CONFLICT (normalized_surface) DO UPDATE SET "
                    "occurrences = identity_demand_log.occurrences + 1, "
                    "surface = excluded.surface, source = excluded.source, "
                    "last_seen = now()",
                    (normalized, trimmed, source))
        except Exception:  # noqa: BLE001 - telemetry must not break reads
            return

    def add_alias(self, decision: AddAliasDecision) -> IdentityDecisionReceipt:
        normalized = normalize_surface(decision.surface)
        with self._database.connection() as connection:
            replay = self._replay(connection, decision.idempotency_key)
            if replay:
                return replay
            entity = connection.execute(
                "SELECT lower(canonical_name) FROM entities WHERE id = %s",
                (decision.entity_id,)).fetchone()
            if entity is None:
                raise IdentityQueueError("alias target entity does not exist")
            if normalized == entity[0]:
                raise IdentityQueueError("the canonical name already resolves; no alias needed")
            conflict = connection.execute(
                "SELECT 1 WHERE EXISTS (SELECT 1 FROM entity_aliases a "
                "WHERE a.normalized_alias = %s AND a.entity_id <> %s) "
                "OR EXISTS (SELECT 1 FROM entities e WHERE lower(e.canonical_name) = %s "
                "AND e.id <> %s)",
                (normalized, decision.entity_id, normalized, decision.entity_id),
            ).fetchone()
            if conflict:
                raise IdentityQueueError(
                    "that name belongs to another identity; merge requires explicit review")
            revision = connection.execute(
                EVIDENCE_REVISION_SQL, (f"%{decision.surface.lower()}%",)).fetchone()
            if revision is None:
                raise IdentityQueueError(
                    "no current claim evidences this surface; nothing to source the alias from")
            connection.execute(
                "INSERT INTO entity_aliases (id, entity_id, namespace, alias, "
                "normalized_alias, alias_kind, source_revision_id) "
                "VALUES (%s, %s, %s, %s, %s, 'queue_decision', %s)",
                (uuid4(), decision.entity_id, QUEUE_NAMESPACE,
                 decision.surface.strip(), normalized, revision[0]),
            )
            return self._record(connection, "add_alias", decision.surface, normalized,
                                decision.entity_id, decision.idempotency_key)

    def create_entity(self, decision: CreateEntityDecision) -> IdentityDecisionReceipt:
        """Entity creation (optionally merging related surfaces) stays behind
        the database's auditable write boundary."""
        surface = decision.surface.strip()
        normalized = normalize_surface(surface)
        aliases = tuple(alias.strip() for alias in decision.alias_surfaces
                        if alias.strip() and alias.strip() != surface)
        with self._database.connection() as connection:
            replay = self._replay(connection, decision.idempotency_key)
            if replay:
                return replay
            try:
                row = connection.execute(
                    "SELECT apply_identity_queue_create_identity(%s, %s, %s, %s, %s)",
                    (surface, normalized, decision.entity_kind.value,
                     list(aliases), decision.idempotency_key),
                ).fetchone()
            except psycopg.DatabaseError as error:
                if error.sqlstate == "P0001":
                    raise IdentityQueueError(str(error).splitlines()[0]) from error
                raise
            payload = row[0]
            return IdentityDecisionReceipt(
                decision_id=payload["decision_id"], kind="create_entity",
                surface=surface, entity_id=payload["entity_id"],
                idempotent_replay=bool(payload["idempotent_replay"]))

    def mark_role(self, decision: SurfaceDecision) -> IdentityDecisionReceipt:
        return self._surface_only("mark_role", decision)

    def dismiss(self, decision: SurfaceDecision) -> IdentityDecisionReceipt:
        return self._surface_only("dismiss", decision)

    def _surface_only(self, kind: str, decision: SurfaceDecision) -> IdentityDecisionReceipt:
        normalized = normalize_surface(decision.surface)
        with self._database.connection() as connection:
            replay = self._replay(connection, decision.idempotency_key)
            if replay:
                return replay
            return self._record(connection, kind, decision.surface.strip(), normalized,
                                None, decision.idempotency_key)

    @staticmethod
    def _replay(connection, idempotency_key: str) -> IdentityDecisionReceipt | None:
        row = connection.execute(
            "SELECT id, kind, surface, entity_id FROM identity_decisions "
            "WHERE idempotency_key = %s", (idempotency_key,)).fetchone()
        if row is None:
            return None
        return IdentityDecisionReceipt(decision_id=row[0], kind=row[1], surface=row[2],
                                       entity_id=row[3], idempotent_replay=True)

    @staticmethod
    def _record(connection, kind: str, surface: str, normalized: str,
                entity_id: UUID | None, idempotency_key: str) -> IdentityDecisionReceipt:
        decision_id = uuid4()
        connection.execute(
            "INSERT INTO identity_decisions (id, kind, surface, normalized_surface, "
            "entity_id, idempotency_key) VALUES (%s, %s, %s, %s, %s, %s)",
            (decision_id, kind, surface, normalized, entity_id, idempotency_key))
        return IdentityDecisionReceipt(decision_id=decision_id, kind=kind, surface=surface,
                                       entity_id=entity_id, idempotent_replay=False)
