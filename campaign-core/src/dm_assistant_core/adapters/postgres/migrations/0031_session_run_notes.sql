-- Mutable live-play workspace. These rows are scratch state until wrap-up captures
-- them as immutable session-note evidence and closes the run.
CREATE TABLE campaign_session_runs (
    run_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    status text NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'closed')),
    session_date date NOT NULL,
    calendar_id text REFERENCES campaign_calendars(calendar_id),
    campaign_year integer,
    campaign_month smallint CHECK (campaign_month BETWEEN 1 AND 12),
    campaign_day smallint CHECK (campaign_day BETWEEN 1 AND 31),
    title text NOT NULL CHECK (btrim(title) <> ''),
    captured_source_document_id uuid,
    capture_id uuid,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    closed_at timestamptz,
    CHECK (
        (calendar_id IS NULL AND campaign_year IS NULL AND campaign_month IS NULL AND campaign_day IS NULL)
        OR campaign_day_ordinal(calendar_id, campaign_year, campaign_month, campaign_day) IS NOT NULL
    )
);

CREATE UNIQUE INDEX campaign_session_runs_one_open
    ON campaign_session_runs ((status)) WHERE status = 'open';

CREATE TABLE campaign_session_run_notes (
    note_id uuid PRIMARY KEY,
    run_id uuid NOT NULL REFERENCES campaign_session_runs(run_id) ON DELETE CASCADE,
    source_document_id uuid,
    source_path text NOT NULL,
    encounter_name text NOT NULL CHECK (btrim(encounter_name) <> ''),
    section_key text NOT NULL CHECK (btrim(section_key) <> ''),
    section_title text NOT NULL CHECK (btrim(section_title) <> ''),
    note_text text NOT NULL CHECK (btrim(note_text) <> ''),
    captured_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX campaign_session_run_notes_chronology
    ON campaign_session_run_notes (run_id, captured_at, note_id);

