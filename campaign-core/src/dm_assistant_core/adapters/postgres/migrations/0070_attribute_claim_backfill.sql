-- TKT-0143 backfill: existing populated attributes become unanchored-but-dated
-- claims (the 0123 killer-vs-killed playbook — mark now, nudge toward anchors
-- later; the Qualified audit's Q5 advisory counts them).
INSERT INTO workflow_sessions (id, kind, started_at)
SELECT gen_random_uuid(), 'lore_entry', now()
WHERE EXISTS (SELECT 1 FROM entity_profiles);

DO $$
DECLARE
    v_session uuid;
    v_entity uuid;
    v_profile jsonb;
    v_field text;
    v_value text;
    v_claim uuid;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM entity_profiles) THEN RETURN; END IF;
    SELECT id INTO v_session FROM workflow_sessions
    WHERE kind = 'lore_entry' ORDER BY started_at DESC LIMIT 1;
    FOR v_entity, v_profile IN
        SELECT entity_id, profile_json FROM entity_profiles
    LOOP
        FOREACH v_field IN ARRAY ARRAY['status', 'location_type', 'race', 'sex', 'base_location']
        LOOP
            v_value := nullif(btrim(coalesce(v_profile->>v_field, '')), '');
            IF v_value IS NULL THEN CONTINUE; END IF;
            v_claim := gen_random_uuid();
            INSERT INTO claims (id, subject_entity_id, predicate, assertion_text,
                state, authority, confidence, visibility, is_conditional,
                predicts_subject_action, recorded_at, created_at, updated_at)
            VALUES (v_claim, v_entity, v_field, v_field || ': ' || v_value,
                'established', 'explicit_lore', 1.0, 'dm_only', false, false,
                now(), now(), now());
            INSERT INTO attribute_claim_bindings (entity_id, field_name, claim_id, created_at)
            VALUES (v_entity, v_field, v_claim, now())
            ON CONFLICT (entity_id, field_name) DO NOTHING;
        END LOOP;
        -- parent_location is a NAME reference, not a free value.
        v_value := nullif(btrim(coalesce(v_profile->>'parent_location', '')), '');
        IF v_value IS NOT NULL THEN
            v_claim := gen_random_uuid();
            INSERT INTO claims (id, subject_entity_id, predicate, assertion_text,
                state, authority, confidence, visibility, is_conditional,
                predicts_subject_action, recorded_at, created_at, updated_at)
            VALUES (v_claim, v_entity, 'parent_location',
                'parent_location: ' || v_value, 'established', 'explicit_lore',
                1.0, 'dm_only', false, false, now(), now(), now());
            INSERT INTO attribute_claim_bindings (entity_id, field_name, claim_id, created_at)
            VALUES (v_entity, 'parent_location', v_claim, now())
            ON CONFLICT (entity_id, field_name) DO NOTHING;
        END IF;
    END LOOP;
END $$;
