CREATE TABLE kind_evolution_events (
    id uuid PRIMARY KEY,
    operation text NOT NULL CHECK (
        operation IN ('add', 'rename', 'deprecate', 'replace', 'merge', 'split')
    ),
    reason text NOT NULL CHECK (length(trim(reason)) > 0),
    migration_version text NOT NULL CHECK (length(trim(migration_version)) > 0),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE kind_evolution_members (
    event_id uuid NOT NULL REFERENCES kind_evolution_events(id),
    kind_id uuid NOT NULL REFERENCES kind_definitions(id),
    role text NOT NULL CHECK (role IN ('source', 'target')),
    PRIMARY KEY (event_id, kind_id, role)
);

CREATE TRIGGER kind_evolution_events_immutable
    BEFORE UPDATE OR DELETE ON kind_evolution_events
    FOR EACH ROW EXECUTE FUNCTION reject_immutable_row_mutation();

CREATE TRIGGER kind_evolution_members_immutable
    BEFORE UPDATE OR DELETE ON kind_evolution_members
    FOR EACH ROW EXECUTE FUNCTION reject_immutable_row_mutation();

CREATE FUNCTION apply_entity_metadata_change_set(
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
    current_metadata jsonb;
    target_kind_id uuid;
    target_kind_version integer;
    created_receipt_id uuid;
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
        SELECT * INTO existing_receipt FROM receipts
         WHERE change_set_id = selected_change_set.id;
        IF NOT FOUND
           OR existing_receipt.decision_json->>'approval_id'
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

    SELECT * INTO selected_proposal FROM proposals
     WHERE id = selected_version.proposal_id FOR UPDATE;
    IF selected_version.version_number <> (
        SELECT max(version_number) FROM proposal_versions
         WHERE proposal_id = selected_version.proposal_id
    ) THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001',
            MESSAGE = 'approval references a superseded proposal version';
    END IF;

    SELECT * INTO selected_approval FROM approvals
     WHERE id = requested_approval_id FOR UPDATE;
    IF NOT FOUND
       OR selected_approval.proposal_version_id <> selected_version.id
       OR selected_approval.revoked_at IS NOT NULL
       OR selected_change_set.approval_id IS DISTINCT FROM selected_approval.id THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001',
            MESSAGE = 'approval does not authorize this proposal version';
    END IF;
    IF selected_change_set.status <> 'pending' THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'change set is not pending';
    END IF;

    IF jsonb_array_length(selected_approval.scope_json) <> 1 THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001',
            MESSAGE = 'entity metadata approval must contain exactly one item';
    END IF;
    SELECT * INTO selected_item FROM proposal_items
     WHERE proposal_version_id = selected_version.id
       AND id = (selected_approval.scope_json->>0)::uuid
       AND mutation_kind = 'update_entity_metadata'
       AND target_type = 'entity'
     FOR UPDATE;
    IF NOT FOUND OR selected_item.target_id IS NULL THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001',
            MESSAGE = 'approval does not select one entity metadata item';
    END IF;

    PERFORM pg_advisory_xact_lock(hashtextextended(selected_item.target_id::text, 0));
    IF selected_item.before_json IS NULL
       OR selected_item.after_json->>'id' IS DISTINCT FROM selected_item.target_id::text
       OR selected_item.after_json->>'record_type' IS DISTINCT FROM 'entity'
       OR selected_item.after_json->>'entity_kind'
          IS DISTINCT FROM selected_item.after_json->>'entity_type'
       OR jsonb_typeof(selected_item.after_json->'tags') <> 'array' THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001',
            MESSAGE = 'entity metadata proposal lacks exact before/after coordinates';
    END IF;

    SELECT kd.id, max(kv.version)
      INTO target_kind_id, target_kind_version
      FROM kind_definitions kd
      JOIN kind_versions kv ON kv.kind_id = kd.id
     WHERE kd.namespace = 'entity'
       AND kd.canonical_key = selected_item.after_json->>'entity_kind'
       AND kd.status = 'active'
     GROUP BY kd.id;
    IF target_kind_id IS NULL
       OR target_kind_version IS DISTINCT FROM
          (selected_item.after_json->>'entity_kind_version')::integer THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001',
            MESSAGE = 'entity metadata proposal references an inactive or stale kind version';
    END IF;

    SELECT jsonb_build_object(
        'id', e.id::text,
        'record_type', 'entity',
        'entity_kind', coalesce(kd.canonical_key, e.entity_type),
        'entity_kind_version', (
            SELECT max(version) FROM kind_versions WHERE kind_id = kd.id
        ),
        'entity_type', coalesce(kd.canonical_key, e.entity_type),
        'canonical_name', e.canonical_name,
        'tags', to_jsonb(ARRAY(
            SELECT normalized_name FROM current_entity_tags
             WHERE entity_id = e.id ORDER BY normalized_name
        ))
    ) INTO current_metadata
    FROM entities e
    LEFT JOIN kind_definitions kd ON kd.id = e.entity_kind_id
    WHERE e.id = selected_item.target_id
    FOR UPDATE OF e;
    IF current_metadata IS NULL THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'entity does not exist';
    END IF;
    IF current_metadata IS DISTINCT FROM selected_item.before_json THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001',
            MESSAGE = 'entity metadata changed after the proposal was reviewed';
    END IF;
    IF selected_item.after_json->>'canonical_name'
       IS DISTINCT FROM current_metadata->>'canonical_name' THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001',
            MESSAGE = 'metadata proposal cannot rename the entity';
    END IF;

    UPDATE entities
       SET entity_type = selected_item.after_json->>'entity_kind', updated_at = now_at
     WHERE id = selected_item.target_id;
    UPDATE entity_tag_assignments
       SET removed_by_change_set_id = selected_change_set.id, removed_at = now_at
     WHERE entity_id = selected_item.target_id AND removed_at IS NULL;

    INSERT INTO change_set_items (
        id, change_set_id, proposal_item_id, outcome, before_json, after_json
    ) VALUES (
        gen_random_uuid(), selected_change_set.id, selected_item.id, 'applied',
        selected_item.before_json, selected_item.after_json
    );

    created_receipt_id := gen_random_uuid();
    INSERT INTO receipts (
        id, change_set_id, decision_json, conflict_json, outcome, issued_at
    ) VALUES (
        created_receipt_id, selected_change_set.id,
        jsonb_build_object(
            'proposal_version_id', selected_version.id,
            'reviewed_version', reviewed_version,
            'content_hash', reviewed_content_hash,
            'approval_id', selected_approval.id,
            'applied_item_ids', jsonb_build_array(selected_item.id)
        ),
        '{}'::jsonb, 'applied', now_at
    );
    UPDATE change_sets SET status = 'applied', applied_at = now_at
     WHERE id = selected_change_set.id;
    UPDATE proposals SET status = 'applied', closed_at = now_at
     WHERE id = selected_proposal.id;

    RETURN jsonb_build_object(
        'receipt_id', created_receipt_id,
        'change_set_id', selected_change_set.id,
        'outcome', 'applied',
        'applied_item_ids', jsonb_build_array(selected_item.id),
        'issued_at', now_at,
        'idempotent_replay', false
    );
END;
$$;

CREATE FUNCTION apply_campaign_change_set(
    requested_change_set_id uuid,
    reviewed_version integer,
    requested_approval_id uuid,
    reviewed_content_hash text
) RETURNS jsonb
LANGUAGE plpgsql
AS $$
DECLARE
    metadata_count integer;
    other_count integer;
BEGIN
    SELECT count(*) FILTER (WHERE pi.mutation_kind = 'update_entity_metadata'),
           count(*) FILTER (WHERE pi.mutation_kind <> 'update_entity_metadata')
      INTO metadata_count, other_count
      FROM change_sets cs
      JOIN proposal_items pi ON pi.proposal_version_id = cs.proposal_version_id
     WHERE cs.id = requested_change_set_id;
    IF metadata_count > 0 AND other_count > 0 THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001',
            MESSAGE = 'entity metadata mutations cannot be mixed with other mutation kinds';
    END IF;
    IF metadata_count > 0 THEN
        RETURN apply_entity_metadata_change_set(
            requested_change_set_id, reviewed_version,
            requested_approval_id, reviewed_content_hash
        );
    END IF;
    RETURN apply_change_set(
        requested_change_set_id, reviewed_version,
        requested_approval_id, reviewed_content_hash
    );
END;
$$;
