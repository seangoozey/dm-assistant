CREATE TABLE claim_reconciliation_decisions (
    id uuid PRIMARY KEY,
    superseding_claim_id uuid NOT NULL REFERENCES claims(id),
    superseded_claim_id uuid NOT NULL REFERENCES claims(id),
    decision text NOT NULL CHECK (decision IN ('retain_both', 'duplicate', 'supersede')),
    superseding_snapshot_hash text NOT NULL CHECK (superseding_snapshot_hash ~ '^[0-9a-f]{64}$'),
    superseded_snapshot_hash text NOT NULL CHECK (superseded_snapshot_hash ~ '^[0-9a-f]{64}$'),
    reason text NOT NULL CHECK (length(trim(reason)) > 0),
    receipt_id uuid NOT NULL UNIQUE REFERENCES receipts(id),
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (superseding_claim_id <> superseded_claim_id)
);

CREATE INDEX claim_reconciliation_pair_idx
    ON claim_reconciliation_decisions (superseding_claim_id, superseded_claim_id, created_at DESC);
