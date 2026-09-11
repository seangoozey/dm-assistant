-- TKT-0032: Structured rules elements and derived artifact export profiles.
-- A rules_element entity (from TKT-0029) carries structured mechanics in a dedicated
-- table. A versioned Markdown-card export profile produces a deterministic derived
-- artifact from an approved canonical rules-element record. This migration is additive:
-- it introduces the mechanics table, the rules_card artifact kind, and export-profile
-- registry metadata without touching existing canonical data.

-- The rules_card artifact kind: a deterministic Markdown card generated from a canonical
-- rules-element entity. Distinct from the generic markdown_export kind.
ALTER TYPE artifact_kind ADD VALUE IF NOT EXISTS 'rules_card';

-- Register rules_card in the artifact kind registry.
INSERT INTO kind_definitions (id, namespace, canonical_key, status) VALUES
    ('40000000-0000-0000-0000-000000000007', 'artifact', 'rules_card', 'active')
    ON CONFLICT (namespace, canonical_key) DO NOTHING;

INSERT INTO kind_versions (
    kind_id, version, label, description, inclusion_rule, exclusions,
    examples, counterexamples, behavior_version
) VALUES
    ('40000000-0000-0000-0000-000000000007', 1,
     'Rules card',
     'A deterministic Markdown card generated from a canonical rules-element entity.',
     'Use for a spell, feat, or ability card exported from an approved canonical record.',
     ARRAY['foundry item documents', 'raw source handouts', 'character sheets']::text[],
     ARRAY['a spell card with school, level, and description']::text[],
     ARRAY['a Foundry export package']::text[],
     'campaign-core/1')
    ON CONFLICT (kind_id, version) DO NOTHING;

-- Widen the namespace check so export_profile is an accepted kind namespace. This must
-- run before the export_profile kind definition is inserted.
ALTER TABLE kind_definitions DROP CONSTRAINT kind_definitions_namespace_check;
ALTER TABLE kind_definitions ADD CONSTRAINT kind_definitions_namespace_check
    CHECK (namespace IN ('record', 'entity', 'plan', 'artifact', 'rules', 'export_profile'));

-- Register the export profile as a versioned kind. The profile version is the
-- behavior_version; a later profile version ships as a new kind_versions row.
INSERT INTO kind_definitions (id, namespace, canonical_key, status) VALUES
    ('70000000-0000-0000-0000-000000000001', 'export_profile', 'markdown_card', 'active')
    ON CONFLICT (namespace, canonical_key) DO NOTHING;

INSERT INTO kind_versions (
    kind_id, version, label, description, inclusion_rule, exclusions,
    examples, counterexamples, behavior_version
) VALUES
    ('70000000-0000-0000-0000-000000000001', 1,
     'Markdown card profile',
     'A versioned export profile that renders a canonical rules element as a Markdown card.',
     'Use to export an approved spell, feat, or ability into a deterministic Markdown card.',
     ARRAY['foundry exports', 'non-rules records']::text[],
     ARRAY['a spell rendered as a Markdown card with deterministic formatting']::text[],
     ARRAY['a freeform text dump']::text[],
     'markdown-card/1')
    ON CONFLICT (kind_id, version) DO NOTHING;

-- Structured mechanics for a rules_element entity. The entity is the canonical identity;
-- this table holds the kind-specific structured detail. mechanics_jsonb is validated by
-- application code against the rules_kind; unsupported shapes fail into review.
CREATE TABLE rules_element_mechanics (
    entity_id uuid PRIMARY KEY REFERENCES entities(id),
    rules_kind text NOT NULL CHECK (rules_kind IN ('spell', 'feat', 'ability')),
    summary text NOT NULL CHECK (length(trim(summary)) > 0),
    mechanics_jsonb jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_by_change_set_id uuid NOT NULL REFERENCES change_sets(id),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TRIGGER rules_element_mechanics_immutable_before
    BEFORE DELETE ON rules_element_mechanics
    FOR EACH ROW EXECUTE FUNCTION reject_immutable_row_mutation();

-- Persist rules-element mechanics when a create_entity change-set item is applied.
-- Mirrors apply_created_entity_tags: reads the optional rules_element_mechanics object
-- from the proposal payload and inserts a mechanics row bound to the new entity.
CREATE FUNCTION apply_created_rules_element_mechanics() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    mechanics_obj jsonb;
    rules_kind_value text;
    summary_value text;
    mechanics_jsonb_value jsonb;
    created_entity_id uuid;
BEGIN
    IF NOT (NEW.after_json ? 'entity_type') THEN
        RETURN NEW;
    END IF;
    IF NEW.after_json->>'entity_type' <> 'rules_element' THEN
        RETURN NEW;
    END IF;
    IF NOT (NEW.after_json ? 'rules_element_mechanics') THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001',
            MESSAGE = 'rules_element entity requires rules_element_mechanics';
    END IF;
    mechanics_obj := NEW.after_json->'rules_element_mechanics';
    rules_kind_value := mechanics_obj->>'rules_kind';
    summary_value := mechanics_obj->>'summary';
    mechanics_jsonb_value := mechanics_obj->'mechanics';
    IF rules_kind_value IS NULL OR summary_value IS NULL THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001',
            MESSAGE = 'rules_element_mechanics requires rules_kind and summary';
    END IF;
    IF rules_kind_value NOT IN ('spell', 'feat', 'ability') THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001',
            MESSAGE = 'unsupported rules_kind: ' || rules_kind_value;
    END IF;
    created_entity_id := (NEW.after_json->>'id')::uuid;
    INSERT INTO rules_element_mechanics (
        entity_id, rules_kind, summary, mechanics_jsonb,
        created_by_change_set_id, created_at, updated_at
    ) VALUES (
        created_entity_id, rules_kind_value, summary_value,
        COALESCE(mechanics_jsonb_value, '{}'::jsonb),
        NEW.change_set_id, now(), now()
    );
    RETURN NEW;
END;
$$;

CREATE TRIGGER change_set_items_apply_rules_element_mechanics
    AFTER INSERT ON change_set_items
    FOR EACH ROW WHEN (NEW.after_json->>'entity_type' = 'rules_element')
    EXECUTE FUNCTION apply_created_rules_element_mechanics();

-- Link derived artifacts to the export profile version that produced them. This makes
-- regeneration reproducible: the same canonical record + profile version yields the same
-- content hash.
ALTER TABLE derived_artifacts
    ADD COLUMN export_profile_kind_id uuid REFERENCES kind_definitions(id);

-- Allow artifact_inputs to reference a canonical entity (the source of a rules-card
-- export). The existing check requires exactly one of claim/relationship/source_revision;
-- widen it to include entity_id so a rules-element export names its canonical entity.
DO $$
DECLARE check_constraint_name text;
        unique_constraint_name text;
BEGIN
    SELECT conname INTO check_constraint_name
      FROM pg_constraint
     WHERE conrelid = 'artifact_inputs'::regclass AND contype = 'c'
       AND pg_get_constraintdef(oid) LIKE '%num_nonnulls(claim_id%';
    IF check_constraint_name IS NOT NULL THEN
        EXECUTE format('ALTER TABLE artifact_inputs DROP CONSTRAINT %I', check_constraint_name);
    END IF;

    SELECT conname INTO unique_constraint_name
      FROM pg_constraint
     WHERE conrelid = 'artifact_inputs'::regclass AND contype = 'u';
    IF unique_constraint_name IS NOT NULL THEN
        EXECUTE format('ALTER TABLE artifact_inputs DROP CONSTRAINT %I', unique_constraint_name);
    END IF;
END;
$$;

ALTER TABLE artifact_inputs ADD COLUMN entity_id uuid REFERENCES entities(id);
ALTER TABLE artifact_inputs ADD CONSTRAINT artifact_inputs_one_input
    CHECK (num_nonnulls(claim_id, relationship_id, source_revision_id, entity_id) = 1);
ALTER TABLE artifact_inputs ADD CONSTRAINT artifact_inputs_unique_input
    UNIQUE NULLS NOT DISTINCT (artifact_id, claim_id, relationship_id, source_revision_id, entity_id);
