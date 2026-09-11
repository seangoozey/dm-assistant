CREATE TABLE brainstorm_sessions (
    workflow_session_id uuid PRIMARY KEY REFERENCES workflow_sessions(id),
    title text NOT NULL CHECK (length(trim(title)) > 0),
    idempotency_key text NOT NULL UNIQUE
);

CREATE TABLE brainstorm_thoughts (
    id uuid PRIMARY KEY,
    workflow_session_id uuid NOT NULL REFERENCES brainstorm_sessions(workflow_session_id),
    sequence integer NOT NULL CHECK (sequence > 0),
    source_document_id uuid NOT NULL REFERENCES source_documents(id),
    source_revision_id uuid NOT NULL REFERENCES source_revisions(id),
    candidate_id uuid NOT NULL REFERENCES import_candidates(id),
    thought_text text NOT NULL CHECK (length(trim(thought_text)) > 0),
    evidence_json jsonb NOT NULL,
    idempotency_key text NOT NULL UNIQUE,
    captured_at timestamptz NOT NULL,
    UNIQUE (workflow_session_id, sequence),
    UNIQUE (workflow_session_id, source_revision_id),
    UNIQUE (workflow_session_id, candidate_id)
);

CREATE TRIGGER brainstorm_thoughts_immutable
    BEFORE UPDATE OR DELETE ON brainstorm_thoughts
    FOR EACH ROW EXECUTE FUNCTION reject_immutable_row_mutation();
