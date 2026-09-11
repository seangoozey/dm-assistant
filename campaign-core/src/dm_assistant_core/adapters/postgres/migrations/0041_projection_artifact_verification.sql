-- Existing manifests remain inactive until an independent artifact read-back.
ALTER TABLE retrieval_projection_builds
    ADD COLUMN artifact_verified_hash text,
    ADD COLUMN artifact_verified_at timestamptz,
    ADD CONSTRAINT artifact_matches_manifest CHECK (
        artifact_verified_hash IS NULL OR artifact_verified_hash = manifest_hash
    );
