-- TKT-0117: campaign clock management. Every change to the current in-game
-- date (DM set/advance, or session capture advancing it) is appended here so
-- the clock is auditable, in the same spirit as decision receipts.
CREATE TABLE campaign_clock_changes (
    id uuid PRIMARY KEY,
    calendar_id text NOT NULL,
    campaign_year integer NOT NULL,
    campaign_month integer NOT NULL,
    campaign_day integer NOT NULL,
    reason text,
    changed_by text NOT NULL DEFAULT 'dm',
    changed_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX campaign_clock_changes_recent_idx ON campaign_clock_changes (changed_at DESC);
