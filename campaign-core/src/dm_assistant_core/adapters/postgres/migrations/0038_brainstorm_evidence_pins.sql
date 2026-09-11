CREATE TABLE brainstorm_evidence_pins (
    workflow_session_id uuid NOT NULL REFERENCES brainstorm_sessions(workflow_session_id),
    record_id text NOT NULL,
    assertion text NOT NULL,
    citation text NOT NULL,
    entity_id uuid REFERENCES entities(id),
    position integer NOT NULL CHECK (position > 0),
    pinned_at timestamptz NOT NULL,
    PRIMARY KEY (workflow_session_id, record_id),
    UNIQUE (workflow_session_id, position)
);
