-- A live session may move through zero, one, or many encounters. Context is
-- operational table support and never evidence that prepared material occurred.
ALTER TABLE campaign_session_run_notes
    ADD COLUMN context_kind text NOT NULL DEFAULT 'encounter'
        CHECK (context_kind IN ('general', 'encounter'));

ALTER TABLE campaign_session_run_notes ALTER COLUMN encounter_name DROP NOT NULL;
ALTER TABLE campaign_session_run_notes ALTER COLUMN section_key DROP NOT NULL;
ALTER TABLE campaign_session_run_notes ALTER COLUMN section_title DROP NOT NULL;

ALTER TABLE campaign_session_run_notes
    ADD CONSTRAINT campaign_session_run_notes_context_valid CHECK (
        (context_kind = 'general'
            AND encounter_name IS NULL
            AND section_key IS NULL
            AND section_title IS NULL)
        OR
        (context_kind = 'encounter'
            AND btrim(encounter_name) <> ''
            AND btrim(section_key) <> ''
            AND btrim(section_title) <> '')
    );
