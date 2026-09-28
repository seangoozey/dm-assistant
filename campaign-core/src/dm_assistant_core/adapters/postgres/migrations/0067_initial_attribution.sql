-- TKT-0140 Step 1 (Sean's ruling 2026-09-22): Assign Ownership over a
-- document's exclusive claims requires INITIAL attribution — claims that
-- have no owner at all (the migration's provenance-first orphans). The
-- function now accepts a NULL old owner, matching subjectless claims.
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
        SELECT 1 FROM claims WHERE id = p_claim_id
          AND ((p_old_entity_id IS NULL AND subject_entity_id IS NULL)
               OR subject_entity_id = p_old_entity_id)
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
