-- Identity review queue decisions (TKT-0106). Derived gap candidates are
-- never stored; only human decisions are durable. Canonical mutations made by
-- decisions still land in entities/entity_aliases/change_sets — this table is
-- the decision audit trail, not a second source of truth.
CREATE TABLE identity_decisions (
    id uuid PRIMARY KEY,
    kind text NOT NULL CHECK (kind IN ('create_entity','add_alias','mark_role','dismiss')),
    surface text NOT NULL,
    normalized_surface text NOT NULL,
    entity_id uuid REFERENCES entities(id),
    details jsonb,
    idempotency_key text NOT NULL UNIQUE,
    decided_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX identity_decisions_surface_idx ON identity_decisions (normalized_surface, kind);

-- Canonical entity creation stays inside the database's auditable write
-- boundary (same pattern as apply_campaign_change_set): adapters only call
-- this function; workflow session, change set, change-set item with exact
-- entity coordinates, entity row, and decision receipt commit atomically.
CREATE FUNCTION apply_identity_queue_create_entity(
    p_surface text,
    p_normalized_surface text,
    p_entity_type text,
    p_idempotency_key text
) RETURNS jsonb
LANGUAGE plpgsql AS $$
DECLARE
    v_workflow uuid := gen_random_uuid();
    v_change_set uuid := gen_random_uuid();
    v_entity uuid := gen_random_uuid();
    v_decision uuid := gen_random_uuid();
    v_existing record;
BEGIN
    SELECT id, entity_id INTO v_existing FROM identity_decisions
     WHERE idempotency_key = p_idempotency_key AND kind = 'create_entity';
    IF FOUND THEN
        RETURN jsonb_build_object('decision_id', v_existing.id,
                                  'entity_id', v_existing.entity_id,
                                  'idempotent_replay', true);
    END IF;
    IF EXISTS (SELECT 1 FROM entities e WHERE lower(e.canonical_name) = p_normalized_surface)
       OR EXISTS (SELECT 1 FROM entity_aliases a WHERE a.normalized_alias = p_normalized_surface) THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001',
            MESSAGE = 'that name already resolves to an identity';
    END IF;
    INSERT INTO workflow_sessions (id, kind, started_at)
    VALUES (v_workflow, 'lore_entry', now());
    INSERT INTO change_sets (id, idempotency_key, workflow_session_id, status,
                             requested_at, applied_at)
    VALUES (v_change_set, p_idempotency_key, v_workflow, 'applied', now(), now());
    INSERT INTO change_set_items (id, change_set_id, outcome, after_json)
    VALUES (gen_random_uuid(), v_change_set, 'applied', jsonb_build_object(
        'record_type', 'entity', 'id', v_entity, 'canonical_name', p_surface,
        'entity_type', p_entity_type, 'entity_kind', p_entity_type,
        'entity_kind_version', 1, 'tags', '[]'::jsonb, 'origin', 'identity_queue'));
    INSERT INTO entities (id, entity_type, canonical_name, created_by_change_set_id,
                          created_at, updated_at)
    VALUES (v_entity, p_entity_type, p_surface, v_change_set, now(), now());
    INSERT INTO identity_decisions (id, kind, surface, normalized_surface,
                                    entity_id, idempotency_key)
    VALUES (v_decision, 'create_entity', p_surface, p_normalized_surface,
            v_entity, p_idempotency_key);
    RETURN jsonb_build_object('decision_id', v_decision, 'entity_id', v_entity,
                              'idempotent_replay', false);
END;
$$;
