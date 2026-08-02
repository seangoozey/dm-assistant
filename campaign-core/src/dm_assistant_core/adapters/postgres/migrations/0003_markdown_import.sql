ALTER TABLE source_revisions
    ADD COLUMN original_path text,
    ADD COLUMN filesystem_modified_at timestamptz,
    ADD COLUMN discovered_at timestamptz,
    ADD COLUMN parser_version text,
    ADD COLUMN path_policy_version text,
    ADD COLUMN frontmatter_json jsonb,
    ADD COLUMN classification text;

CREATE TABLE source_document_paths (
    source_document_id uuid NOT NULL REFERENCES source_documents(id),
    connector text NOT NULL,
    normalized_path text NOT NULL,
    first_seen_at timestamptz NOT NULL,
    last_seen_at timestamptz NOT NULL,
    is_current boolean NOT NULL,
    missing_scans integer NOT NULL DEFAULT 0 CHECK (missing_scans >= 0),
    missing_reviewed_at timestamptz,
    PRIMARY KEY (source_document_id, normalized_path),
    UNIQUE (connector, normalized_path),
    CHECK (missing_reviewed_at IS NULL OR missing_reviewed_at >= first_seen_at)
);

CREATE UNIQUE INDEX source_document_paths_one_current_uq
    ON source_document_paths (source_document_id)
    WHERE is_current;

CREATE TABLE import_candidates (
    id uuid PRIMARY KEY,
    source_document_id uuid NOT NULL REFERENCES source_documents(id),
    fingerprint text NOT NULL CHECK (fingerprint ~ '^[0-9a-f]{64}$'),
    assertion_text text NOT NULL,
    state claim_state NOT NULL,
    authority authority_kind NOT NULL,
    visibility text NOT NULL CHECK (visibility IN ('dm_only', 'party', 'character')),
    is_conditional boolean NOT NULL,
    predicts_subject_action boolean NOT NULL,
    evidence_only boolean NOT NULL,
    status text NOT NULL CHECK (status IN ('active', 'source_removed')),
    extractor_version text NOT NULL,
    first_seen_import_run_id uuid NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    UNIQUE (source_document_id, fingerprint),
    CONSTRAINT import_candidates_first_seen_run_fk
        FOREIGN KEY (first_seen_import_run_id) REFERENCES import_runs(id)
        DEFERRABLE INITIALLY DEFERRED
);

CREATE TABLE import_candidate_evidence (
    candidate_id uuid NOT NULL REFERENCES import_candidates(id),
    source_revision_id uuid NOT NULL REFERENCES source_revisions(id),
    section_path text NOT NULL,
    start_offset integer NOT NULL CHECK (start_offset >= 0),
    end_offset integer NOT NULL CHECK (end_offset >= start_offset),
    PRIMARY KEY (candidate_id, source_revision_id)
);

ALTER TABLE review_items
    ALTER COLUMN opened_by_change_set_id DROP NOT NULL,
    ADD COLUMN opened_by_import_run_id uuid;

ALTER TABLE review_items
    ADD CONSTRAINT review_items_import_run_fk
        FOREIGN KEY (opened_by_import_run_id) REFERENCES import_runs(id)
        DEFERRABLE INITIALLY DEFERRED,
    ADD CONSTRAINT review_items_exactly_one_opener_ck
        CHECK (num_nonnulls(opened_by_change_set_id, opened_by_import_run_id) = 1);

CREATE TRIGGER import_runs_immutable
    BEFORE UPDATE OR DELETE ON import_runs
    FOR EACH ROW EXECUTE FUNCTION reject_immutable_row_mutation();

CREATE TRIGGER import_observations_immutable
    BEFORE UPDATE OR DELETE ON import_observations
    FOR EACH ROW EXECUTE FUNCTION reject_immutable_row_mutation();
