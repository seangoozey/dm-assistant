-- Derived diagnostics only. These rows are not canonical claims or proposal inputs.
CREATE TABLE candidate_extraction_failures (
    id uuid PRIMARY KEY,
    failure_group_id uuid NOT NULL,
    candidate_id uuid NOT NULL REFERENCES import_candidates(id),
    attempt_number integer NOT NULL CHECK (attempt_number > 0),
    error text NOT NULL CHECK (length(trim(error)) > 0),
    raw_response text,
    extractor_version text NOT NULL,
    model_profile_key text,
    model_slug text,
    prompt_version text,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX candidate_extraction_failures_candidate_idx
    ON candidate_extraction_failures (candidate_id, created_at DESC);

CREATE TRIGGER candidate_extraction_failures_immutable
    BEFORE UPDATE OR DELETE ON candidate_extraction_failures
    FOR EACH ROW EXECUTE FUNCTION reject_immutable_row_mutation();
