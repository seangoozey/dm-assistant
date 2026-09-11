CREATE TABLE claim_conditions (
    claim_id uuid PRIMARY KEY REFERENCES claims(id),
    trigger_text text,
    reference_type text,
    reference_id uuid,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT claim_conditions_trigger_present CHECK (
        length(trim(coalesce(trigger_text, ''))) > 0 OR reference_id IS NOT NULL
    ),
    CONSTRAINT claim_conditions_reference_complete CHECK (
        (reference_type IS NULL) = (reference_id IS NULL)
    ),
    CONSTRAINT claim_conditions_reference_type CHECK (
        reference_type IS NULL OR reference_type IN ('claim', 'event', 'plan', 'entity')
    )
);

CREATE FUNCTION capture_applied_claim_condition() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    payload jsonb;
BEGIN
    IF NOT NEW.is_conditional THEN
        RETURN NEW;
    END IF;

    SELECT item.after_json INTO payload
      FROM proposal_items item
      JOIN proposal_versions version ON version.id = item.proposal_version_id
      JOIN proposals proposal ON proposal.id = version.proposal_id
     WHERE item.target_id = NEW.id
       AND proposal.workflow_session_id = NEW.session_id
     ORDER BY version.version_number DESC
     LIMIT 1;

    IF payload IS NULL OR (
        length(trim(coalesce(payload->>'condition_text', ''))) = 0
        AND payload->>'condition_reference_id' IS NULL
    ) THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001',
            MESSAGE = 'conditional claim requires an explicit trigger';
    END IF;

    INSERT INTO claim_conditions (claim_id, trigger_text, reference_type, reference_id)
    VALUES (
        NEW.id,
        nullif(trim(payload->>'condition_text'), ''),
        payload->>'condition_reference_type',
        (payload->>'condition_reference_id')::uuid
    );
    RETURN NEW;
END;
$$;

CREATE TRIGGER claims_capture_explicit_condition
AFTER INSERT ON claims
FOR EACH ROW EXECUTE FUNCTION capture_applied_claim_condition();
