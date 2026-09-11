CREATE TYPE plan_lifecycle AS ENUM ('active', 'completed', 'failed', 'abandoned', 'superseded');

INSERT INTO kind_definitions (id, namespace, canonical_key, status) VALUES
    ('60000000-0000-0000-0000-000000000001', 'plan', 'campaign_direction', 'active'),
    ('60000000-0000-0000-0000-000000000002', 'plan', 'in_world_plan', 'active'),
    ('60000000-0000-0000-0000-000000000003', 'plan', 'player_plan', 'active');

INSERT INTO kind_versions (
    kind_id, version, label, description, inclusion_rule, exclusions,
    examples, counterexamples, behavior_version
) VALUES
    ('60000000-0000-0000-0000-000000000001', 1, 'Campaign direction',
     'DM-only guidance for campaign development.',
     'Use for pressures, opportunities, themes, or hoped-for arcs the DM may develop.',
     ARRAY['in-world actor intentions', 'statements communicated by players', 'predictions of PC action'],
     ARRAY['Develop pressure around a PC family secret without prescribing the PC response.'],
     ARRAY['The PC will accept the bargain.'], 'campaign-core/1'),
    ('60000000-0000-0000-0000-000000000002', 1, 'In-world plan',
     'A DM-authored intention owned by an NPC or faction.',
     'Use for a plan whose owner is a DM-controlled NPC or faction.',
     ARRAY['campaign-development guidance', 'player statements', 'observed outcomes'],
     ARRAY['A villain intends to end mortality by rerouting the world lifeforce.'],
     ARRAY['The ritual succeeded.'], 'campaign-core/1'),
    ('60000000-0000-0000-0000-000000000003', 1, 'Player plan',
     'A time-bound, attributed, revocable statement communicated by a player.',
     'Use only for what a player explicitly communicated about their PC.',
     ARRAY['true internal intent', 'predictions', 'DM-authored character arcs'],
     ARRAY['A player said their PC planned to seek the lost archive.'],
     ARRAY['The PC will seek the lost archive.'], 'campaign-core/1');

CREATE TABLE plans (
    id uuid PRIMARY KEY REFERENCES records(id),
    plan_kind_id uuid NOT NULL REFERENCES kind_definitions(id),
    canonical_name text NOT NULL CHECK (length(trim(canonical_name)) > 0),
    summary text NOT NULL CHECK (length(trim(summary)) > 0),
    objective text,
    mechanism text,
    intended_outcome text,
    lifecycle plan_lifecycle NOT NULL DEFAULT 'active',
    knowledge_boundary text NOT NULL CHECK (knowledge_boundary IN (
        'dm_direction', 'dm_authored_actor_intention', 'player_communicated_nonbinding'
    )),
    visibility text NOT NULL CHECK (visibility IN ('dm_only', 'party', 'character')),
    owner_record_id uuid REFERENCES records(id),
    player_attribution text,
    communicated_at timestamptz,
    created_by_change_set_id uuid NOT NULL REFERENCES change_sets(id),
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    CHECK (owner_record_id IS NULL OR owner_record_id <> id),
    CHECK (player_attribution IS NULL OR length(trim(player_attribution)) > 0)
);

CREATE TABLE plan_evidence (
    plan_id uuid NOT NULL REFERENCES plans(id),
    source_span_id uuid NOT NULL REFERENCES source_spans(id),
    evidence_role text NOT NULL DEFAULT 'source' CHECK (evidence_role IN ('source', 'support')),
    PRIMARY KEY (plan_id, source_span_id)
);

CREATE TABLE plan_relationships (
    plan_id uuid NOT NULL REFERENCES plans(id),
    related_plan_id uuid NOT NULL REFERENCES plans(id),
    relationship_kind text NOT NULL DEFAULT 'related' CHECK (
        relationship_kind IN ('related', 'advances', 'depends_on', 'supersedes')
    ),
    created_by_change_set_id uuid NOT NULL REFERENCES change_sets(id),
    created_at timestamptz NOT NULL,
    PRIMARY KEY (plan_id, related_plan_id, relationship_kind),
    CHECK (plan_id <> related_plan_id)
);

CREATE TABLE plan_lifecycle_events (
    id uuid PRIMARY KEY,
    plan_id uuid NOT NULL REFERENCES plans(id),
    from_lifecycle plan_lifecycle,
    to_lifecycle plan_lifecycle NOT NULL,
    changed_by_change_set_id uuid NOT NULL REFERENCES change_sets(id),
    changed_at timestamptz NOT NULL,
    CHECK (from_lifecycle IS NULL OR from_lifecycle <> to_lifecycle)
);

CREATE TABLE plan_lifecycle_evidence (
    lifecycle_event_id uuid NOT NULL REFERENCES plan_lifecycle_events(id),
    claim_id uuid NOT NULL REFERENCES claims(id),
    PRIMARY KEY (lifecycle_event_id, claim_id)
);

CREATE FUNCTION enforce_plan_boundary() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    kind_key text;
    owner_kind text;
BEGIN
    SELECT canonical_key INTO kind_key FROM kind_definitions
     WHERE id = NEW.plan_kind_id AND namespace = 'plan' AND status = 'active';
    IF kind_key IS NULL THEN
        RAISE EXCEPTION 'plan kind must reference an active plan kind';
    END IF;
    IF NEW.owner_record_id IS NOT NULL THEN
        SELECT entity_type INTO owner_kind FROM entities WHERE id = NEW.owner_record_id;
    END IF;
    IF kind_key = 'campaign_direction' AND (
        NEW.knowledge_boundary <> 'dm_direction' OR NEW.owner_record_id IS NOT NULL
        OR NEW.player_attribution IS NOT NULL OR NEW.communicated_at IS NOT NULL
    ) THEN
        RAISE EXCEPTION 'campaign direction has no owner or player attribution';
    ELSIF kind_key = 'in_world_plan' AND (
        NEW.knowledge_boundary <> 'dm_authored_actor_intention'
        OR owner_kind NOT IN ('npc', 'faction') OR NEW.player_attribution IS NOT NULL
        OR NEW.communicated_at IS NOT NULL
    ) THEN
        RAISE EXCEPTION 'in-world plan requires an NPC or faction owner';
    ELSIF kind_key = 'player_plan' AND (
        NEW.knowledge_boundary <> 'player_communicated_nonbinding'
        OR owner_kind IS DISTINCT FROM 'pc' OR NEW.player_attribution IS NULL
        OR NEW.communicated_at IS NULL
    ) THEN
        RAISE EXCEPTION 'player plan requires a PC owner, attribution, and communication time';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER plans_enforce_boundary
    BEFORE INSERT OR UPDATE ON plans
    FOR EACH ROW EXECUTE FUNCTION enforce_plan_boundary();

CREATE FUNCTION apply_plan_change_set(
    requested_change_set_id uuid,
    reviewed_version integer,
    requested_approval_id uuid,
    reviewed_content_hash text
) RETURNS jsonb
LANGUAGE plpgsql AS $$
DECLARE
    selected_change_set change_sets%ROWTYPE;
    selected_version proposal_versions%ROWTYPE;
    selected_approval approvals%ROWTYPE;
    selected_proposal proposals%ROWTYPE;
    selected_item proposal_items%ROWTYPE;
    existing_receipt receipts%ROWTYPE;
    target_kind_id uuid;
    current_payload jsonb;
    raw_id text;
    lifecycle_event_id uuid;
    created_receipt_id uuid;
    now_at timestamptz := clock_timestamp();
BEGIN
    SELECT * INTO selected_change_set FROM change_sets
     WHERE id = requested_change_set_id FOR UPDATE;
    IF NOT FOUND OR selected_change_set.proposal_version_id IS NULL THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'change set or proposal version does not exist';
    END IF;
    SELECT * INTO selected_version FROM proposal_versions
     WHERE id = selected_change_set.proposal_version_id FOR UPDATE;
    IF NOT FOUND OR selected_version.version_number <> reviewed_version
       OR selected_version.content_hash <> reviewed_content_hash THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'reviewed proposal version or content hash does not match';
    END IF;
    IF selected_change_set.status = 'applied' THEN
        SELECT * INTO existing_receipt FROM receipts WHERE change_set_id = selected_change_set.id;
        IF NOT FOUND OR existing_receipt.decision_json->>'approval_id' IS DISTINCT FROM requested_approval_id::text THEN
            RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'retry approval does not match the applied receipt';
        END IF;
        RETURN jsonb_build_object('receipt_id', existing_receipt.id, 'change_set_id', existing_receipt.change_set_id,
            'outcome', existing_receipt.outcome, 'applied_item_ids', existing_receipt.decision_json->'applied_item_ids',
            'issued_at', existing_receipt.issued_at, 'idempotent_replay', true);
    END IF;
    SELECT * INTO selected_proposal FROM proposals WHERE id = selected_version.proposal_id FOR UPDATE;
    IF selected_version.version_number <> (SELECT max(version_number) FROM proposal_versions WHERE proposal_id = selected_version.proposal_id) THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'approval references a superseded proposal version';
    END IF;
    SELECT * INTO selected_approval FROM approvals WHERE id = requested_approval_id FOR UPDATE;
    IF NOT FOUND OR selected_approval.proposal_version_id <> selected_version.id OR selected_approval.revoked_at IS NOT NULL THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'approval does not authorize this proposal version';
    END IF;
    IF selected_approval.scope_json <> jsonb_build_array((SELECT id FROM proposal_items WHERE proposal_version_id = selected_version.id)) THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'plan approval must bind the exact single proposal item';
    END IF;
    IF EXISTS (SELECT 1 FROM change_sets WHERE approval_id = selected_approval.id AND id <> selected_change_set.id) THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'approval is already bound to another change set';
    END IF;
    UPDATE change_sets SET approval_id = selected_approval.id WHERE id = selected_change_set.id;
    SELECT * INTO selected_item FROM proposal_items WHERE proposal_version_id = selected_version.id FOR UPDATE;
    IF NOT FOUND OR selected_item.target_type <> 'plan' OR selected_item.target_id IS NULL
       OR selected_item.after_json->>'id' IS DISTINCT FROM selected_item.target_id::text
       OR selected_item.after_json->>'record_type' IS DISTINCT FROM 'plan' THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'plan proposal lacks its exact record coordinates';
    END IF;
    PERFORM pg_advisory_xact_lock(hashtextextended(selected_item.target_id::text, 0));

    IF selected_item.mutation_kind = 'create_plan' THEN
        IF selected_item.before_json IS NOT NULL OR EXISTS (SELECT 1 FROM records WHERE id = selected_item.target_id) THEN
            RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'create plan target already exists';
        END IF;
        SELECT kd.id INTO target_kind_id FROM kind_definitions kd
         JOIN kind_versions kv ON kv.kind_id = kd.id
         WHERE kd.namespace = 'plan' AND kd.canonical_key = selected_item.after_json->>'plan_kind'
           AND kd.status = 'active' AND kv.version = (selected_item.after_json->>'plan_kind_version')::integer;
        IF target_kind_id IS NULL OR selected_item.after_json->>'lifecycle' <> 'active' THEN
            RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'unsupported plan kind, version, or initial lifecycle';
        END IF;
        INSERT INTO records (id, record_type_kind_id, created_by_change_set_id, created_at)
        VALUES (selected_item.target_id, '10000000-0000-0000-0000-000000000002', selected_change_set.id, now_at);
        INSERT INTO plans (
            id, plan_kind_id, canonical_name, summary, objective, mechanism, intended_outcome,
            lifecycle, knowledge_boundary, visibility, owner_record_id, player_attribution,
            communicated_at, created_by_change_set_id, created_at, updated_at
        ) VALUES (
            selected_item.target_id, target_kind_id, selected_item.after_json->>'canonical_name',
            selected_item.after_json->>'summary', selected_item.after_json->>'objective',
            selected_item.after_json->>'mechanism', selected_item.after_json->>'intended_outcome',
            'active', selected_item.after_json->>'knowledge_boundary', selected_item.after_json->>'visibility',
            (selected_item.after_json->>'owner_record_id')::uuid, selected_item.after_json->>'player_attribution',
            (selected_item.after_json->>'communicated_at')::timestamptz, selected_change_set.id, now_at, now_at
        );
        FOR raw_id IN SELECT jsonb_array_elements_text(selected_item.after_json->'evidence_source_span_ids') LOOP
            INSERT INTO plan_evidence (plan_id, source_span_id) VALUES (selected_item.target_id, raw_id::uuid);
        END LOOP;
        IF selected_item.after_json->>'plan_kind' = 'player_plan'
           AND jsonb_array_length(selected_item.after_json->'evidence_source_span_ids') = 0 THEN
            RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'player plan requires source evidence';
        END IF;
        FOR raw_id IN SELECT jsonb_array_elements_text(selected_item.after_json->'related_plan_ids') LOOP
            INSERT INTO plan_relationships (plan_id, related_plan_id, created_by_change_set_id, created_at)
            VALUES (selected_item.target_id, raw_id::uuid, selected_change_set.id, now_at);
        END LOOP;
        lifecycle_event_id := gen_random_uuid();
        INSERT INTO plan_lifecycle_events (id, plan_id, from_lifecycle, to_lifecycle, changed_by_change_set_id, changed_at)
        VALUES (lifecycle_event_id, selected_item.target_id, NULL, 'active', selected_change_set.id, now_at);
    ELSIF selected_item.mutation_kind = 'transition_plan' THEN
        SELECT jsonb_build_object(
            'id', p.id, 'record_type', 'plan', 'plan_kind', kd.canonical_key,
            'plan_kind_version', (SELECT max(version) FROM kind_versions WHERE kind_id = kd.id),
            'canonical_name', p.canonical_name, 'summary', p.summary, 'objective', p.objective,
            'mechanism', p.mechanism, 'intended_outcome', p.intended_outcome,
            'lifecycle', p.lifecycle, 'knowledge_boundary', p.knowledge_boundary,
            'visibility', p.visibility, 'owner_record_id', p.owner_record_id,
            'owner_kind', owner.entity_type, 'owner_name', owner.canonical_name,
            'player_attribution', p.player_attribution, 'communicated_at', p.communicated_at,
            'evidence_source_span_ids', (SELECT coalesce(jsonb_agg(source_span_id ORDER BY source_span_id), '[]') FROM plan_evidence WHERE plan_id = p.id),
            'related_plan_ids', (SELECT coalesce(jsonb_agg(related_plan_id ORDER BY related_plan_id), '[]') FROM plan_relationships WHERE plan_id = p.id),
            'supporting_claim_ids', (SELECT coalesce(jsonb_agg(ple.claim_id ORDER BY ple.claim_id) FILTER (WHERE ple.claim_id IS NOT NULL), '[]') FROM plan_lifecycle_events event LEFT JOIN plan_lifecycle_evidence ple ON ple.lifecycle_event_id = event.id WHERE event.plan_id = p.id AND event.to_lifecycle = p.lifecycle)
        ) INTO current_payload FROM plans p JOIN kind_definitions kd ON kd.id = p.plan_kind_id
          LEFT JOIN entities owner ON owner.id = p.owner_record_id WHERE p.id = selected_item.target_id FOR UPDATE OF p;
        IF current_payload IS NULL OR current_payload IS DISTINCT FROM selected_item.before_json THEN
            RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'plan changed after the proposal was created';
        END IF;
        IF (selected_item.after_json - 'lifecycle' - 'supporting_claim_ids') IS DISTINCT FROM
           (selected_item.before_json - 'lifecycle' - 'supporting_claim_ids') THEN
            RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'lifecycle proposal changes unrelated plan fields';
        END IF;
        IF selected_item.after_json->>'lifecycle' NOT IN ('active', 'completed', 'failed', 'abandoned', 'superseded')
           OR selected_item.after_json->>'lifecycle' = selected_item.before_json->>'lifecycle' THEN
            RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'invalid plan lifecycle transition';
        END IF;
        IF selected_item.after_json->>'lifecycle' IN ('completed', 'failed')
           AND (jsonb_array_length(selected_item.after_json->'supporting_claim_ids') = 0 OR EXISTS (
               SELECT 1 FROM jsonb_array_elements_text(selected_item.after_json->'supporting_claim_ids') ids(value)
               LEFT JOIN claims c ON c.id = ids.value::uuid AND c.state = 'observed' WHERE c.id IS NULL
           )) THEN
            RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'completion or failure requires separate observed claims';
        END IF;
        lifecycle_event_id := gen_random_uuid();
        INSERT INTO plan_lifecycle_events (id, plan_id, from_lifecycle, to_lifecycle, changed_by_change_set_id, changed_at)
        VALUES (lifecycle_event_id, selected_item.target_id, (selected_item.before_json->>'lifecycle')::plan_lifecycle,
                (selected_item.after_json->>'lifecycle')::plan_lifecycle, selected_change_set.id, now_at);
        FOR raw_id IN SELECT jsonb_array_elements_text(selected_item.after_json->'supporting_claim_ids') LOOP
            INSERT INTO plan_lifecycle_evidence (lifecycle_event_id, claim_id) VALUES (lifecycle_event_id, raw_id::uuid);
        END LOOP;
        UPDATE plans SET lifecycle = (selected_item.after_json->>'lifecycle')::plan_lifecycle, updated_at = now_at
         WHERE id = selected_item.target_id;
    ELSE
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'unsupported plan mutation';
    END IF;

    INSERT INTO change_set_items (id, change_set_id, proposal_item_id, outcome, before_json, after_json)
    VALUES (gen_random_uuid(), selected_change_set.id, selected_item.id, 'applied', selected_item.before_json, selected_item.after_json);
    created_receipt_id := gen_random_uuid();
    INSERT INTO receipts (id, change_set_id, decision_json, conflict_json, outcome, issued_at)
    VALUES (created_receipt_id, selected_change_set.id,
        jsonb_build_object('proposal_version_id', selected_version.id, 'reviewed_version', reviewed_version,
            'content_hash', reviewed_content_hash, 'approval_id', selected_approval.id,
            'applied_item_ids', jsonb_build_array(selected_item.id)), '{}'::jsonb, 'applied', now_at);
    UPDATE change_sets SET status = 'applied', applied_at = now_at WHERE id = selected_change_set.id;
    UPDATE proposals SET status = 'applied', closed_at = now_at WHERE id = selected_proposal.id;
    RETURN jsonb_build_object('receipt_id', created_receipt_id, 'change_set_id', selected_change_set.id,
        'outcome', 'applied', 'applied_item_ids', jsonb_build_array(selected_item.id),
        'issued_at', now_at, 'idempotent_replay', false);
END;
$$;

CREATE OR REPLACE FUNCTION apply_campaign_change_set(
    requested_change_set_id uuid,
    reviewed_version integer,
    requested_approval_id uuid,
    reviewed_content_hash text
) RETURNS jsonb
LANGUAGE plpgsql AS $$
DECLARE
    metadata_count integer;
    plan_count integer;
    other_count integer;
BEGIN
    SELECT count(*) FILTER (WHERE pi.mutation_kind = 'update_entity_metadata'),
           count(*) FILTER (WHERE pi.mutation_kind IN ('create_plan', 'transition_plan')),
           count(*) FILTER (WHERE pi.mutation_kind NOT IN ('update_entity_metadata', 'create_plan', 'transition_plan'))
      INTO metadata_count, plan_count, other_count
      FROM change_sets cs JOIN proposal_items pi ON pi.proposal_version_id = cs.proposal_version_id
     WHERE cs.id = requested_change_set_id;
    IF (metadata_count > 0)::integer + (plan_count > 0)::integer + (other_count > 0)::integer > 1 THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'plan, entity metadata, and other mutations cannot be mixed';
    END IF;
    IF metadata_count > 0 THEN
        RETURN apply_entity_metadata_change_set(requested_change_set_id, reviewed_version, requested_approval_id, reviewed_content_hash);
    ELSIF plan_count > 0 THEN
        RETURN apply_plan_change_set(requested_change_set_id, reviewed_version, requested_approval_id, reviewed_content_hash);
    END IF;
    RETURN apply_change_set(requested_change_set_id, reviewed_version, requested_approval_id, reviewed_content_hash);
END;
$$;

CREATE TRIGGER plan_lifecycle_events_immutable
    BEFORE UPDATE OR DELETE ON plan_lifecycle_events
    FOR EACH ROW EXECUTE FUNCTION reject_immutable_row_mutation();
CREATE TRIGGER plan_lifecycle_evidence_immutable
    BEFORE UPDATE OR DELETE ON plan_lifecycle_evidence
    FOR EACH ROW EXECUTE FUNCTION reject_immutable_row_mutation();
