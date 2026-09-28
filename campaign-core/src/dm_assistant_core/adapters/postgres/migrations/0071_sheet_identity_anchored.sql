-- TKT-0147 Slice 1: sheet identity migrates onto the record as ANCHORED
-- attribute claims — evidence spans point into the sheet text itself, so
-- these claims are born anchored (unlike the 0070 backfill's nudged ones).
-- PCProfile stops being the identity source; the per-document store becomes
-- read-only legacy.
DO $$
DECLARE
    v_doc uuid;
    v_entity uuid;
    v_content text;
    v_claim uuid;
    v_span uuid;
    v_field text;
    v_value text;
    v_at int;
    v_line text;
BEGIN
    FOR v_doc, v_entity, v_content IN
        SELECT d.id, e.id, convert_from(sr.raw_content, 'UTF8')
        FROM source_document_paths p
        JOIN source_documents d ON d.id = p.source_document_id
        JOIN source_revisions sr ON sr.source_document_id = d.id
        JOIN entities e ON lower(e.canonical_name) = lower(
            regexp_replace(split_part(p.normalized_path, '/', 2), '\.md$', ''))
        WHERE p.is_current
          AND p.normalized_path ~ '^(npcs|pcs)/'
          AND (sr.frontmatter_json->>'type') IN ('npc', 'pc')
          AND sr.id = (SELECT sr2.id FROM source_revisions sr2
                       WHERE sr2.source_document_id = d.id
                       ORDER BY sr2.captured_at DESC LIMIT 1)
    LOOP
        FOREACH v_field IN ARRAY ARRAY['race', 'sex', 'status', 'player']
        LOOP
            -- Sheet fields render as "- **Race:** Half-Elf" or "Race: Half-Elf".
            v_line := NULL;
            v_at := NULL;
            FOR v_line IN
                SELECT line FROM unnest(string_to_array(v_content, chr(10))) AS line
                WHERE lower(line) ~ ('^\s*-?\s*\*\*' || v_field || '\*\*:\s*')
                    OR lower(line) ~ ('^\s*-?\s*' || v_field || ':\s*')
                LIMIT 1
            LOOP
                v_at := position(lower(v_line) in lower(v_content)) - 1;
                EXIT WHEN v_at >= 0;
            END LOOP;
            CONTINUE WHEN v_at IS NULL OR v_at < 0;
            v_value := btrim(regexp_replace(regexp_replace(v_line,
                '^\s*-?\s*\*\*' || v_field || '\*\*:\s*', '', 'i'),
                '^\s*-?\s*' || v_field || ':\s*', '', 'i'));
            CONTINUE WHEN v_value = '' OR v_value IS NULL;
            -- Skip when a binding already holds this field (0070 backfill).
            CONTINUE WHEN EXISTS (SELECT 1 FROM attribute_claim_bindings b
                WHERE b.entity_id = v_entity AND b.field_name = v_field);
            v_claim := gen_random_uuid();
            v_span := gen_random_uuid();
            INSERT INTO source_spans (id, source_revision_id, section_path,
                start_offset, end_offset, excerpt_hash)
            VALUES (v_span,
                (SELECT sr3.id FROM source_revisions sr3 WHERE sr3.source_document_id = v_doc
                 ORDER BY sr3.captured_at DESC LIMIT 1),
                'Sheet', v_at, v_at + length(v_line),
                encode(sha256(convert_to(v_line, 'UTF8')), 'hex'));
            INSERT INTO claims (id, subject_entity_id, predicate, assertion_text,
                state, authority, confidence, visibility, is_conditional,
                predicts_subject_action, recorded_at, created_at, updated_at)
            VALUES (v_claim, v_entity, v_field, v_field || ': ' || v_value,
                'established', 'explicit_lore', 1.0, 'dm_only', false, false,
                now(), now(), now());
            INSERT INTO claim_evidence (claim_id, source_span_id, evidence_role)
            VALUES (v_claim, v_span, 'support');
            INSERT INTO attribute_claim_bindings (entity_id, field_name, claim_id, created_at)
            VALUES (v_entity, v_field, v_claim, now())
            ON CONFLICT (entity_id, field_name) DO NOTHING;
        END LOOP;
    END LOOP;
END $$;
