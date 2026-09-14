-- TKT-0106: versioned, receipted profile overlays for identities that have no
-- source document of their own (queue-created entities). Mirrors the
-- pc_document_profiles pattern, keyed to the entity. Canonical truth stays in
-- entities/claims; this is presentational, editable metadata with full audit.
CREATE TABLE entity_profiles (
    entity_id uuid PRIMARY KEY REFERENCES entities(id),
    version integer NOT NULL CHECK (version > 0),
    profile_json jsonb NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE entity_profile_revisions (
    entity_id uuid NOT NULL REFERENCES entities(id),
    version integer NOT NULL CHECK (version > 0),
    profile_json jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (entity_id, version)
);

CREATE TABLE entity_profile_receipts (
    id uuid PRIMARY KEY,
    entity_id uuid NOT NULL REFERENCES entities(id),
    version integer NOT NULL,
    idempotency_key text NOT NULL UNIQUE,
    alias_sync jsonb,
    issued_at timestamptz NOT NULL DEFAULT now()
);
