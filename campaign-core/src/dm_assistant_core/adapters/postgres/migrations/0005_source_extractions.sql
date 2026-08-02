CREATE TABLE source_extractions (
    source_revision_id uuid NOT NULL REFERENCES source_revisions(id),
    parser_version text NOT NULL,
    import_run_id uuid REFERENCES import_runs(id) DEFERRABLE INITIALLY DEFERRED,
    extracted_at timestamptz NOT NULL,
    PRIMARY KEY (source_revision_id, parser_version)
);

INSERT INTO source_extractions (
    source_revision_id, parser_version, import_run_id, extracted_at
)
SELECT
    sr.id,
    sr.parser_version,
    observation.import_run_id,
    sr.captured_at
FROM source_revisions sr
LEFT JOIN LATERAL (
    SELECT io.import_run_id
    FROM import_observations io
    WHERE io.source_revision_id = sr.id
    ORDER BY io.id
    LIMIT 1
) observation ON true
WHERE sr.parser_version IS NOT NULL
ON CONFLICT DO NOTHING;

CREATE TRIGGER source_extractions_immutable
    BEFORE UPDATE OR DELETE ON source_extractions
    FOR EACH ROW EXECUTE FUNCTION reject_immutable_row_mutation();
