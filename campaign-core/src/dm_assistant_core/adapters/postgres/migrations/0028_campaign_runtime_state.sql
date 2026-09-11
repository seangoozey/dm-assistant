-- Mutable campaign cursor used only as a data-entry default. Canonical chronology
-- remains attached to claims and immutable evidence.
CREATE TABLE campaign_runtime_state (
    state_key text PRIMARY KEY CHECK (state_key = 'current_ingame_date'),
    calendar_id text NOT NULL REFERENCES campaign_calendars(calendar_id),
    campaign_year integer NOT NULL,
    campaign_month smallint NOT NULL CHECK (campaign_month BETWEEN 1 AND 12),
    campaign_day smallint NOT NULL CHECK (campaign_day BETWEEN 1 AND 31),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CHECK (campaign_day_ordinal(calendar_id, campaign_year, campaign_month, campaign_day) IS NOT NULL)
);
