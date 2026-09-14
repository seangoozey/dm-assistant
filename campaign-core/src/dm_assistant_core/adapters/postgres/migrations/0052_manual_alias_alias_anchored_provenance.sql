-- TKT-0106: manual-alias provenance anchors to whatever actually exists in
-- claims. When the DM expands a canonical name beyond what sources say
-- (claims mention "Penelope"; canonical becomes "Penelope Clinkhammer"),
-- the alias's own claim evidence is the right provenance anchor — the
-- canonical surface text is only the fallback.
CREATE OR REPLACE FUNCTION apply_identity_queue_create_identity(
    p_surface text,
    p_normalized_surface text,
    p_entity_type text,
    p_alias_surfaces text[],
    p_manual_aliases text[],
    p_idempotency_key text
) RETURNS jsonb
LANGUAGE plpgsql AS $$
DECLARE
    v_workflow uuid := gen_random_uuid();
    v_change_set uuid := gen_random_uuid();
    v_entity uuid := gen_random_uuid();
    v_decision uuid := gen_random_uuid();
    v_existing record;
    v_alias text;
    v_alias_normalized text;
    v_revision uuid;
    v_linked integer := 0;
    v_name_pattern text;
BEGIN
    SELECT id, entity_id INTO v_existing FROM identity_decisions
     WHERE idempotency_key = p_idempotency_key AND kind = 'create_entity';
    IF FOUND THEN
        RETURN jsonb_build_object('decision_id', v_existing.id,
                                  'entity_id', v_existing.entity_id,
                                  'linked_claims', 0,
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
        'entity_kind_version', 1, 'tags', '[]'::jsonb, 'origin', 'identity_queue',
        'aliases', to_jsonb(p_alias_surfaces),
        'manual_aliases', to_jsonb(p_manual_aliases)));
    INSERT INTO entities (id, entity_type, canonical_name, created_by_change_set_id,
                          created_at, updated_at)
    VALUES (v_entity, p_entity_type, p_surface, v_change_set, now(), now());

    FOR v_alias IN SELECT DISTINCT unnest(p_alias_surfaces)
    LOOP
        v_alias_normalized := lower(trim(regexp_replace(v_alias, '\s+', ' ', 'g')));
        IF v_alias_normalized = '' OR v_alias_normalized = p_normalized_surface THEN
            CONTINUE;
        END IF;
        IF EXISTS (SELECT 1 FROM entity_aliases a WHERE a.normalized_alias = v_alias_normalized)
           OR EXISTS (SELECT 1 FROM entities e WHERE lower(e.canonical_name) = v_alias_normalized) THEN
            RAISE EXCEPTION USING ERRCODE = 'P0001',
                MESSAGE = 'alias "' || v_alias || '" belongs to another identity; merge requires explicit review';
        END IF;
        SELECT ss.source_revision_id INTO v_revision
          FROM claims c
          JOIN claim_evidence ce ON ce.claim_id = c.id
          JOIN source_spans ss ON ss.id = ce.source_span_id
         WHERE c.state IN ('established','observed','intended','prepared')
           AND NOT EXISTS (SELECT 1 FROM claim_supersessions cs
                           WHERE cs.superseded_claim_id = c.id)
           AND lower(c.assertion_text) LIKE '%' || lower(v_alias) || '%'
         ORDER BY c.recorded_at, c.id LIMIT 1;
        IF v_revision IS NULL THEN
            RAISE EXCEPTION USING ERRCODE = 'P0001',
                MESSAGE = 'alias "' || v_alias || '" has no current claim evidence';
        END IF;
        INSERT INTO entity_aliases (id, entity_id, namespace, alias, normalized_alias,
                                    alias_kind, source_revision_id)
        VALUES (gen_random_uuid(), v_entity, 'identity_queue', v_alias,
                v_alias_normalized, 'queue_decision', v_revision);
    END LOOP;

    -- Owner-declared aliases: no per-alias evidence requirement, never steal
    -- a name another identity owns, and provenance anchored to the alias's
    -- own claims first, the created surface's claims as fallback.
    FOR v_alias IN SELECT DISTINCT unnest(p_manual_aliases)
    LOOP
        v_alias_normalized := lower(trim(regexp_replace(v_alias, '\s+', ' ', 'g')));
        IF v_alias_normalized = '' OR v_alias_normalized = p_normalized_surface THEN
            CONTINUE;
        END IF;
        IF EXISTS (SELECT 1 FROM entity_aliases a WHERE a.normalized_alias = v_alias_normalized)
           OR EXISTS (SELECT 1 FROM entities e WHERE lower(e.canonical_name) = v_alias_normalized) THEN
            RAISE EXCEPTION USING ERRCODE = 'P0001',
                MESSAGE = 'alias "' || v_alias || '" belongs to another identity; merge requires explicit review';
        END IF;
        SELECT ss.source_revision_id INTO v_revision
          FROM claims c
          JOIN claim_evidence ce ON ce.claim_id = c.id
          JOIN source_spans ss ON ss.id = ce.source_span_id
         WHERE c.state IN ('established','observed','intended','prepared')
           AND NOT EXISTS (SELECT 1 FROM claim_supersessions cs
                           WHERE cs.superseded_claim_id = c.id)
           AND (lower(c.assertion_text) LIKE '%' || lower(v_alias) || '%'
                OR lower(c.assertion_text) LIKE '%' || lower(p_surface) || '%')
         ORDER BY (c.assertion_text ILIKE '%' || v_alias || '%') DESC, c.recorded_at, c.id
         LIMIT 1;
        IF v_revision IS NULL THEN
            RAISE EXCEPTION USING ERRCODE = 'P0001',
                MESSAGE = 'manual alias "' || v_alias || '" has no provenance: no current claim mentions "' || v_alias || '" or "' || p_surface || '"';
        END IF;
        INSERT INTO entity_aliases (id, entity_id, namespace, alias, normalized_alias,
                                    alias_kind, source_revision_id)
        VALUES (gen_random_uuid(), v_entity, 'identity_queue', v_alias,
                v_alias_normalized, 'manual_declaration', v_revision);
    END LOOP;

    v_name_pattern := '\m' || regexp_replace(p_surface, '\s+', '\s+', 'g') || '\M';
    WITH matched AS (
        SELECT c.id FROM claims c
        WHERE c.state IN ('established','observed','intended','prepared')
          AND NOT EXISTS (SELECT 1 FROM claim_supersessions cs
                          WHERE cs.superseded_claim_id = c.id)
          AND ((CASE WHEN p_surface ~ '[A-Z]'
                     THEN c.assertion_text ~ v_name_pattern
                     ELSE c.assertion_text ~* v_name_pattern END)
               OR EXISTS (SELECT 1 FROM unnest(p_alias_surfaces) alias_name
                          WHERE CASE WHEN alias_name ~ '[A-Z]'
                               THEN c.assertion_text ~ ('\m' || regexp_replace(alias_name, '\s+', '\s+', 'g') || '\M')
                               ELSE c.assertion_text ~* ('\m' || regexp_replace(alias_name, '\s+', '\s+', 'g') || '\M') END)
               OR EXISTS (SELECT 1 FROM unnest(p_manual_aliases) alias_name
                          WHERE CASE WHEN alias_name ~ '[A-Z]'
                               THEN c.assertion_text ~ ('\m' || regexp_replace(alias_name, '\s+', '\s+', 'g') || '\M')
                               ELSE c.assertion_text ~* ('\m' || regexp_replace(alias_name, '\s+', '\s+', 'g') || '\M') END))
    )
    INSERT INTO claim_related_entities (claim_id, entity_id, relation_kind)
    SELECT matched.id, v_entity, 'derived_mention' FROM matched
    ON CONFLICT DO NOTHING;
    GET DIAGNOSTICS v_linked = ROW_COUNT;

    INSERT INTO identity_decisions (id, kind, surface, normalized_surface,
                                    entity_id, details, idempotency_key)
    VALUES (v_decision, 'create_entity', p_surface, p_normalized_surface, v_entity,
            jsonb_build_object('alias_surfaces', to_jsonb(p_alias_surfaces),
                               'manual_aliases', to_jsonb(p_manual_aliases),
                               'linked_claims', v_linked),
            p_idempotency_key);
    RETURN jsonb_build_object('decision_id', v_decision, 'entity_id', v_entity,
                              'linked_claims', v_linked,
                              'idempotent_replay', false);
END;
$$;
