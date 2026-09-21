"""Persistence for the campaign's current in-game date cursor."""

from datetime import datetime
from uuid import uuid4

from dm_assistant_core.adapters.postgres.database import PostgresDatabase
from dm_assistant_core.domain.chronology import CampaignDate


class CampaignClockChange:
    """One recorded change to the current in-game date (TKT-0117)."""

    def __init__(self, date: CampaignDate, changed_at: datetime, reason: str | None,
                 changed_by: str) -> None:
        self.date = date
        self.changed_at = changed_at
        self.reason = reason
        self.changed_by = changed_by


class PostgresCampaignClockRepository:
    def __init__(self, database: PostgresDatabase) -> None:
        self._database = database

    def get_current(self) -> CampaignDate | None:
        with self._database.connection() as connection:
            row = connection.execute(
                "SELECT calendar_id,campaign_year,campaign_month,campaign_day "
                "FROM campaign_runtime_state WHERE state_key='current_ingame_date'"
            ).fetchone()
        return None if row is None else CampaignDate(
            calendar_id=row[0], year=row[1], month=row[2], day=row[3]
        )

    def set_current(self, value: CampaignDate, reason: str | None = None) -> None:
        if not value.is_complete():
            raise ValueError("the current in-game date must include year, month, and day")
        with self._database.connection() as connection:
            connection.execute(
                "INSERT INTO campaign_runtime_state "
                "(state_key,calendar_id,campaign_year,campaign_month,campaign_day) "
                "VALUES ('current_ingame_date',%s,%s,%s,%s) "
                "ON CONFLICT (state_key) DO UPDATE SET calendar_id=excluded.calendar_id, "
                "campaign_year=excluded.campaign_year,campaign_month=excluded.campaign_month, "
                "campaign_day=excluded.campaign_day,updated_at=now()",
                (value.calendar_id, value.year, value.month, value.day),
            )
            connection.execute(
                "INSERT INTO campaign_clock_changes "
                "(id,calendar_id,campaign_year,campaign_month,campaign_day,reason) "
                "VALUES (%s,%s,%s,%s,%s,%s)",
                (uuid4(), value.calendar_id, value.year, value.month, value.day, reason),
            )

    def history(self, limit: int = 10) -> tuple[CampaignClockChange, ...]:
        with self._database.connection() as connection:
            rows = connection.execute(
                "SELECT calendar_id,campaign_year,campaign_month,campaign_day,reason,"
                "changed_by,changed_at FROM campaign_clock_changes "
                "ORDER BY changed_at DESC, id DESC LIMIT %s",
                (limit,),
            ).fetchall()
        return tuple(
            CampaignClockChange(
                date=CampaignDate(calendar_id=row[0], year=row[1], month=row[2], day=row[3]),
                changed_at=row[6], reason=row[4], changed_by=row[5])
            for row in rows
        )
