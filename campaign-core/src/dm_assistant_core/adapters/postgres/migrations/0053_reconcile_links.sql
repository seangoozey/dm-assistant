-- TKT-0106 follow-up: audited pure-linking reconcile for identities created
-- before claim-linking existed (Myrin, and the migration-era backfill), or
-- whose claim text mentions names added by other paths. Inserts
-- derived_mention rows for an entity's canonical name and all its aliases
-- using the same whole-word, case-aware rule as create and alias decisions;
-- records a receipted reconcile_links decision.
-- Idempotent: safe when the objects already exist outside the migration
-- runner's bookkeeping.
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint
                 WHERE conrelid = 'identity_decisions'::regclass
                 AND conname = 'identity_decisions_kind_check'
                 AND pg_get_constraintdef(oid) LIKE '%reconcile_links%') THEN
    ALTER TABLE identity_decisions DROP CONSTRAINT identity_decisions_kind_check;
    ALTER TABLE identity_decisions ADD CONSTRAINT identity_decisions_kind_check
        CHECK (kind IN ('create_entity','add_alias','mark_role','dismiss','revert',
                        'mark_misspelling','reconcile_links'));
  END IF;
END $$;

CREATE OR REPLACE FUNCTION apply_identity_reconcile_links(
    p_entity_id uuid,
    p_idempotency_key text
) RETURNS jsonb
LANGUAGE plpgsql AS $$
DECLARE
    v_entity record;
    v_linked integer := 0;
BEGIN
    SELECT id, canonical_name INTO v_entity FROM entities WHERE id = p_entity_id;
    IF NOT FOUND THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'no identity matches that entity';
    END IF;

    IF EXISTS (SELECT 1 FROM identity_decisions
               WHERE idempotency_key = p_idempotency_key AND kind = 'reconcile_links') THEN
        RETURN jsonb_build_object('linked_claims', 0, 'idempotent_replay', true);
    END IF;

    WITH names AS (
        SELECT v_entity.canonical_name AS name
        UNION
        SELECT a.alias FROM entity_aliases a WHERE a.entity_id = p_entity_id
    ),
    matched AS (
        SELECT DISTINCT c.id FROM claims c, names n
        WHERE c.state IN ('established','observed','intended','prepared')
          AND NOT EXISTS (SELECT 1 FROM claim_supersessions cs
                          WHERE cs.superseded_claim_id = c.id)
          AND (CASE WHEN n.name ~ '[A-Z]'
               THEN c.assertion_text ~ ('\m' || regexp_replace(n.name, '\s+', '\s+', 'g') || '\M')
               ELSE c.assertion_text ~* ('\m' || regexp_replace(n.name, '\s+', '\s+', 'g') || '\M') END)
    )
    INSERT INTO claim_related_entities (claim_id, entity_id, relation_kind)
    SELECT matched.id, p_entity_id, 'derived_mention' FROM matched
    ON CONFLICT DO NOTHING;
    GET DIAGNOSTICS v_linked = ROW_COUNT;

    INSERT INTO identity_decisions (id, kind, surface, normalized_surface,
                                    entity_id, details, idempotency_key)
    VALUES (gen_random_uuid(), 'reconcile_links', v_entity.canonical_name,
            lower(v_entity.canonical_name), p_entity_id,
            jsonb_build_object('linked_claims', v_linked), p_idempotency_key);
    RETURN jsonb_build_object('linked_claims', v_linked, 'idempotent_replay', false);
END;
$$;
