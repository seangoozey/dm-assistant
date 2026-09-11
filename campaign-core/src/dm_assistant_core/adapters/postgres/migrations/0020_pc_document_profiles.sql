CREATE TABLE pc_document_profiles (
    source_document_id uuid PRIMARY KEY REFERENCES source_documents(id),
    source_revision_id uuid NOT NULL REFERENCES source_revisions(id),
    version integer NOT NULL CHECK (version > 0),
    profile_json jsonb NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE pc_profile_revisions (
    source_document_id uuid NOT NULL REFERENCES source_documents(id),
    source_revision_id uuid NOT NULL REFERENCES source_revisions(id),
    version integer NOT NULL CHECK (version > 0),
    profile_json jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (source_document_id, version)
);
CREATE TABLE pc_profile_receipts (
    id uuid PRIMARY KEY,
    source_document_id uuid NOT NULL REFERENCES source_documents(id),
    version integer NOT NULL,
    idempotency_key text NOT NULL UNIQUE,
    issued_at timestamptz NOT NULL DEFAULT now()
);
