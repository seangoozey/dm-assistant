-- Assertion text is the complete claim. Predicate/object are optional retrieval indexes.
ALTER TABLE candidate_extractions
    ALTER COLUMN predicate DROP NOT NULL;

ALTER TABLE candidate_extractions
    DROP CONSTRAINT IF EXISTS candidate_extractions_predicate_check,
    ADD CONSTRAINT candidate_extractions_predicate_nonempty
        CHECK (predicate IS NULL OR length(trim(predicate)) > 0);
