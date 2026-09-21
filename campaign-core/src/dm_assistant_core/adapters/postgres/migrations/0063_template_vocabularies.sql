-- TKT-0129: controlled vocabularies for template enumerations. One receipted
-- list per field; retiring stops a value being offered but keeps it rendering
-- for entries that already carry it.
CREATE TABLE vocabulary_receipts (
    receipt_id uuid PRIMARY KEY,
    vocabulary text NOT NULL,
    action text NOT NULL CHECK (action IN ('add', 'retire')),
    value text NOT NULL,
    changed_at timestamptz NOT NULL
);

CREATE TABLE template_vocabularies (
    vocabulary text NOT NULL,
    value text NOT NULL,
    retired boolean NOT NULL DEFAULT false,
    receipt_id uuid NOT NULL REFERENCES vocabulary_receipts (receipt_id),
    updated_at timestamptz NOT NULL,
    PRIMARY KEY (vocabulary, value)
);
