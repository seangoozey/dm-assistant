-- TKT-0121: DM-curated dossier promotion. Promoting a claim to an entry's
-- dossier (or demoting it) is an audited per-claim decision — the latest
-- decision per claim wins.
CREATE TABLE dossier_decisions (
    receipt_id uuid PRIMARY KEY,
    entity_id uuid NOT NULL,
    claim_id uuid NOT NULL,
    action text NOT NULL CHECK (action IN ('promote', 'demote')),
    decided_at timestamptz NOT NULL
);

CREATE INDEX dossier_decisions_entity_idx ON dossier_decisions (entity_id, claim_id, decided_at DESC);
