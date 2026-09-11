-- TKT-0064: persist Campaign Core's source-grounded principal-subject classification.
ALTER TABLE candidate_extractions
    ADD COLUMN subject_resolution text NOT NULL DEFAULT 'named_identity'
    CHECK (subject_resolution IN ('focal_entity', 'named_identity', 'non_entity'));

ALTER TABLE candidate_extractions
    ALTER COLUMN subject_resolution DROP DEFAULT;
