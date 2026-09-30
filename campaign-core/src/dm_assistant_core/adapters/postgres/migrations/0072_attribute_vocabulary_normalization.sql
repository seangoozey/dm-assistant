-- TKT-0140 data fix (Sean's ruling 2026-09-24): poll all attribute values —
-- create the obvious missing vocabulary entries, normalize every value to its
-- canonical (active) form case-insensitively, and normalize the
-- automation-minted attribute claims to match. Existing vocabulary style is
-- lowercase; the new values follow it.

-- 1. Create the missing vocabulary values (receipted, the 0129 pattern).
INSERT INTO vocabulary_receipts (receipt_id, vocabulary, action, value, changed_at)
SELECT gen_random_uuid(), v.vocabulary, 'add', v.value, now()
FROM (VALUES
    ('race', 'dwarf'), ('race', 'human'), ('race', 'gnome'),
    ('race', 'half-elf'), ('race', 'high elf'),
    ('sex', 'male'), ('sex', 'female'), ('sex', 'unspecified'),
    ('status', 'active'), ('status', 'dead'), ('status', 'disbanded'),
    ('location_type', 'region')
) AS v(vocabulary, value)
WHERE NOT EXISTS (SELECT 1 FROM template_vocabularies t
                  WHERE t.vocabulary = v.vocabulary AND t.value = v.value);

INSERT INTO template_vocabularies (vocabulary, value, retired, receipt_id, updated_at)
SELECT r.vocabulary, r.value, false, r.receipt_id, r.changed_at
FROM vocabulary_receipts r
WHERE r.action = 'add'
  AND r.receipt_id NOT IN (SELECT receipt_id FROM template_vocabularies)
  AND (r.vocabulary, r.value) IN (VALUES
    ('race', 'dwarf'), ('race', 'human'), ('race', 'gnome'),
    ('race', 'half-elf'), ('race', 'high elf'),
    ('sex', 'male'), ('sex', 'female'), ('sex', 'unspecified'),
    ('status', 'active'), ('status', 'dead'), ('status', 'disbanded'),
    ('location_type', 'region'))
ON CONFLICT DO NOTHING;

-- 2a. Repair type corruption left by an earlier form of this migration,
--     which rebuilt profile_json through jsonb_each_text and flattened
--     non-string values (aliases arrays, life_status_since objects) to text.
UPDATE entity_profiles ep
SET profile_json = jsonb_set(ep.profile_json, '{aliases}',
        to_jsonb((ep.profile_json->>'aliases')::jsonb))
WHERE jsonb_typeof(ep.profile_json->'aliases') = 'string'
  AND left(ep.profile_json->>'aliases', 1) = '[';

UPDATE entity_profiles ep
SET profile_json = jsonb_set(ep.profile_json, '{life_status_since}',
        to_jsonb((ep.profile_json->>'life_status_since')::jsonb))
WHERE jsonb_typeof(ep.profile_json->'life_status_since') = 'string'
  AND left(ep.profile_json->>'life_status_since', 1) = '{';

-- 2b. Normalize vocabulary attribute values to canonical form
--     (case-insensitive), rewriting ONLY the four string keys — never
--     rebuilding the object, so JSON types survive.
DO $$
DECLARE
    k text;
BEGIN
    FOREACH k IN ARRAY ARRAY['status', 'location_type', 'race', 'sex'] LOOP
        UPDATE entity_profiles ep
        SET profile_json = jsonb_set(ep.profile_json, ARRAY[k], to_jsonb(t.value)),
            updated_at = now()
        FROM template_vocabularies t
        WHERE t.retired = false
          AND t.vocabulary = k
          AND jsonb_typeof(ep.profile_json->k) = 'string'
          AND lower(t.value) = lower(ep.profile_json->>k)
          AND ep.profile_json->>k <> t.value
          AND ep.version = (SELECT MAX(version) FROM entity_profiles p2
                             WHERE p2.entity_id = ep.entity_id);
    END LOOP;
END $$;

-- 3. Normalize the automation-minted attribute claims to the same canonical
--    values (assertion "field: value" → canonical casing). Provenance and
--    evidence untouched — casing normalization of automation output, not a
--    content correction.
UPDATE claims c
SET assertion_text = b.field_name || ': ' || t.value, updated_at = now()
FROM attribute_claim_bindings b, template_vocabularies t
WHERE c.id = b.claim_id
  AND t.retired = false
  AND t.vocabulary = b.field_name
  AND c.assertion_text ~ ('^[a-z_]+: ')
  AND lower(t.value) = lower(regexp_replace(c.assertion_text, '^[a-z_]+: ', ''))
  AND c.assertion_text <> b.field_name || ': ' || t.value;
