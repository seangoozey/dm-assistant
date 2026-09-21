-- TKT-0126: receipted prompt overrides. One effective prompt per purpose;
-- clearing an override restores the built-in default. Every save files a
-- receipt so prompt history is auditable like model activation.
CREATE TABLE prompt_override_receipts (
    receipt_id uuid PRIMARY KEY,
    purpose text NOT NULL,
    action text NOT NULL CHECK (action IN ('set', 'clear')),
    version_label text NOT NULL,
    changed_at timestamptz NOT NULL
);

CREATE TABLE prompt_overrides (
    purpose text PRIMARY KEY,
    prompt_text text NOT NULL,
    version_label text NOT NULL,
    receipt_id uuid NOT NULL REFERENCES prompt_override_receipts (receipt_id),
    updated_at timestamptz NOT NULL
);
