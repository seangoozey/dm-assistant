-- TKT-0138 close (2026-10-02): receipted canonical-name correction. The
-- third blocked case (Ishirala Tower, Mads) made the gap concrete — canonical
-- names are correctable identity facts. The write lives here (migration-
-- owned); the adapter only calls it and files the identity_decisions receipt.

ALTER TABLE identity_decisions DROP CONSTRAINT identity_decisions_kind_check;
ALTER TABLE identity_decisions ADD CONSTRAINT identity_decisions_kind_check
    CHECK (kind = ANY (ARRAY['create_entity', 'add_alias', 'mark_role', 'dismiss',
                           'revert', 'mark_misspelling', 'reconcile_links',
                           'membership', 'correct_name']));

CREATE OR REPLACE FUNCTION correct_identity_canonical_name(
    p_entity_id uuid,
    p_new_name text
) RETURNS jsonb
LANGUAGE plpgsql
AS $$
DECLARE
    old_name text;
    clash_id uuid;
BEGIN
    IF coalesce(btrim(p_new_name), '') = '' THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001',
            MESSAGE = 'a canonical name cannot be empty';
    END IF;
    SELECT canonical_name INTO old_name FROM entities WHERE id = p_entity_id;
    IF old_name IS NULL THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001',
            MESSAGE = 'no identity matches that entity';
    END IF;
    SELECT id INTO clash_id FROM entities
     WHERE id <> p_entity_id
       AND lower(regexp_replace(canonical_name, '[^a-z0-9]+', '', 'gi'))
         = lower(regexp_replace(p_new_name, '[^a-z0-9]+', '', 'gi'));
    IF clash_id IS NOT NULL THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001',
            MESSAGE = 'that name already belongs to another identity';
    END IF;
    UPDATE entities
       SET canonical_name = btrim(p_new_name), updated_at = now()
     WHERE id = p_entity_id;
    -- The old name does NOT become an alias: aliases are provenance-
    -- anchored (0052) and a corrected-away typo should not stay resolvable.
    -- The audit receipt (identity_decisions.details.old_name) preserves it.
    RETURN jsonb_build_object('old_name', old_name, 'new_name', btrim(p_new_name));
END;
$$;
