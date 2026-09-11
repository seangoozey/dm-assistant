-- Mutable table-running state. This is deliberately separate from canonical
-- claims and from the immutable session note produced at closeout.
CREATE TABLE campaign_encounter_progress (
    source_document_id uuid PRIMARY KEY REFERENCES source_documents(id) ON DELETE CASCADE,
    source_path text NOT NULL CHECK (btrim(source_path) <> ''),
    encounter_name text NOT NULL CHECK (btrim(encounter_name) <> ''),
    status text NOT NULL DEFAULT 'not_started'
        CHECK (status IN ('not_started', 'in_progress', 'completed', 'abandoned')),
    resume_section_key text,
    resume_section_title text,
    last_session_run_id uuid REFERENCES campaign_session_runs(run_id) ON DELETE SET NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CHECK (
        (resume_section_key IS NULL AND resume_section_title IS NULL)
        OR
        (status = 'in_progress'
            AND btrim(resume_section_key) <> ''
            AND btrim(resume_section_title) <> '')
    )
);

CREATE TABLE campaign_session_run_encounters (
    run_id uuid NOT NULL REFERENCES campaign_session_runs(run_id) ON DELETE CASCADE,
    source_document_id uuid NOT NULL REFERENCES source_documents(id) ON DELETE CASCADE,
    source_path text NOT NULL CHECK (btrim(source_path) <> ''),
    encounter_name text NOT NULL CHECK (btrim(encounter_name) <> ''),
    first_activity_at timestamptz NOT NULL DEFAULT now(),
    last_activity_at timestamptz NOT NULL DEFAULT now(),
    last_section_key text,
    last_section_title text,
    PRIMARY KEY (run_id, source_document_id)
);

CREATE INDEX campaign_session_run_encounters_by_document
    ON campaign_session_run_encounters (source_document_id, last_activity_at DESC);
