-- TKT-0099: assertion re-attribution. When Lore creation assigns an
-- assertion to a new entity, the assertion's subject changes and the old
-- owner gets a "moved to" reference. Provenance is untouched.
CREATE TABLE claim_reattributions (
    receipt_id uuid PRIMARY KEY,
    claim_id uuid NOT NULL REFERENCES claims(id),
    old_entity_id uuid NOT NULL REFERENCES entities(id),
    new_entity_id uuid NOT NULL REFERENCES entities(id),
    reason text NOT NULL,
    moved_at timestamptz NOT NULL
);

CREATE INDEX claim_reattributions_old_entity ON claim_reattributions (old_entity_id, moved_at DESC);
CREATE INDEX claim_reattributions_claim ON claim_reattributions (claim_id);
