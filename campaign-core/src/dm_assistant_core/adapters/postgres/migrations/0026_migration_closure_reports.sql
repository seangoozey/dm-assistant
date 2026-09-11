CREATE TABLE migration_closure_reports (
    id uuid PRIMARY KEY,
    migration_key text NOT NULL UNIQUE CHECK (length(btrim(migration_key)) > 0),
    report_hash text NOT NULL CHECK (report_hash ~ '^[0-9a-f]{64}$'),
    report_json jsonb NOT NULL,
    created_at timestamptz NOT NULL
);

CREATE TRIGGER migration_closure_reports_immutable
    BEFORE UPDATE OR DELETE ON migration_closure_reports
    FOR EACH ROW EXECUTE FUNCTION reject_immutable_row_mutation();
