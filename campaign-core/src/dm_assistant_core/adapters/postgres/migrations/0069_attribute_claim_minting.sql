-- TKT-0143: claim-backed attribute minting. Every profile-editor attribute
-- change mints a dated claim behind the dropdown (the life_status pattern
-- generalized); the prior winner supersedes through the presumed-retcon rule
-- (ADR/TKT-0141: an established fact changing with no conflicting observed
-- claim auto-accepts as presumed retcon; the reason is editable later).
CREATE TABLE attribute_claim_bindings (
    entity_id uuid NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    field_name text NOT NULL,
    claim_id uuid NOT NULL REFERENCES claims(id),
    created_at timestamptz NOT NULL,
    PRIMARY KEY (entity_id, field_name)
);

CREATE INDEX attribute_claim_bindings_claim ON attribute_claim_bindings(claim_id);

-- Supersession reasons live on claim_supersessions, which demands a change
-- set; attribute mints carry their own applied change set (workflow session
-- kind 'attribute_mint', already allowed or added alongside).
CREATE TABLE attribute_claim_receipts (
    id bigserial PRIMARY KEY,
    idempotency_key text NOT NULL UNIQUE,
    result jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE OR REPLACE FUNCTION apply_attribute_claim(
    p_entity_id uuid,
    p_field text,
    p_new_value text,
    p_idempotency_key text,
    p_recorded_at timestamptz DEFAULT now()
) RETURNS jsonb
LANGUAGE plpgsql AS $$
DECLARE
    v_claim_id uuid := gen_random_uuid();
    v_change_set_id uuid := gen_random_uuid();
    v_session_id uuid;
    v_prior record;
    v_presumed boolean := false;
    v_opposed_observed boolean;
    v_existing jsonb;
BEGIN
    -- Idempotent per key: the same editor save replays the same claim.
    SELECT result INTO v_existing FROM attribute_claim_receipts
    WHERE idempotency_key = p_idempotency_key;
    IF v_existing IS NOT NULL THEN
        RETURN jsonb_build_object('idempotent_replay', true) || v_existing;
    END IF;

    IF EXISTS (SELECT 1 FROM entities WHERE id = p_entity_id) IS NOT TRUE THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001',
            MESSAGE = 'attribute claim requires an existing record';
    END IF;
    IF btrim(p_new_value) = '' THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001',
            MESSAGE = 'attribute value cannot be blank';
    END IF;

    INSERT INTO workflow_sessions (id, kind, started_at)
    VALUES (gen_random_uuid(), 'lore_entry', p_recorded_at)
    RETURNING id INTO v_session_id;

    INSERT INTO claims (id, subject_entity_id, predicate, assertion_text, state,
        authority, confidence, visibility, is_conditional, predicts_subject_action,
        recorded_at, created_at, updated_at)
    VALUES (v_claim_id, p_entity_id, p_field,
        p_field || ': ' || btrim(p_new_value), 'established', 'explicit_lore',
        1.0, 'dm_only', false, false, p_recorded_at, p_recorded_at, p_recorded_at);

    -- The presumed-retcon check: the prior winner superseding is opposed only
    -- by a conflicting OBSERVED claim on the same record naming this field.
    SELECT b.claim_id, c.state INTO v_prior
    FROM attribute_claim_bindings b
    JOIN claims c ON c.id = b.claim_id
    WHERE b.entity_id = p_entity_id AND b.field_name = p_field;
    IF v_prior IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM claim_supersessions cs WHERE cs.superseded_claim_id = v_prior.claim_id
    ) THEN
        SELECT EXISTS (
            SELECT 1 FROM claims o
            WHERE o.subject_entity_id = p_entity_id
              AND o.state = 'observed'
              AND o.id <> v_prior.claim_id
              AND o.id <> v_claim_id
              AND lower(o.assertion_text) LIKE '%' || lower(p_field) || '%'
        ) INTO v_opposed_observed;
        IF v_opposed_observed THEN
            RAISE EXCEPTION USING ERRCODE = 'P0001',
                MESSAGE = 'an observed claim names this attribute — resolve the conflict before changing it';
        END IF;

        INSERT INTO change_sets (id, idempotency_key, workflow_session_id, status,
            requested_at, applied_at)
        VALUES (v_change_set_id, p_idempotency_key || ':supersede', v_session_id,
            'applied', p_recorded_at, p_recorded_at);
        INSERT INTO claim_supersessions (superseding_claim_id, superseded_claim_id,
            resolution_change_set_id, reason)
        VALUES (v_claim_id, v_prior.claim_id, v_change_set_id, 'presumed retcon');
        v_presumed := true;
    END IF;

    INSERT INTO attribute_claim_bindings (entity_id, field_name, claim_id, created_at)
    VALUES (p_entity_id, p_field, v_claim_id, p_recorded_at)
    ON CONFLICT (entity_id, field_name) DO UPDATE SET
        claim_id = excluded.claim_id, created_at = excluded.created_at;

    INSERT INTO attribute_claim_receipts (idempotency_key, result)
    VALUES (p_idempotency_key,
        jsonb_build_object('claim_id', v_claim_id,
                           'superseded_claim_id', v_prior.claim_id,
                           'presumed_retcon', v_presumed));

    RETURN jsonb_build_object('claim_id', v_claim_id,
        'superseded_claim_id', v_prior.claim_id, 'presumed_retcon', v_presumed);
END;
$$;

