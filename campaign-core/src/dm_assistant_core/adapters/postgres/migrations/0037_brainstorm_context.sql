ALTER TABLE brainstorm_thoughts
    ADD COLUMN mentions_json jsonb NOT NULL DEFAULT '[]'::jsonb;

CREATE TABLE brainstorm_pins (
    workflow_session_id uuid NOT NULL REFERENCES brainstorm_sessions(workflow_session_id),
    entity_id uuid NOT NULL REFERENCES entities(id),
    position integer NOT NULL CHECK (position > 0),
    pinned_at timestamptz NOT NULL,
    PRIMARY KEY (workflow_session_id, entity_id),
    UNIQUE (workflow_session_id, position)
);

