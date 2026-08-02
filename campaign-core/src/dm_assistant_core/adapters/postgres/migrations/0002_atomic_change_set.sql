ALTER TABLE change_sets
    ADD COLUMN approval_id uuid REFERENCES approvals(id);

CREATE UNIQUE INDEX change_sets_approval_id_uq
    ON change_sets (approval_id)
    WHERE approval_id IS NOT NULL;

CREATE FUNCTION apply_change_set(
    requested_change_set_id uuid,
    reviewed_version integer,
    requested_approval_id uuid,
    reviewed_content_hash text
) RETURNS jsonb
LANGUAGE plpgsql
AS $$
DECLARE
    selected_change_set change_sets%ROWTYPE;
    selected_version proposal_versions%ROWTYPE;
    selected_approval approvals%ROWTYPE;
    selected_proposal proposals%ROWTYPE;
    selected_item proposal_items%ROWTYPE;
    existing_receipt receipts%ROWTYPE;
    scope_item_ids uuid[];
    scope_count integer;
    proposal_item_count integer;
    created_receipt_id uuid;
    applied_item_ids jsonb := '[]'::jsonb;
    now_at timestamptz := clock_timestamp();
BEGIN
    SELECT * INTO selected_change_set
      FROM change_sets
     WHERE id = requested_change_set_id
     FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'change set does not exist';
    END IF;

    IF selected_change_set.proposal_version_id IS NULL THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'change set has no proposal version';
    END IF;

    SELECT * INTO selected_version
      FROM proposal_versions
     WHERE id = selected_change_set.proposal_version_id
     FOR UPDATE;
    IF NOT FOUND
       OR selected_version.version_number <> reviewed_version
       OR selected_version.content_hash <> reviewed_content_hash THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001',
            MESSAGE = 'reviewed proposal version or content hash does not match';
    END IF;

    IF selected_change_set.status = 'applied' THEN
        SELECT * INTO existing_receipt
          FROM receipts
         WHERE change_set_id = selected_change_set.id;
        IF NOT FOUND THEN
            RAISE EXCEPTION USING ERRCODE = 'P0001',
                MESSAGE = 'applied change set has no receipt';
        END IF;
        IF existing_receipt.decision_json->>'approval_id'
           IS DISTINCT FROM requested_approval_id::text THEN
            RAISE EXCEPTION USING ERRCODE = 'P0001',
                MESSAGE = 'retry approval does not match the applied receipt';
        END IF;
        RETURN jsonb_build_object(
            'receipt_id', existing_receipt.id,
            'change_set_id', existing_receipt.change_set_id,
            'outcome', existing_receipt.outcome,
            'applied_item_ids', existing_receipt.decision_json->'applied_item_ids',
            'issued_at', existing_receipt.issued_at,
            'idempotent_replay', true
        );
    END IF;

    SELECT * INTO selected_proposal
      FROM proposals
     WHERE id = selected_version.proposal_id
     FOR UPDATE;
    IF selected_version.version_number <> (
        SELECT max(version_number)
          FROM proposal_versions
         WHERE proposal_id = selected_version.proposal_id
    ) THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001',
            MESSAGE = 'approval references a superseded proposal version';
    END IF;

    SELECT * INTO selected_approval
      FROM approvals
     WHERE id = requested_approval_id
     FOR UPDATE;
    IF NOT FOUND
       OR selected_approval.proposal_version_id <> selected_version.id
       OR selected_approval.revoked_at IS NOT NULL THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001',
            MESSAGE = 'approval does not authorize this proposal version';
    END IF;
    IF EXISTS (
        SELECT 1 FROM change_sets
         WHERE approval_id = selected_approval.id
           AND id <> selected_change_set.id
    ) THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001',
            MESSAGE = 'approval is already bound to another change set';
    END IF;
    UPDATE change_sets
       SET approval_id = selected_approval.id
     WHERE id = selected_change_set.id;

    SELECT array_agg(value::uuid), count(*), count(DISTINCT value)
      INTO scope_item_ids, scope_count, proposal_item_count
      FROM jsonb_array_elements_text(selected_approval.scope_json) AS scoped(value);
    IF scope_count IS NULL OR scope_count = 0 THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'approval scope is empty';
    END IF;
    IF scope_count <> proposal_item_count THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001',
            MESSAGE = 'approval scope contains duplicate proposal items';
    END IF;
    SELECT count(*) INTO proposal_item_count
      FROM proposal_items
     WHERE proposal_version_id = selected_version.id
       AND id = ANY(scope_item_ids);
    IF proposal_item_count <> scope_count THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001',
            MESSAGE = 'approval scope contains an item from another proposal version';
    END IF;

    IF selected_change_set.status <> 'pending' THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001',
            MESSAGE = 'change set is not pending or applied';
    END IF;

    PERFORM 1
      FROM proposal_items
     WHERE id = ANY(scope_item_ids)
     ORDER BY sequence
     FOR UPDATE;

    FOR selected_item IN
        SELECT *
          FROM proposal_items
         WHERE id = ANY(scope_item_ids)
         ORDER BY sequence
    LOOP
        IF selected_item.target_id IS NULL THEN
            RAISE EXCEPTION USING ERRCODE = 'P0001',
                MESSAGE = 'canonical mutation target ID is required';
        END IF;
        PERFORM pg_advisory_xact_lock(hashtextextended(selected_item.target_id::text, 0));

        IF selected_item.mutation_kind = 'create_entity'
           AND selected_item.target_type = 'entity' THEN
            IF selected_item.before_json IS NOT NULL
               OR selected_item.after_json->>'id' IS DISTINCT FROM selected_item.target_id::text THEN
                RAISE EXCEPTION USING ERRCODE = 'P0001',
                    MESSAGE = 'create_entity payload does not match its immutable target';
            END IF;
            INSERT INTO entities (
                id, entity_type, canonical_name, created_by_change_set_id, created_at, updated_at
            ) VALUES (
                selected_item.target_id,
                selected_item.after_json->>'entity_type',
                selected_item.after_json->>'canonical_name',
                selected_change_set.id,
                now_at,
                now_at
            );
        ELSIF selected_item.mutation_kind = 'create_claim'
              AND selected_item.target_type = 'claim' THEN
            IF selected_item.before_json IS NOT NULL
               OR selected_item.after_json->>'id' IS DISTINCT FROM selected_item.target_id::text
               OR selected_item.after_json->>'source_span_id' IS NULL THEN
                RAISE EXCEPTION USING ERRCODE = 'P0001',
                    MESSAGE = 'create_claim payload lacks its immutable target or evidence';
            END IF;
            PERFORM 1 FROM entities
             WHERE id IN (
                 (selected_item.after_json->>'subject_entity_id')::uuid,
                 (selected_item.after_json->>'object_entity_id')::uuid
             )
             FOR UPDATE;
            PERFORM 1 FROM source_spans
             WHERE id = (selected_item.after_json->>'source_span_id')::uuid
             FOR UPDATE;
            INSERT INTO claims (
                id, subject_entity_id, predicate, object_entity_id, assertion_text,
                state, authority, confidence, visibility, is_conditional,
                predicts_subject_action, recorded_at, effective_from, effective_until,
                expected_at, observed_at, time_precision, session_id, created_at, updated_at
            ) VALUES (
                selected_item.target_id,
                (selected_item.after_json->>'subject_entity_id')::uuid,
                selected_item.after_json->>'predicate',
                (selected_item.after_json->>'object_entity_id')::uuid,
                selected_item.after_json->>'assertion_text',
                (selected_item.after_json->>'state')::claim_state,
                (selected_item.after_json->>'authority')::authority_kind,
                (selected_item.after_json->>'confidence')::numeric,
                selected_item.after_json->>'visibility',
                coalesce((selected_item.after_json->>'is_conditional')::boolean, false),
                coalesce((selected_item.after_json->>'predicts_subject_action')::boolean, false),
                (selected_item.after_json->>'recorded_at')::timestamptz,
                (selected_item.after_json->>'effective_from')::timestamptz,
                (selected_item.after_json->>'effective_until')::timestamptz,
                (selected_item.after_json->>'expected_at')::timestamptz,
                (selected_item.after_json->>'observed_at')::timestamptz,
                selected_item.after_json->>'time_precision',
                (selected_item.after_json->>'session_id')::uuid,
                now_at,
                now_at
            );
            INSERT INTO claim_evidence (claim_id, source_span_id, evidence_role)
            VALUES (
                selected_item.target_id,
                (selected_item.after_json->>'source_span_id')::uuid,
                coalesce(selected_item.after_json->>'evidence_role', 'support')
            );
        ELSE
            RAISE EXCEPTION USING ERRCODE = 'P0001',
                MESSAGE = format(
                    'unsupported canonical mutation %s for %s',
                    selected_item.mutation_kind,
                    selected_item.target_type
                );
        END IF;

        INSERT INTO change_set_items (
            id, change_set_id, proposal_item_id, outcome, before_json, after_json
        ) VALUES (
            gen_random_uuid(), selected_change_set.id, selected_item.id, 'applied',
            selected_item.before_json, selected_item.after_json
        );
        applied_item_ids := applied_item_ids || jsonb_build_array(selected_item.id);
    END LOOP;

    created_receipt_id := gen_random_uuid();
    INSERT INTO receipts (
        id, change_set_id, decision_json, conflict_json, outcome, issued_at
    ) VALUES (
        created_receipt_id,
        selected_change_set.id,
        jsonb_build_object(
            'proposal_version_id', selected_version.id,
            'reviewed_version', reviewed_version,
            'content_hash', reviewed_content_hash,
            'approval_id', selected_approval.id,
            'applied_item_ids', applied_item_ids
        ),
        '{}'::jsonb,
        'applied',
        now_at
    );
    UPDATE change_sets
       SET status = 'applied', applied_at = now_at
     WHERE id = selected_change_set.id;

    SELECT count(*) INTO proposal_item_count
      FROM proposal_items
     WHERE proposal_version_id = selected_version.id;
    IF proposal_item_count = scope_count THEN
        UPDATE proposals
           SET status = 'applied', closed_at = now_at
         WHERE id = selected_proposal.id;
    END IF;

    RETURN jsonb_build_object(
        'receipt_id', created_receipt_id,
        'change_set_id', selected_change_set.id,
        'outcome', 'applied',
        'applied_item_ids', applied_item_ids,
        'issued_at', now_at,
        'idempotent_replay', false
    );
END;
$$;
