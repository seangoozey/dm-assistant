-- Keep canonical claim creation inside the database mutation boundary.
CREATE FUNCTION create_replacement_claim(
    original_claim_id uuid,
    replacement_claim_id uuid,
    replacement jsonb,
    workflow_session_id uuid,
    created_at timestamptz
) RETURNS void
LANGUAGE sql AS $$
    INSERT INTO claims (
        id,subject_entity_id,predicate,object_entity_id,assertion_text,state,authority,
        confidence,visibility,is_conditional,predicts_subject_action,recorded_at,session_id,
        created_at,updated_at,effective_from_year,effective_from_month,effective_from_day,
        effective_until_year,effective_until_month,effective_until_day,expected_year,
        expected_month,expected_day,observed_year,observed_month,observed_day,campaign_calendar_id)
    SELECT replacement_claim_id,subject_entity_id,predicate,object_entity_id,
        trim(replacement->>'assertion_text'),(replacement->>'state')::claim_state,
        (replacement->>'authority')::authority_kind,confidence,replacement->>'visibility',
        coalesce(nullif(replacement->>'condition_text','') IS NOT NULL,false),
        predicts_subject_action,created_at,workflow_session_id,created_at,created_at,
        nullif(replacement#>>'{effective_from,year}','')::integer,
        nullif(replacement#>>'{effective_from,month}','')::smallint,
        nullif(replacement#>>'{effective_from,day}','')::smallint,
        nullif(replacement#>>'{effective_until,year}','')::integer,
        nullif(replacement#>>'{effective_until,month}','')::smallint,
        nullif(replacement#>>'{effective_until,day}','')::smallint,
        nullif(replacement#>>'{expected,year}','')::integer,
        nullif(replacement#>>'{expected,month}','')::smallint,
        nullif(replacement#>>'{expected,day}','')::smallint,
        nullif(replacement#>>'{observed,year}','')::integer,
        nullif(replacement#>>'{observed,month}','')::smallint,
        nullif(replacement#>>'{observed,day}','')::smallint,
        campaign_calendar_id
      FROM claims WHERE id=original_claim_id;
$$;
