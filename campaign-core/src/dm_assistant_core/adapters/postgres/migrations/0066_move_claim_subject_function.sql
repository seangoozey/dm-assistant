-- TKT-0136 compliance fix (flagged by test_boundaries): the canonical
-- re-attribution write moves into a migration-owned database function.
-- Defense in depth: idempotent on the receipt, loud on a raced owner change.
CREATE OR REPLACE FUNCTION move_claim_subject(
    p_receipt_id uuid,
    p_claim_id uuid,
    p_old_entity_id uuid,
    p_new_entity_id uuid,
    p_reason text,
    p_moved_at timestamptz
) RETURNS jsonb
LANGUAGE plpgsql AS $$
BEGIN
    IF EXISTS (SELECT 1 FROM claim_reattributions WHERE receipt_id = p_receipt_id) THEN
        RETURN jsonb_build_object('idempotent_replay', true);
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM claims WHERE id = p_claim_id AND subject_entity_id = p_old_entity_id
    ) THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001',
            MESSAGE = 'claim is no longer owned by the expected record';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM entities WHERE id = p_new_entity_id) THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001',
            MESSAGE = 're-attribution target does not exist';
    END IF;
    IF p_old_entity_id = p_new_entity_id THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001',
            MESSAGE = 'a claim cannot be re-attributed to its current owner';
    END IF;
    UPDATE claims SET subject_entity_id = p_new_entity_id, updated_at = now()
    WHERE id = p_claim_id;
    INSERT INTO claim_reattributions
        (receipt_id, claim_id, old_entity_id, new_entity_id, reason, moved_at)
    VALUES
        (p_receipt_id, p_claim_id, p_old_entity_id, p_new_entity_id, p_reason, p_moved_at);
    RETURN jsonb_build_object('idempotent_replay', false);
END;
$$;
