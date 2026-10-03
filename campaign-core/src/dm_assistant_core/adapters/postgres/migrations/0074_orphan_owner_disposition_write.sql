-- TKT-0138 slice 2: the receipted "no owner needed" write for EXISTING
-- claims. Migration 0073 created claim_owner_dispositions and files receipts
-- for NEW claims inside the change-set apply (the 0148 commit path); the
-- orphan review disposes claims that already exist, through this
-- migration-owned function — the only canonical write path for it.

CREATE OR REPLACE FUNCTION dispose_claim_owner(
    p_claim_id uuid,
    p_reason text
) RETURNS jsonb
LANGUAGE plpgsql
AS $$
DECLARE
    disposed record;
BEGIN
    IF coalesce(btrim(p_reason), '') = '' THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001',
            MESSAGE = 'a no-owner disposition requires a reason';
    END IF;
    SELECT c.id, c.subject_entity_id INTO disposed
      FROM claims c
     WHERE c.id = p_claim_id
       AND NOT EXISTS (SELECT 1 FROM claim_supersessions cs WHERE cs.superseded_claim_id = c.id)
     FOR UPDATE;
    IF disposed.id IS NULL THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001',
            MESSAGE = 'no current claim matches that disposition target';
    END IF;
    IF disposed.subject_entity_id IS NOT NULL THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001',
            MESSAGE = 'that claim already has an owning record';
    END IF;
    IF EXISTS (SELECT 1 FROM claim_owner_dispositions WHERE claim_id = p_claim_id) THEN
        RETURN jsonb_build_object(
            'claim_id', p_claim_id, 'reason', btrim(p_reason), 'already_disposed', true
        );
    END IF;
    INSERT INTO claim_owner_dispositions (claim_id, reason, receipt_id, disposition_at)
    VALUES (p_claim_id, btrim(p_reason), gen_random_uuid(), now());
    RETURN jsonb_build_object(
        'claim_id', p_claim_id, 'reason', btrim(p_reason), 'already_disposed', false
    );
END;
$$;
