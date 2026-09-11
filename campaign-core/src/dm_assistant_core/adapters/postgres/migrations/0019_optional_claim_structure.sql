-- A complete assertion and its provenance can be canonical without graph enrichment.
ALTER TABLE claims
    ALTER COLUMN subject_entity_id DROP NOT NULL;
