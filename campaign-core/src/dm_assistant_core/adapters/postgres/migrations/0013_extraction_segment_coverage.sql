-- TKT-0052: persist deterministic source segments and provider coverage accounting.

ALTER TABLE candidate_extraction_runs
    ADD COLUMN segments_json jsonb NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN coverage_json jsonb NOT NULL DEFAULT '[]'::jsonb;

ALTER TABLE candidate_extractions
    ADD COLUMN source_segment_ids text[] NOT NULL DEFAULT ARRAY['legacy']::text[];

ALTER TABLE candidate_extractions ALTER COLUMN source_segment_ids DROP DEFAULT;

ALTER TABLE candidate_extractions
    ADD CONSTRAINT candidate_extractions_source_segments_nonempty
        CHECK (cardinality(source_segment_ids) > 0);
