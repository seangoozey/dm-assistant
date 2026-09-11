CREATE TYPE kind_lifecycle_status AS ENUM ('active', 'deprecated', 'retired');

CREATE TABLE kind_definitions (
    id uuid PRIMARY KEY,
    namespace text NOT NULL CHECK (
        namespace IN ('record', 'entity', 'plan', 'artifact', 'rules')
    ),
    canonical_key text NOT NULL CHECK (canonical_key ~ '^[a-z][a-z0-9_]*$'),
    status kind_lifecycle_status NOT NULL DEFAULT 'active',
    replacement_kind_id uuid REFERENCES kind_definitions(id),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (namespace, canonical_key),
    CHECK (replacement_kind_id IS NULL OR replacement_kind_id <> id)
);

CREATE TABLE kind_versions (
    kind_id uuid NOT NULL REFERENCES kind_definitions(id),
    version integer NOT NULL CHECK (version > 0),
    label text NOT NULL CHECK (length(trim(label)) > 0),
    description text NOT NULL CHECK (length(trim(description)) > 0),
    inclusion_rule text NOT NULL,
    exclusions text[] NOT NULL DEFAULT '{}',
    examples text[] NOT NULL DEFAULT '{}',
    counterexamples text[] NOT NULL DEFAULT '{}',
    behavior_version text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (kind_id, version)
);

CREATE TABLE kind_aliases (
    namespace text NOT NULL,
    alias_key text NOT NULL CHECK (alias_key ~ '^[a-z][a-z0-9_]*$'),
    kind_id uuid NOT NULL REFERENCES kind_definitions(id),
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (namespace, alias_key)
);

INSERT INTO kind_definitions (id, namespace, canonical_key, status) VALUES
    ('10000000-0000-0000-0000-000000000001', 'record', 'entity', 'active'),
    ('10000000-0000-0000-0000-000000000002', 'record', 'plan', 'active'),
    ('10000000-0000-0000-0000-000000000003', 'record', 'artifact', 'active'),
    ('10000000-0000-0000-0000-000000000004', 'record', 'encounter', 'active'),
    ('10000000-0000-0000-0000-000000000005', 'record', 'session', 'active'),
    ('20000000-0000-0000-0000-000000000001', 'entity', 'npc', 'active'),
    ('20000000-0000-0000-0000-000000000002', 'entity', 'pc', 'active'),
    ('20000000-0000-0000-0000-000000000003', 'entity', 'location', 'active'),
    ('20000000-0000-0000-0000-000000000004', 'entity', 'faction', 'active'),
    ('20000000-0000-0000-0000-000000000005', 'entity', 'item', 'active'),
    ('20000000-0000-0000-0000-000000000006', 'entity', 'event', 'active'),
    ('20000000-0000-0000-0000-000000000007', 'entity', 'worldbuilding', 'active'),
    ('20000000-0000-0000-0000-000000000008', 'entity', 'rules_element', 'active'),
    ('30000000-0000-0000-0000-000000000001', 'rules', 'spell', 'active'),
    ('30000000-0000-0000-0000-000000000002', 'rules', 'feat', 'active'),
    ('30000000-0000-0000-0000-000000000003', 'rules', 'ability', 'active'),
    ('40000000-0000-0000-0000-000000000001', 'artifact', 'read_aloud', 'active'),
    ('40000000-0000-0000-0000-000000000002', 'artifact', 'transcript', 'active'),
    ('40000000-0000-0000-0000-000000000003', 'artifact', 'foundry_export', 'active'),
    ('40000000-0000-0000-0000-000000000004', 'artifact', 'markdown_export', 'active'),
    ('40000000-0000-0000-0000-000000000005', 'artifact', 'retrieval_index', 'active'),
    ('40000000-0000-0000-0000-000000000006', 'artifact', 'other', 'deprecated');

INSERT INTO kind_versions (
    kind_id, version, label, description, inclusion_rule, exclusions,
    examples, counterexamples, behavior_version
)
SELECT id, 1, initcap(replace(canonical_key, '_', ' ')),
       CASE namespace
           WHEN 'record' THEN 'A stable referenceable record family.'
           WHEN 'entity' THEN 'A controlled primary entity classification.'
           WHEN 'rules' THEN 'A controlled reusable rules-element subtype.'
           ELSE 'A controlled derived-artifact classification.'
       END,
       'Use only when the record satisfies the documented family and kind boundary.',
       ARRAY[]::text[], ARRAY[]::text[], ARRAY[]::text[], 'campaign-core/1'
FROM kind_definitions;

UPDATE kind_versions kv
SET label = details.label,
    description = details.description,
    inclusion_rule = details.inclusion_rule,
    exclusions = details.exclusions,
    examples = details.examples,
    counterexamples = details.counterexamples
FROM kind_definitions kd
JOIN (VALUES
    ('npc', 'NPC', 'A DM-controlled character.',
     'Use for a character whose actions are authored by the DM.',
     ARRAY['player-controlled characters']::text[], ARRAY['a deity NPC']::text[],
     ARRAY['a player character']::text[]),
    ('pc', 'PC', 'A character controlled only by its player.',
     'Use for a player character whose future choices cannot be predicted by the system.',
     ARRAY['DM-controlled characters']::text[], ARRAY['an active player character']::text[],
     ARRAY['a recurring allied NPC']::text[]),
    ('location', 'Location', 'A place at any geographic scale.',
     'Use for a place that needs stable identity and cross-document reference.',
     ARRAY['organizations', 'historical occurrences']::text[],
     ARRAY['a settlement', 'a continent']::text[], ARRAY['a ruling council']::text[]),
    ('faction', 'Faction', 'An organized group with shared identity.',
     'Use for an organization, institution, or coordinated group.',
     ARRAY['places', 'unorganized populations']::text[], ARRAY['a political council']::text[],
     ARRAY['a country as geography']::text[]),
    ('item', 'Item', 'An in-world object with canonical identity.',
     'Use for the object itself, independent of any generated sheet or export.',
     ARRAY['deliverables', 'source handouts']::text[], ARRAY['a named relic']::text[],
     ARRAY['a Foundry export package']::text[]),
    ('event', 'Event', 'A distinct historical, mythical, or cosmological occurrence.',
     'Use for an occurrence with stable identity, even when its exact date is unknown.',
     ARRAY['eras', 'plans', 'abstract concepts']::text[], ARRAY['a legendary war']::text[],
     ARRAY['an age of history']::text[]),
    ('worldbuilding', 'Worldbuilding',
     'An era, legend, cosmological structure, or abstract setting concept.',
     'Use for stable setting subjects not represented by another entity kind.',
     ARRAY['plans', 'sources', 'sessions', 'unsupported fallback values']::text[],
     ARRAY['a cosmological law', 'a named era']::text[], ARRAY['a villain scheme']::text[]),
    ('rules_element', 'Rules element', 'A reusable spell, feat, or ability.',
     'Use for a canonical reusable game mechanic; structured mechanics follow in TKT-0032.',
     ARRAY['items', 'exports', 'character sheets']::text[], ARRAY['a custom spell']::text[],
     ARRAY['a printable spell card']::text[])
) AS details(
    canonical_key, label, description, inclusion_rule, exclusions, examples, counterexamples
) ON details.canonical_key = kd.canonical_key
WHERE kv.kind_id = kd.id AND kd.namespace = 'entity' AND kv.version = 1;

CREATE TABLE records (
    id uuid PRIMARY KEY,
    record_type_kind_id uuid NOT NULL REFERENCES kind_definitions(id),
    created_by_change_set_id uuid REFERENCES change_sets(id),
    created_at timestamptz NOT NULL,
    CHECK (id IS NOT NULL)
);

CREATE FUNCTION enforce_record_type_kind() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM kind_definitions kd
        WHERE kd.id = NEW.record_type_kind_id
          AND kd.namespace = 'record'
          AND kd.status = 'active'
    ) THEN
        RAISE EXCEPTION 'record type must reference an active record kind';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER records_controlled_type
    BEFORE INSERT OR UPDATE OF record_type_kind_id ON records
    FOR EACH ROW EXECUTE FUNCTION enforce_record_type_kind();

INSERT INTO records (id, record_type_kind_id, created_by_change_set_id, created_at)
SELECT e.id, '10000000-0000-0000-0000-000000000001',
       e.created_by_change_set_id, e.created_at
FROM entities e;

INSERT INTO records (id, record_type_kind_id, created_at)
SELECT a.id, '10000000-0000-0000-0000-000000000003', a.created_at
FROM derived_artifacts a;

ALTER TABLE entities
    ADD COLUMN entity_kind_id uuid REFERENCES kind_definitions(id);

UPDATE entities e
   SET entity_kind_id = kd.id
  FROM kind_definitions kd
 WHERE kd.namespace = 'entity'
   AND kd.status = 'active'
   AND kd.canonical_key = e.entity_type;

ALTER TABLE entities
    ADD CONSTRAINT entities_record_id_fk FOREIGN KEY (id) REFERENCES records(id);

ALTER TABLE derived_artifacts
    ADD CONSTRAINT derived_artifacts_record_id_fk FOREIGN KEY (id) REFERENCES records(id);

ALTER TABLE claims
    ADD CONSTRAINT claims_subject_record_id_fk
        FOREIGN KEY (subject_entity_id) REFERENCES records(id),
    ADD CONSTRAINT claims_object_record_id_fk
        FOREIGN KEY (object_entity_id) REFERENCES records(id);

ALTER TABLE relationships
    ADD CONSTRAINT relationships_from_record_id_fk
        FOREIGN KEY (from_entity_id) REFERENCES records(id),
    ADD CONSTRAINT relationships_to_record_id_fk
        FOREIGN KEY (to_entity_id) REFERENCES records(id);

INSERT INTO review_items (
    id, kind, status, subject_type, subject_id, details,
    opened_by_change_set_id, created_at, updated_at
)
SELECT gen_random_uuid(), 'unsupported_legacy_entity_kind', 'open', 'entity', e.id,
       jsonb_build_object(
           'legacy_entity_type', e.entity_type,
           'reason', 'Existing free-text entity type requires explicit reclassification'
       ),
       e.created_by_change_set_id, now(), now()
FROM entities e
WHERE e.entity_kind_id IS NULL;

CREATE FUNCTION enforce_entity_kind_and_record() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    resolved_kind_id uuid;
BEGIN
    SELECT kd.id INTO resolved_kind_id
      FROM kind_definitions kd
     WHERE kd.namespace = 'entity'
       AND kd.canonical_key = NEW.entity_type
       AND kd.status = 'active';
    IF resolved_kind_id IS NULL THEN
        RAISE EXCEPTION 'unsupported entity kind: %', NEW.entity_type;
    END IF;
    IF TG_OP = 'INSERT'
       AND NEW.entity_kind_id IS NOT NULL
       AND NEW.entity_kind_id <> resolved_kind_id THEN
        RAISE EXCEPTION 'entity kind ID does not match its versioned key';
    END IF;
    IF TG_OP = 'UPDATE'
       AND NEW.entity_kind_id IS DISTINCT FROM OLD.entity_kind_id
       AND NEW.entity_kind_id <> resolved_kind_id THEN
        RAISE EXCEPTION 'entity kind ID does not match its versioned key';
    END IF;
    IF TG_OP = 'UPDATE'
       AND OLD.entity_type IN ('pc', 'npc')
       AND NEW.entity_type <> OLD.entity_type THEN
        RAISE EXCEPTION 'PC and NPC agency kinds cannot be reclassified';
    END IF;
    NEW.entity_kind_id := resolved_kind_id;
    IF TG_OP = 'INSERT' THEN
        INSERT INTO records (
            id, record_type_kind_id, created_by_change_set_id, created_at
        ) VALUES (
            NEW.id, '10000000-0000-0000-0000-000000000001',
            NEW.created_by_change_set_id, NEW.created_at
        );
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER entities_controlled_kind
    BEFORE INSERT OR UPDATE OF entity_type, entity_kind_id ON entities
    FOR EACH ROW EXECUTE FUNCTION enforce_entity_kind_and_record();

CREATE FUNCTION register_artifact_record() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.kind = 'other' THEN
        RAISE EXCEPTION 'artifact kind other is deprecated and cannot be used for new artifacts';
    END IF;
    INSERT INTO records (id, record_type_kind_id, created_at)
    VALUES (NEW.id, '10000000-0000-0000-0000-000000000003', NEW.created_at);
    RETURN NEW;
END;
$$;

CREATE TRIGGER derived_artifacts_register_record
    BEFORE INSERT ON derived_artifacts
    FOR EACH ROW EXECUTE FUNCTION register_artifact_record();

CREATE TABLE tags (
    id uuid PRIMARY KEY,
    name text NOT NULL CHECK (length(trim(name)) BETWEEN 1 AND 64),
    normalized_name text NOT NULL CHECK (normalized_name = lower(trim(normalized_name))),
    created_by_change_set_id uuid REFERENCES change_sets(id),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (normalized_name)
);

CREATE TABLE entity_tag_assignments (
    id uuid PRIMARY KEY,
    entity_id uuid NOT NULL REFERENCES entities(id),
    tag_id uuid NOT NULL REFERENCES tags(id),
    assigned_by_change_set_id uuid NOT NULL REFERENCES change_sets(id),
    assigned_at timestamptz NOT NULL,
    removed_by_change_set_id uuid REFERENCES change_sets(id),
    removed_at timestamptz,
    CHECK ((removed_by_change_set_id IS NULL) = (removed_at IS NULL)),
    CHECK (removed_at IS NULL OR removed_at >= assigned_at)
);

CREATE UNIQUE INDEX entity_tag_assignments_active_uq
    ON entity_tag_assignments (entity_id, tag_id)
    WHERE removed_at IS NULL;

INSERT INTO tags (id, name, normalized_name) VALUES
    ('50000000-0000-0000-0000-000000000001', 'history', 'history'),
    ('50000000-0000-0000-0000-000000000002', 'mythology', 'mythology'),
    ('50000000-0000-0000-0000-000000000003', 'cosmology', 'cosmology'),
    ('50000000-0000-0000-0000-000000000004', 'world', 'world'),
    ('50000000-0000-0000-0000-000000000005', 'continent', 'continent'),
    ('50000000-0000-0000-0000-000000000006', 'country', 'country'),
    ('50000000-0000-0000-0000-000000000007', 'region', 'region'),
    ('50000000-0000-0000-0000-000000000008', 'settlement', 'settlement'),
    ('50000000-0000-0000-0000-000000000009', 'monster', 'monster'),
    ('50000000-0000-0000-0000-000000000010', 'deity', 'deity'),
    ('50000000-0000-0000-0000-000000000011', 'religion', 'religion'),
    ('50000000-0000-0000-0000-000000000012', 'political', 'political');

CREATE VIEW current_entity_tags AS
SELECT eta.entity_id, t.id AS tag_id, t.name, t.normalized_name
FROM entity_tag_assignments eta
JOIN tags t ON t.id = eta.tag_id
WHERE eta.removed_at IS NULL;

CREATE FUNCTION apply_created_entity_tags() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    raw_tag text;
    normalized_tag text;
    selected_tag_id uuid;
BEGIN
    IF NOT (NEW.after_json ? 'entity_type') THEN
        RETURN NEW;
    END IF;
    IF NEW.after_json->>'record_type' IS DISTINCT FROM 'entity'
       OR NEW.after_json->>'entity_kind' IS DISTINCT FROM NEW.after_json->>'entity_type'
       OR coalesce((NEW.after_json->>'entity_kind_version')::integer, 0) <> 1 THEN
        RAISE EXCEPTION 'entity proposal lacks exact record and kind coordinates';
    END IF;
    IF NOT (NEW.after_json ? 'tags') THEN
        RAISE EXCEPTION 'entity proposal lacks exact tag state';
    END IF;
    IF jsonb_typeof(NEW.after_json->'tags') <> 'array' THEN
        RAISE EXCEPTION 'entity tags must be an array';
    END IF;
    FOR raw_tag IN SELECT jsonb_array_elements_text(NEW.after_json->'tags')
    LOOP
        normalized_tag := lower(trim(regexp_replace(raw_tag, '\s+', ' ', 'g')));
        IF length(normalized_tag) NOT BETWEEN 1 AND 64 THEN
            RAISE EXCEPTION 'tag must contain between 1 and 64 characters';
        END IF;
        INSERT INTO tags (
            id, name, normalized_name, created_by_change_set_id, created_at
        ) VALUES (
            gen_random_uuid(), normalized_tag, normalized_tag, NEW.change_set_id, now()
        ) ON CONFLICT (normalized_name) DO NOTHING;
        SELECT id INTO selected_tag_id FROM tags WHERE normalized_name = normalized_tag;
        INSERT INTO entity_tag_assignments (
            id, entity_id, tag_id, assigned_by_change_set_id, assigned_at
        ) VALUES (
            gen_random_uuid(), (NEW.after_json->>'id')::uuid, selected_tag_id,
            NEW.change_set_id, now()
        );
    END LOOP;
    RETURN NEW;
END;
$$;

CREATE TRIGGER change_set_items_apply_entity_tags
    AFTER INSERT ON change_set_items
    FOR EACH ROW EXECUTE FUNCTION apply_created_entity_tags();

CREATE TRIGGER kind_versions_immutable
    BEFORE UPDATE OR DELETE ON kind_versions
    FOR EACH ROW EXECUTE FUNCTION reject_immutable_row_mutation();

CREATE TRIGGER kind_aliases_immutable
    BEFORE UPDATE OR DELETE ON kind_aliases
    FOR EACH ROW EXECUTE FUNCTION reject_immutable_row_mutation();
