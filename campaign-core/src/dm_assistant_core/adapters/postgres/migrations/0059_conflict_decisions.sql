-- TKT-0097: conflict review decisions. Detected conflicts are computed live
-- (never stored as truth); only DM decisions are durable. Dismissal records
-- "reviewed, kept both"; supersession retires the losing claim through the
-- same audited change-set machinery as every other canonical mutation.
CREATE TABLE conflict_decisions (
    id uuid PRIMARY KEY,
    claim_a_id uuid NOT NULL REFERENCES claims(id),
    claim_b_id uuid NOT NULL REFERENCES claims(id),
    action text NOT NULL CHECK (action IN ('dismiss', 'supersede')),
    reason text NOT NULL,
    resolution_change_set_id uuid,
    decided_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (claim_a_id, claim_b_id)
);

CREATE FUNCTION apply_conflict_decision(
    p_claim_a_id uuid,
    p_claim_b_id uuid,
    p_action text,
    p_reason text
) RETURNS jsonb
LANGUAGE plpgsql AS $$
DECLARE
    v_decision uuid := gen_random_uuid();
    v_workflow uuid;
    v_change_set uuid;
    v_item uuid;
    v_receipt uuid;
    v_now timestamptz := now();
BEGIN
    IF p_action NOT IN ('dismiss', 'supersede') THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'action must be dismiss or supersede';
    END IF;
    IF nullif(btrim(coalesce(p_reason, '')), '') IS NULL THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'a reason is required';
    END IF;
    IF EXISTS (SELECT 1 FROM conflict_decisions WHERE claim_a_id = p_claim_a_id AND claim_b_id = p_claim_b_id) THEN
        RETURN jsonb_build_object('idempotent_replay', true);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM claims WHERE id = p_claim_a_id)
       OR NOT EXISTS (SELECT 1 FROM claims WHERE id = p_claim_b_id) THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'both claims must exist';
    END IF;

    IF p_action = 'supersede' THEN
        v_workflow := gen_random_uuid();
        v_change_set := gen_random_uuid();
        v_item := gen_random_uuid();
        v_receipt := gen_random_uuid();
        INSERT INTO workflow_sessions (id, kind, started_at) VALUES (v_workflow, 'real_play', v_now);
        INSERT INTO change_sets (id, idempotency_key, workflow_session_id, status, requested_at, applied_at)
        VALUES (v_change_set, 'conflict:' || v_decision, v_workflow, 'applied', v_now, v_now);
        INSERT INTO claim_supersessions (superseding_claim_id, superseded_claim_id, resolution_change_set_id, reason)
        VALUES (p_claim_a_id, p_claim_b_id, v_change_set, btrim(p_reason));
        INSERT INTO change_set_items (id, change_set_id, outcome, before_json, after_json)
        VALUES (v_item, v_change_set, 'applied',
                jsonb_build_object('conflict', 'claim pair', 'claim_a', p_claim_a_id, 'claim_b', p_claim_b_id),
                jsonb_build_object('action', 'supersede', 'superseded_claim_id', p_claim_b_id,
                                   'superseding_claim_id', p_claim_a_id, 'reason', btrim(p_reason)));
        INSERT INTO receipts (id, change_set_id, decision_json, conflict_json, outcome, issued_at)
        VALUES (v_receipt, v_change_set,
                jsonb_build_object('action', 'supersede', 'reason', btrim(p_reason),
                                   'claim_a', p_claim_a_id, 'claim_b', p_claim_b_id),
                '{}'::jsonb, 'applied', v_now);
    END IF;

    INSERT INTO conflict_decisions (id, claim_a_id, claim_b_id, action, reason, resolution_change_set_id)
    VALUES (v_decision, p_claim_a_id, p_claim_b_id, p_action, btrim(p_reason),
            CASE WHEN p_action = 'supersede' THEN v_change_set END);
    RETURN jsonb_build_object('decision_id', v_decision,
                              'change_set_id', v_change_set,
                              'idempotent_replay', false);
END;
$$;
