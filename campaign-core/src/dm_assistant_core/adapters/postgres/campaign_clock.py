"""Persistence for the campaign's current in-game date cursor."""

from dm_assistant_core.adapters.postgres.database import PostgresDatabase
from dm_assistant_core.domain.chronology import CampaignDate


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

    def set_current(self, value: CampaignDate) -> None:
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
