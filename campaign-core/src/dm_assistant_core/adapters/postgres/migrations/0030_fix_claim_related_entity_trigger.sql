-- Proposal items already contain the immutable confirmed payload when the claim
-- insert fires; change_set_items is populated only afterward.
CREATE OR REPLACE FUNCTION attach_claim_related_entities() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO claim_related_entities(claim_id, entity_id, relation_kind)
    SELECT NEW.id, related.entity_id::uuid, 'mentioned'
    FROM proposal_items item
    CROSS JOIN LATERAL jsonb_array_elements_text(
        coalesce(item.after_json->'related_entity_ids', '[]'::jsonb)
    ) AS related(entity_id)
    WHERE item.target_id = NEW.id
      AND item.mutation_kind = 'create_claim'
    ON CONFLICT DO NOTHING;
    RETURN NEW;
END;
$$;
