"""PostgreSQL identity review queue (TKT-0106 Phase 1)."""

from __future__ import annotations

from uuid import UUID, uuid4

import re

import psycopg
from psycopg.types.json import Jsonb

from dm_assistant_core.adapters.postgres.database import PostgresDatabase
from dm_assistant_core.domain import EntityKind
from dm_assistant_core.application.identity_gaps import (
    QUEUE_NAMESPACE,
    AddAliasDecision,
    CreateEntityDecision,
    GapAliasCandidate,
    IdentityDecisionReceipt,
    IdentityGap,
    IdentityGapQueue,
    IdentityQueueError,
    MarkMisspellingDecision,
    FactionRoleSummary,
    IdentityDecisionEntry,
    MembershipDecision,
    RoleDeclarationSummary,
    RevertDecision,
    RoleDecision,
    RoleDefinitionDecision,
    SurfaceDecision,
    mine_gaps,
    normalize_surface,
    related_surfaces,
    role_hint_surfaces,
    strip_title_prefix,
    suggest_kind,
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
                "SELECT e.id, lower(e.canonical_name), e.canonical_name, e.entity_type, "
                "coalesce((SELECT array_agg(lower(a.normalized_alias)) FROM entity_aliases a "
                "WHERE a.entity_id=e.id), '{}') FROM entities e").fetchall()
            decided = {row[0] for row in connection.execute(
                "SELECT normalized_surface FROM identity_decisions "
                "WHERE kind IN ('dismiss','mark_role')").fetchall()}
            role_marked = [row[0] for row in connection.execute(
                "SELECT normalized_surface FROM identity_decisions "
                "WHERE kind = 'mark_role'").fetchall()]
            demand = {row[0]: int(row[1]) for row in connection.execute(
                "SELECT normalized_surface, occurrences FROM identity_demand_log").fetchall()}
        known_names = set()
        display_name: dict[str, str] = {}
        entity_by_name: dict[str, tuple[UUID, str]] = {}
        for entity_id, canonical, display, entity_type, aliases in known_rows:
            known_names.add(canonical)
            known_names.update(aliases)
            display_name.setdefault(canonical, display)
            entity_by_name.setdefault(canonical, (entity_id, entity_type))

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
            candidates = sorted(
                name for name in known_names
                if len(name) > 3 and len(gap.normalized_surface) > 3
                and (name in gap.normalized_surface or gap.normalized_surface in name)
                and name in entity_by_name)
            candidate_kinds = [entity_by_name[name][1] for name in candidates]
            content = [word for word in gap.normalized_surface.split()
                       if word not in ("of", "the", "de", "le", "la", "von", "van")]
            suggested_kind = suggest_kind(gap.normalized_surface, candidate_kinds)
            gaps.append(gap.model_copy(update={
                "retrieval_demand": demand.get(gap.normalized_surface, 0),
                "role_hint": bool(content and content[-1] in role_finals),
                "suggested_canonical_name": strip_title_prefix(gap.surface),
                "suggested_kind": EntityKind(suggested_kind) if suggested_kind else None,
                "related_surfaces": related.get(gap.normalized_surface, ()),
                "alias_candidates": tuple(
                    GapAliasCandidate(entity_id=entity_by_name[name][0],
                                      canonical_name=display_name.get(name, name),
                                      entity_kind=EntityKind(entity_by_name[name][1]))
                    for name in candidates)}))
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

    def mark_misspelling(self, decision: MarkMisspellingDecision) -> IdentityDecisionReceipt:
        """A misspelling resolves lookups and links claims, but is never a name."""
        return self._resolve_alias(AddAliasDecision(
            surface=decision.surface, entity_id=decision.entity_id,
            idempotency_key=decision.idempotency_key), "mark_misspelling")

    def add_alias(self, decision: AddAliasDecision) -> IdentityDecisionReceipt:
        """Evidence-sourced alias; names owned by other identities are never stolen."""
        return self._resolve_alias(decision, "add_alias")

    def _resolve_alias(self, decision: AddAliasDecision,
                       decision_kind: str) -> IdentityDecisionReceipt:
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
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (uuid4(), decision.entity_id, QUEUE_NAMESPACE,
                 decision.surface.strip(), normalized,
                 "misspelling" if decision_kind == "mark_misspelling" else "queue_decision",
                 revision[0]),
            )
            surface = decision.surface.strip()
            pattern = r"\m" + re.sub(r"\s+", r"\\s+", surface) + r"\M"
            operator = "~" if any(ch.isupper() for ch in surface) else "~*"
            with connection.cursor() as cursor:
                cursor.execute(
                    f"INSERT INTO claim_related_entities (claim_id, entity_id, relation_kind) "
                    f"SELECT c.id, %s, 'derived_mention' FROM claims c "
                    f"WHERE c.state IN ('established','observed','intended','prepared') "
                    f"AND NOT EXISTS (SELECT 1 FROM claim_supersessions cs "
                    f"WHERE cs.superseded_claim_id=c.id) "
                    f"AND c.assertion_text {operator} %s ON CONFLICT DO NOTHING",
                    (decision.entity_id, pattern))
                linked = cursor.rowcount
            return self._record(connection, decision_kind, decision.surface, normalized,
                                decision.entity_id, decision.idempotency_key,
                                {"linked_claims": linked,
                                 "alias_kind": "misspelling" if decision_kind == "mark_misspelling" else "queue_decision"})

    def correct_canonical_name(self, decision) -> "IdentityDecisionReceipt":
        """Receipted canonical-name correction through the migration-owned
        write (0076): the entity row updates, the old name survives as an
        alias so surfaces keep resolving, the decision is on the audit."""
        new_name = decision.new_name.strip()
        normalized = normalize_surface(new_name)
        with self._database.connection() as connection:
            replay = self._replay(connection, decision.idempotency_key)
            if replay:
                return replay
            try:
                row = connection.execute(
                    "SELECT correct_identity_canonical_name(%s, %s)",
                    (decision.entity_id, new_name),
                ).fetchone()
            except psycopg.DatabaseError as error:
                if error.sqlstate == "P0001":
                    raise IdentityQueueError(str(error).splitlines()[0]) from error
                raise
            payload = row[0]
            return self._record(connection, "correct_name", new_name, normalized,
                                decision.entity_id, decision.idempotency_key,
                                {"old_name": payload["old_name"],
                                 "new_name": payload["new_name"]})

    def create_entity(self, decision: CreateEntityDecision) -> IdentityDecisionReceipt:
        """Entity creation (optionally merging related surfaces) stays behind
        the database's auditable write boundary."""
        surface = decision.surface.strip()
        normalized = normalize_surface(surface)
        aliases = tuple(alias.strip() for alias in decision.alias_surfaces
                        if alias.strip() and alias.strip() != surface)
        manual = tuple(alias.strip() for alias in decision.manual_aliases
                       if alias.strip() and alias.strip() != surface)
        with self._database.connection() as connection:
            replay = self._replay(connection, decision.idempotency_key)
            if replay:
                return replay
            try:
                row = connection.execute(
                    "SELECT apply_identity_queue_create_identity(%s, %s, %s, %s, %s, %s)",
                    (surface, normalized, decision.entity_kind.value,
                     list(aliases), list(manual), decision.idempotency_key),
                ).fetchone()
            except psycopg.DatabaseError as error:
                if error.sqlstate == "P0001":
                    raise IdentityQueueError(str(error).splitlines()[0]) from error
                raise
            payload = row[0]
            return IdentityDecisionReceipt(
                decision_id=payload["decision_id"], kind="create_entity",
                surface=surface, entity_id=payload["entity_id"],
                linked_claims=int(payload.get("linked_claims", 0)),
                idempotent_replay=bool(payload["idempotent_replay"]))

    def revert(self, decision: RevertDecision) -> IdentityDecisionReceipt:
        """Reverse a prior decision; both receipts remain in audit history.

        v1 reverts add_alias decisions: the alias is removed and the entity's
        derived claim links are reconciled against its remaining names —
        links still justified by the canonical name or a surviving alias stay.
        """
        with self._database.connection() as connection:
            replay = self._replay(connection, decision.idempotency_key)
            if replay:
                return replay
            original = connection.execute(
                "SELECT kind, surface, normalized_surface, entity_id FROM "
                "identity_decisions WHERE id = %s", (decision.decision_id,)).fetchone()
            if original is None:
                raise IdentityQueueError("no decision matches that receipt")
            already = connection.execute(
                "SELECT 1 FROM identity_decisions WHERE kind = 'revert' AND "
                "details->>'reverts' = %s", (str(decision.decision_id),)).fetchone()
            if already:
                raise IdentityQueueError("that decision was already reverted")
            if original[0] not in ("add_alias", "mark_misspelling") or original[3] is None:
                raise IdentityQueueError(
                    "only alias and misspelling decisions can be reverted so far; "
                    "entity retirement follows the reviewed supersession pattern")

            aliases_removed = connection.execute(
                "DELETE FROM entity_aliases WHERE entity_id = %s AND namespace = %s "
                "AND normalized_alias = %s",
                (original[3], QUEUE_NAMESPACE, original[2])).rowcount
            # Reconcile: keep derived links still justified by a current name.
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    DELETE FROM claim_related_entities cre
                    WHERE cre.entity_id = %s AND cre.relation_kind = 'derived_mention'
                    AND NOT EXISTS (
                        SELECT 1 FROM claims c
                        WHERE c.id = cre.claim_id
                          AND c.state IN ('established','observed','intended','prepared')
                          AND NOT EXISTS (SELECT 1 FROM claim_supersessions cs
                                          WHERE cs.superseded_claim_id = c.id)
                          AND ((CASE WHEN (SELECT canonical_name FROM entities WHERE id = %s) ~ '[A-Z]'
                                THEN c.assertion_text ~ ('\m' || regexp_replace(
                                     (SELECT canonical_name FROM entities WHERE id = %s), '\s+', '\s+', 'g') || '\M')
                                ELSE c.assertion_text ~* ('\m' || regexp_replace(
                                     (SELECT canonical_name FROM entities WHERE id = %s), '\s+', '\s+', 'g') || '\M') END)
                               OR EXISTS (
                                   SELECT 1 FROM entity_aliases a
                                   WHERE a.entity_id = %s
                                     AND (CASE WHEN a.alias ~ '[A-Z]'
                                          THEN c.assertion_text ~ ('\m' || regexp_replace(a.alias, '\s+', '\s+', 'g') || '\M')
                                          ELSE c.assertion_text ~* ('\m' || regexp_replace(a.alias, '\s+', '\s+', 'g') || '\M') END))))
                    """,
                    (original[3], original[3], original[3], original[3], original[3]))
                links_removed = cursor.rowcount
            return self._record(connection, "revert", original[1], original[2],
                                original[3], decision.idempotency_key,
                                {"reverts": str(decision.decision_id),
                                 "aliases_removed": aliases_removed,
                                 "links_removed": links_removed})

    def reconcile_links(self, entity_id, idempotency_key: str) -> IdentityDecisionReceipt:
        """Link claims for an existing identity's names (canonical + aliases).

        Audited pure-linking for identities created before claim-linking
        existed, or whose names arrived by paths that do not link.
        """
        with self._database.connection() as connection:
            replay = self._replay(connection, idempotency_key)
            if replay:
                return replay
            try:
                row = connection.execute(
                    "SELECT apply_identity_reconcile_links(%s, %s)",
                    (entity_id, idempotency_key)).fetchone()
            except psycopg.DatabaseError as error:
                if error.sqlstate == "P0001":
                    raise IdentityQueueError(str(error).splitlines()[0]) from error
                raise
            payload = row[0]
            entity_name = connection.execute(
                "SELECT canonical_name FROM entities WHERE id = %s",
                (entity_id,)).fetchone()
            return IdentityDecisionReceipt(
                decision_id=connection.execute(
                    "SELECT id FROM identity_decisions WHERE idempotency_key = %s",
                    (idempotency_key,)).fetchone()[0],
                kind="reconcile_links", surface=str(entity_name[0]),
                entity_id=entity_id,
                linked_claims=int(payload.get("linked_claims", 0)),
                idempotent_replay=bool(payload.get("idempotent_replay", False)))

    def membership(self, decision: MembershipDecision) -> IdentityDecisionReceipt:
        """Roster management behind the audited membership decision."""
        with self._database.connection() as connection:
            replay = self._replay(connection, decision.idempotency_key)
            if replay:
                return replay
            try:
                connection.execute(
                    "SELECT apply_membership_decision(%s, %s, %s, %s, %s, %s)",
                    (decision.faction_id, decision.member_id,
                     decision.role_title or "" if decision.add else None,
                     decision.source_claim_id, not decision.add,
                     decision.idempotency_key))
            except psycopg.DatabaseError as error:
                if error.sqlstate == "P0001":
                    raise IdentityQueueError(str(error).splitlines()[0]) from error
                raise
            row = connection.execute(
                "SELECT id, surface, entity_id FROM identity_decisions "
                "WHERE idempotency_key = %s", (decision.idempotency_key,)).fetchone()
            return IdentityDecisionReceipt(decision_id=row[0], kind="membership",
                                          surface=row[1], entity_id=row[2],
                                          idempotent_replay=False)

    def define_role(self, decision: RoleDefinitionDecision) -> IdentityDecisionReceipt:
        """Define a (possibly vacant) role for a faction, audited."""
        with self._database.connection() as connection:
            replay = self._replay(connection, decision.idempotency_key)
            if replay:
                return replay
            try:
                connection.execute(
                    "SELECT apply_role_decision(%s, NULL, %s, %s, NULL, %s)",
                    (decision.faction_id, decision.role_name,
                     decision.is_leadership, decision.idempotency_key))
            except psycopg.DatabaseError as error:
                if error.sqlstate == "P0001":
                    raise IdentityQueueError(str(error).splitlines()[0]) from error
                raise
            row = connection.execute(
                "SELECT id, surface, entity_id FROM identity_decisions "
                "WHERE idempotency_key = %s", (decision.idempotency_key,)).fetchone()
            return IdentityDecisionReceipt(decision_id=row[0], kind="membership",
                                          surface=row[1], entity_id=row[2],
                                          idempotent_replay=False)

    def roles(self) -> tuple[FactionRoleSummary, ...]:
        """Cross-faction role listing: definitions, linkage, current holders."""
        with self._database.connection() as connection:
            rows = connection.execute(
                """
                SELECT fr.faction_id, f.canonical_name, fr.name, fr.is_leadership,
                       COALESCE((SELECT array_agg(jsonb_build_object('id', mr.member_id,
                                        'name', me.canonical_name) ORDER BY me.canonical_name)
                        FROM membership_records mr
                        JOIN entities me ON me.id = mr.member_id
                        WHERE mr.faction_id = fr.faction_id AND mr.role_title = fr.name
                          AND mr.superseded_by IS NULL), ARRAY[]::jsonb[])
                FROM faction_roles fr
                JOIN entities f ON f.id = fr.faction_id
                ORDER BY f.canonical_name, fr.is_leadership DESC, lower(fr.name)
                """
            ).fetchall()
        return tuple(
            FactionRoleSummary(
                faction_id=row[0], faction_name=str(row[1]), name=str(row[2]),
                is_leadership=bool(row[3]),
                holders=tuple((item["id"], str(item["name"])) for item in (row[4] or ())))
            for row in rows
        )

    def recent_decisions(self, limit: int = 100) -> tuple[IdentityDecisionEntry, ...]:
        """Durable decision audit, newest first (Log page source)."""
        with self._database.connection() as connection:
            rows = connection.execute(
                """
                SELECT d.id, d.kind, d.surface, d.decided_at, d.details
                FROM identity_decisions d
                ORDER BY d.decided_at DESC, d.id
                LIMIT %s
                """,
                (limit,),
            ).fetchall()
        return tuple(
            IdentityDecisionEntry(decision_id=row[0], kind=str(row[1]), surface=str(row[2]),
                                  decided_at=row[3], details=row[4])
            for row in rows
        )

    def role_declarations(self) -> tuple[RoleDeclarationSummary, ...]:
        """Role-marked surfaces from Identity Review, not yet in any catalog."""
        with self._database.connection() as connection:
            rows = connection.execute(
                """
                SELECT DISTINCT d.surface, d.normalized_surface
                FROM identity_decisions d
                WHERE d.kind = 'mark_role'
                  AND NOT EXISTS (SELECT 1 FROM faction_roles fr
                                  WHERE lower(fr.name) = d.normalized_surface)
                ORDER BY d.normalized_surface
                """
            ).fetchall()
        return tuple(RoleDeclarationSummary(surface=row[0], normalized_surface=row[1])
                     for row in rows)

    def role(self, decision: RoleDecision) -> IdentityDecisionReceipt:
        """Role seating behind the audited membership decision family."""
        with self._database.connection() as connection:
            replay = self._replay(connection, decision.idempotency_key)
            if replay:
                return replay
            try:
                connection.execute(
                    "SELECT apply_role_decision(%s, %s, %s, %s, %s, %s)",
                    (decision.faction_id, decision.member_id,
                     decision.role_name, decision.is_leadership,
                     decision.source_claim_id, decision.idempotency_key))
            except psycopg.DatabaseError as error:
                if error.sqlstate == "P0001":
                    raise IdentityQueueError(str(error).splitlines()[0]) from error
                raise
            row = connection.execute(
                "SELECT id, surface, entity_id FROM identity_decisions "
                "WHERE idempotency_key = %s", (decision.idempotency_key,)).fetchone()
            return IdentityDecisionReceipt(decision_id=row[0], kind="membership",
                                          surface=row[1], entity_id=row[2],
                                          idempotent_replay=False)

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
                entity_id: UUID | None, idempotency_key: str,
                details: dict | None = None) -> IdentityDecisionReceipt:
        decision_id = uuid4()
        connection.execute(
            "INSERT INTO identity_decisions (id, kind, surface, normalized_surface, "
            "entity_id, details, idempotency_key) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (decision_id, kind, surface, normalized, entity_id,
             Jsonb(details) if details else None, idempotency_key))
        return IdentityDecisionReceipt(decision_id=decision_id, kind=kind, surface=surface,
                                       entity_id=entity_id,
                                       linked_claims=int(details.get("linked_claims", 0)) if details else 0,
                                       details=details,
                                       idempotent_replay=False)
