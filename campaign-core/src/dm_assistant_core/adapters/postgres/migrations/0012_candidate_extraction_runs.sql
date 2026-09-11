-- TKT-0050: group immutable candidate extractions into append-only runs.
-- A run exists even when extraction returns no claims, allowing an empty re-extraction
-- to supersede an earlier non-empty result without deleting historical evidence.

CREATE TABLE candidate_extraction_runs (
    id uuid PRIMARY KEY,
    candidate_id uuid NOT NULL REFERENCES import_candidates(id),
    extractor_version text NOT NULL CHECK (length(trim(extractor_version)) > 0),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX candidate_extraction_runs_candidate_idx
    ON candidate_extraction_runs (candidate_id, created_at DESC, id DESC);

ALTER TABLE candidate_extractions ADD COLUMN extraction_run_id uuid;

-- Existing rows predate explicit runs. Group all rows for one candidate into one
-- baseline run while temporarily allowing the migration-only backfill update.
ALTER TABLE candidate_extractions DISABLE TRIGGER candidate_extractions_immutable;
DO $$
DECLARE
    candidate_row record;
    run_id uuid;
BEGIN
    FOR candidate_row IN
        SELECT candidate_id, min(extractor_version) AS extractor_version,
               min(created_at) AS created_at
        FROM candidate_extractions
        GROUP BY candidate_id
    LOOP
        run_id := gen_random_uuid();
        INSERT INTO candidate_extraction_runs (id, candidate_id, extractor_version, created_at)
        VALUES (run_id, candidate_row.candidate_id, candidate_row.extractor_version, candidate_row.created_at);
        UPDATE candidate_extractions
        SET extraction_run_id = run_id
        WHERE candidate_id = candidate_row.candidate_id;
    END LOOP;
END $$;
ALTER TABLE candidate_extractions ENABLE TRIGGER candidate_extractions_immutable;

ALTER TABLE candidate_extractions
    ALTER COLUMN extraction_run_id SET NOT NULL,
    ADD CONSTRAINT candidate_extractions_run_fk
        FOREIGN KEY (extraction_run_id) REFERENCES candidate_extraction_runs(id);

ALTER TABLE candidate_extractions
    DROP CONSTRAINT candidate_extractions_candidate_id_subject_predicate_assert_key,
    ADD CONSTRAINT candidate_extractions_run_claim_key
        UNIQUE (extraction_run_id, subject, predicate, assertion_text);

CREATE INDEX candidate_extractions_run_idx ON candidate_extractions (extraction_run_id);

CREATE TRIGGER candidate_extraction_runs_immutable
    BEFORE UPDATE OR DELETE ON candidate_extraction_runs
    FOR EACH ROW EXECUTE FUNCTION reject_immutable_row_mutation();
