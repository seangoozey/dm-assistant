CREATE TABLE retrieval_projection_builds (
    generation uuid PRIMARY KEY,
    scope_id text NOT NULL,
    manifest_hash text NOT NULL CHECK (manifest_hash ~ '^[a-f0-9]{64}$'),
    node_count integer NOT NULL CHECK (node_count >= 0),
    edge_count integer NOT NULL CHECK (edge_count >= 0),
    status text NOT NULL CHECK (status IN ('validated', 'revoked')),
    validated_at timestamptz NOT NULL DEFAULT now()
);
