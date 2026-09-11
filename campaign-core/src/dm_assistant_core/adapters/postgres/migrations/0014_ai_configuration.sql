CREATE TABLE ai_configuration_activations (
    receipt_id uuid PRIMARY KEY,
    profile_key text NOT NULL,
    prompt_version text NOT NULL,
    activated_at timestamptz NOT NULL
);

ALTER TABLE candidate_extraction_runs ADD COLUMN model_profile_key text;
ALTER TABLE candidate_extraction_runs ADD COLUMN model_slug text;
ALTER TABLE candidate_extraction_runs ADD COLUMN prompt_version text;
