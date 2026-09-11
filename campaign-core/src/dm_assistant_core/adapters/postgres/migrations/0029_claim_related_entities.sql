-- Entity mentions are provenance-backed associations, not inferred claim roles.
CREATE TABLE claim_related_entities (
    claim_id uuid NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    entity_id uuid NOT NULL REFERENCES entities(id) ON DELETE RESTRICT,
    relation_kind text NOT NULL DEFAULT 'mentioned' CHECK (relation_kind = 'mentioned'),
    PRIMARY KEY (claim_id, entity_id, relation_kind)
);

CREATE INDEX claim_related_entities_entity_idx
    ON claim_related_entities(entity_id, claim_id);

CREATE FUNCTION attach_claim_related_entities() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO claim_related_entities(claim_id, entity_id, relation_kind)
    SELECT NEW.id, related.entity_id::uuid, 'mentioned'
    FROM change_set_items item
    CROSS JOIN LATERAL jsonb_array_elements_text(
        coalesce(item.after_json->'related_entity_ids', '[]'::jsonb)
    ) AS related(entity_id)
    WHERE item.target_id = NEW.id
      AND item.mutation_kind = 'create_claim'
    ON CONFLICT DO NOTHING;
    RETURN NEW;
END;
$$;

CREATE TRIGGER claims_attach_related_entities
AFTER INSERT ON claims
FOR EACH ROW EXECUTE FUNCTION attach_claim_related_entities();
