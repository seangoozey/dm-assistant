-- Disposable index lifecycle metadata; never campaign truth.
CREATE TABLE retrieval_projection_registry (
    scope_id text PRIMARY KEY,
    visibility_json text NOT NULL,
    generation uuid,
    version bigint NOT NULL CHECK (version > 0),
    updated_at timestamptz NOT NULL DEFAULT now()
);
