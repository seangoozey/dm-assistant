CREATE TABLE source_review_dispositions (
    id uuid PRIMARY KEY,
    review_id uuid NOT NULL UNIQUE REFERENCES review_items(id),
    decision text NOT NULL CHECK (decision IN ('acknowledged', 'content_consumed', 'excluded_by_scope')),
    reason text NOT NULL CHECK (length(btrim(reason)) > 0),
    created_at timestamptz NOT NULL
);

CREATE TRIGGER source_review_dispositions_immutable
    BEFORE UPDATE OR DELETE ON source_review_dispositions
    FOR EACH ROW EXECUTE FUNCTION reject_immutable_row_mutation();
