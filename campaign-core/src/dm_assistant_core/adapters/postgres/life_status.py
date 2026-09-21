"""Life-status backfill and roster conflict detection (TKT-0123).

The backfill proposes `dead` for entities with an observed, dated death claim
whose profile does not yet carry a life status — a review queue, never a bulk
write. The detector reads the resulting enum: current membership or leadership
seats whose member is dead as of before the seat existed.
"""

from uuid import UUID

from dm_assistant_core.adapters.postgres.database import PostgresDatabase
from dm_assistant_core.application.entity_profiles import (
    EntityProfile, EntityProfileReceipt, UpdateEntityProfileCommand)


class LifeStatusProposal:
    def __init__(self, entity_id, entity_name, death_claim_id, death_assertion,
                 death_date, current_status) -> None:
        self.entity_id = entity_id
        self.entity_name = entity_name
        self.death_claim_id = death_claim_id
        self.death_assertion = death_assertion
        self.death_date = death_date
        self.current_status = current_status


class DeadSeat:
    def __init__(self, member_name, faction_name, role_title, is_leadership,
                 life_status_since, member_id, faction_id) -> None:
        self.member_name = member_name
        self.faction_name = faction_name
        self.role_title = role_title
        self.is_leadership = is_leadership
        self.life_status_since = life_status_since
        self.member_id = member_id
        self.faction_id = faction_id


class PostgresLifeStatusRepository:
    def __init__(self, database: PostgresDatabase, profiles) -> None:
        self._database = database
        self._profiles = profiles

    def proposals(self) -> tuple[LifeStatusProposal, ...]:
        """Entities with observed, dated death claims and no life status yet."""
        with self._database.connection() as connection:
            rows = connection.execute(
                r"""
                SELECT DISTINCT e.id::text, e.canonical_name, c.id::text,
                       left(c.assertion_text, 300),
                       (c.effective_from_year || '-' || lpad(coalesce(c.effective_from_month,0)::text,2,'0')
                        || '-' || lpad(coalesce(c.effective_from_day,0)::text,2,'0')),
                       coalesce(ep.profile_json->>'life_status', '')
                FROM claims c
                JOIN entities e ON (e.id = c.subject_entity_id
                    OR EXISTS (SELECT 1 FROM claim_related_entities cre
                               WHERE cre.claim_id = c.id AND cre.entity_id = e.id))
                LEFT JOIN entity_profiles ep ON ep.entity_id = e.id
                WHERE c.state = 'observed' AND c.authority IN ('real_play','dm_correction')
                  AND c.effective_from_year IS NOT NULL
                  AND c.assertion_text ~* ('(^|[^[:alnum:]])' || replace(e.canonical_name, '''', '') || '([[:space:]]+(was|is|has|had))?[[:space:]]*(died|dead|slain|killed)\M')
                  AND NOT EXISTS (SELECT 1 FROM claim_supersessions cs WHERE cs.superseded_claim_id = c.id)
                  AND (ep.profile_json IS NULL OR (ep.profile_json->>'life_status') IS NULL)
                ORDER BY e.canonical_name
                """
            ).fetchall()
        return tuple(
            LifeStatusProposal(
                entity_id=row[0], entity_name=row[1], death_claim_id=row[2],
                death_assertion=row[3], death_date=row[4], current_status=row[5])
            for row in rows
        )

    def apply(self, entity_id: UUID, status: str, since_year: int,
              since_month: int, since_day: int, claim_id: UUID | None,
              idempotency_key: str) -> EntityProfileReceipt:
        """Confirm a proposal (or set any status) through the audited profile
        update path — versioned row, receipt, idempotent."""
        from dm_assistant_core.domain.retrieval import RequesterVisibility
        dm = RequesterVisibility.model_validate({"role": "dm"})
        profile = self._profiles.get(entity_id, dm)
        if profile is None:
            # Entities never edited have no profile row; seed one from the
            # registry so the status write has a versioned home.
            with self._database.connection() as connection:
                row = connection.execute(
                    "SELECT canonical_name, entity_type FROM entities WHERE id = %s",
                    (entity_id,)).fetchone()
            if row is None:
                raise ValueError("no identity matches that entity")
            profile = EntityProfile(
                entity_id=entity_id, version=0, canonical_name=str(row[0]),
                status=None, location_type=None, parent_location=None, base_location=None,
                player=None, race=None, sex=None, aliases=(), summary="")
        from datetime import date as _date
        from dm_assistant_core.domain.chronology import CampaignDate
        updated = profile.model_copy(update={
            "life_status": status,
            "life_status_since": CampaignDate(
                calendar_id="gregorian-ce", year=since_year,
                month=since_month, day=since_day),
            "life_status_claim_id": claim_id,
        })
        command = UpdateEntityProfileCommand(
            **updated.model_dump(),
            idempotency_key=idempotency_key)
        return self._profiles.update(command, dm)

    def dead_seats(self) -> tuple[DeadSeat, ...]:
        """Current roster seats and leadership held by members whose audited
        life_status is dead (as of before today — seat start dates are not
        tracked, so any dead member on a current roster surfaces)."""
        with self._database.connection() as connection:
            rows = connection.execute(
                """
                SELECT m.canonical_name, f.canonical_name, mr.role_title,
                       coalesce(fr.is_leadership, false),
                       concat(ep.profile_json->'life_status_since'->>'year', '-',
                              lpad(coalesce((ep.profile_json->'life_status_since'->>'month')::text,'0'),2,'0'), '-',
                              lpad(coalesce((ep.profile_json->'life_status_since'->>'day')::text,'0'),2,'0')),
                       m.id::text, f.id::text
                FROM membership_records mr
                JOIN entities m ON m.id = mr.member_id
                JOIN entities f ON f.id = mr.faction_id
                JOIN entity_profiles ep ON ep.entity_id = m.id
                LEFT JOIN faction_roles fr ON fr.faction_id = mr.faction_id AND fr.name = mr.role_title
                WHERE mr.superseded_by IS NULL
                  AND ep.profile_json->>'life_status' = 'dead'
                ORDER BY f.canonical_name, m.canonical_name
                """
            ).fetchall()
        return tuple(
            DeadSeat(member_name=row[0], faction_name=row[1], role_title=row[2],
                     is_leadership=bool(row[3]), life_status_since=row[4],
                     member_id=row[5], faction_id=row[6])
            for row in rows
        )
