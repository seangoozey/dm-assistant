CREATE FUNCTION correct_canonical_claim(
    requested_claim_id uuid,
    corrected_assertion text,
    correction_reason text,
    requested_idempotency_key text
) RETURNS TABLE (
    receipt_id uuid,
    change_set_id uuid,
    original_claim_id uuid,
    replacement_claim_id uuid,
    idempotent_replay boolean
)
LANGUAGE plpgsql AS $$
DECLARE
    original claims%ROWTYPE;
    condition claim_conditions%ROWTYPE;
    now_at timestamptz := clock_timestamp();
    workflow_id uuid := gen_random_uuid();
    proposal_id uuid := gen_random_uuid();
    version_id uuid := gen_random_uuid();
    item_id uuid := gen_random_uuid();
    approval_id uuid := gen_random_uuid();
    created_change_set_id uuid := gen_random_uuid();
    created_receipt_id uuid := gen_random_uuid();
    created_replacement_id uuid := gen_random_uuid();
    after_payload jsonb;
    before_payload jsonb;
    version_hash text;
    replay_record record;
BEGIN
    SELECT r.id AS replay_receipt_id, cs.id AS replay_change_set_id,
           (r.decision_json->>'original_claim_id')::uuid AS replay_original_claim_id,
           (r.decision_json->>'replacement_claim_id')::uuid AS replay_replacement_claim_id
      INTO replay_record
      FROM change_sets cs JOIN receipts r ON r.change_set_id = cs.id
     WHERE cs.idempotency_key = requested_idempotency_key;
    IF FOUND THEN
        RETURN QUERY SELECT replay_record.replay_receipt_id, replay_record.replay_change_set_id,
            replay_record.replay_original_claim_id, replay_record.replay_replacement_claim_id, true;
        RETURN;
    END IF;

    IF length(trim(corrected_assertion)) = 0 OR length(trim(correction_reason)) = 0 THEN
        RAISE EXCEPTION USING ERRCODE='P0001', MESSAGE='claim correction requires assertion and reason';
    END IF;
    SELECT * INTO original FROM claims WHERE id=requested_claim_id FOR UPDATE;
    IF NOT FOUND THEN RAISE EXCEPTION USING ERRCODE='P0001', MESSAGE='claim no longer exists'; END IF;
    IF EXISTS (SELECT 1 FROM claim_supersessions WHERE superseded_claim_id=requested_claim_id) THEN
        RAISE EXCEPTION USING ERRCODE='P0001', MESSAGE='only a current claim can be corrected';
    END IF;
    IF trim(original.assertion_text) = trim(corrected_assertion) THEN
        RAISE EXCEPTION USING ERRCODE='P0001', MESSAGE='claim correction does not change the assertion';
    END IF;
    SELECT * INTO condition FROM claim_conditions WHERE claim_id=requested_claim_id;
    before_payload := to_jsonb(original);
    after_payload := jsonb_build_object(
        'id', created_replacement_id, 'original_claim_id', requested_claim_id,
        'assertion_text', trim(corrected_assertion), 'reason', trim(correction_reason)
    );
    IF condition.claim_id IS NOT NULL THEN
        after_payload := after_payload || jsonb_build_object(
            'condition_text', condition.trigger_text,
            'condition_reference_type', condition.reference_type,
            'condition_reference_id', condition.reference_id
        );
    END IF;
    version_hash := encode(digest(convert_to(after_payload::text, 'UTF8'), 'sha256'), 'hex');

    INSERT INTO workflow_sessions(id,kind,started_at,closed_at) VALUES(workflow_id,'lore_entry',now_at,now_at);
    INSERT INTO proposals(id,workflow_session_id,status,created_at,closed_at) VALUES(proposal_id,workflow_id,'applied',now_at,now_at);
    INSERT INTO proposal_versions(id,proposal_id,version_number,content_hash,created_at) VALUES(version_id,proposal_id,1,version_hash,now_at);
    INSERT INTO proposal_items(id,proposal_version_id,sequence,mutation_kind,target_type,target_id,before_json,after_json)
        VALUES(item_id,version_id,1,'correct_claim','claim',created_replacement_id,before_payload,after_payload);
    INSERT INTO approvals(id,proposal_version_id,scope_json,approved_at) VALUES(approval_id,version_id,jsonb_build_array(item_id),now_at);
    INSERT INTO change_sets(id,idempotency_key,workflow_session_id,proposal_version_id,status,requested_at,applied_at,approval_id)
        VALUES(created_change_set_id,requested_idempotency_key,workflow_id,version_id,'applied',now_at,now_at,approval_id);

    INSERT INTO claims (
        id,subject_entity_id,predicate,object_entity_id,assertion_text,state,authority,
        confidence,visibility,is_conditional,predicts_subject_action,recorded_at,session_id,
        created_at,updated_at,effective_from_year,effective_from_month,effective_from_day,
        effective_until_year,effective_until_month,effective_until_day,expected_year,
        expected_month,expected_day,observed_year,observed_month,observed_day,campaign_calendar_id)
    SELECT created_replacement_id,subject_entity_id,predicate,object_entity_id,trim(corrected_assertion),
        state,authority,confidence,visibility,is_conditional,predicts_subject_action,now_at,workflow_id,
        now_at,now_at,effective_from_year,effective_from_month,effective_from_day,effective_until_year,
        effective_until_month,effective_until_day,expected_year,expected_month,expected_day,
        observed_year,observed_month,observed_day,campaign_calendar_id
      FROM claims WHERE id=requested_claim_id;
    INSERT INTO claim_evidence(claim_id,source_span_id,evidence_role)
        SELECT created_replacement_id,source_span_id,evidence_role FROM claim_evidence WHERE claim_id=requested_claim_id;
    INSERT INTO claim_supersessions(superseding_claim_id,superseded_claim_id,resolution_change_set_id,reason)
        VALUES(created_replacement_id,requested_claim_id,created_change_set_id,trim(correction_reason));
    after_payload := after_payload || jsonb_build_object('replacement_claim_id',created_replacement_id);
    INSERT INTO change_set_items(id,change_set_id,proposal_item_id,outcome,before_json,after_json)
        VALUES(gen_random_uuid(),created_change_set_id,item_id,'applied',before_payload,after_payload);
    INSERT INTO receipts(id,change_set_id,decision_json,conflict_json,outcome,issued_at)
        VALUES(created_receipt_id,created_change_set_id,after_payload,'{}','applied',now_at);

    RETURN QUERY SELECT created_receipt_id,created_change_set_id,requested_claim_id,created_replacement_id,false;
END;
$$;
