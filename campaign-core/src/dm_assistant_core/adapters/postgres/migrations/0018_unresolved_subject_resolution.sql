-- Subject phrases that Core cannot deterministically resolve remain reviewable but
-- cannot silently become canonical identities.
ALTER TABLE candidate_extractions
    DROP CONSTRAINT candidate_extractions_subject_resolution_check,
    ADD CONSTRAINT candidate_extractions_subject_resolution_check
    CHECK (subject_resolution IN ('focal_entity', 'named_identity', 'non_entity', 'unresolved'));
