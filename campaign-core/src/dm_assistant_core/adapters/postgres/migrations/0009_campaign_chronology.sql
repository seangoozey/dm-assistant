-- ADR-0007: Separate real-world audit instants from in-game campaign chronology.
-- Campaign dates become integer-year storage backed by a hardcoded Gregorian calendar
-- spec. Audit instants remain timestamptz. Because zero canonical claims exist at this
-- point in development, the old timestamptz campaign-date columns are dropped in this
-- same forward migration rather than carrying a dual-read phase.

-- The calendar spec makes same-calendar day arithmetic deterministic ("how many days
-- since X"). The current campaign is Gregorian-shaped CE; a variant calendar is a future
-- additive spec plus a new calendar_id, never a rewrite of this data.
CREATE TABLE campaign_calendars (
    calendar_id text PRIMARY KEY,
    era_label text NOT NULL,
    months_in_year smallint NOT NULL CHECK (months_in_year > 0),
    spec_version text NOT NULL,
    leap_rule text NOT NULL,
    description text NOT NULL
);

CREATE TABLE campaign_calendar_months (
    calendar_id text NOT NULL REFERENCES campaign_calendars(calendar_id),
    month_index smallint NOT NULL CHECK (month_index > 0),
    month_name text NOT NULL,
    days_in_month smallint NOT NULL CHECK (days_in_month > 0),
    PRIMARY KEY (calendar_id, month_index)
);

-- The hardcoded Gregorian CE calendar. Leap years follow the standard rule.
INSERT INTO campaign_calendars (calendar_id, era_label, months_in_year, spec_version, leap_rule, description)
VALUES ('gregorian-ce', 'CE', 12, 'gregorian/1', 'standard',
        'Gregorian month and day structure with the CE era label.');

INSERT INTO campaign_calendar_months (calendar_id, month_index, month_name, days_in_month) VALUES
    ('gregorian-ce', 1, 'January', 31),
    ('gregorian-ce', 2, 'February', 28),
    ('gregorian-ce', 3, 'March', 31),
    ('gregorian-ce', 4, 'April', 30),
    ('gregorian-ce', 5, 'May', 31),
    ('gregorian-ce', 6, 'June', 30),
    ('gregorian-ce', 7, 'July', 31),
    ('gregorian-ce', 8, 'August', 31),
    ('gregorian-ce', 9, 'September', 30),
    ('gregorian-ce', 10, 'October', 31),
    ('gregorian-ce', 11, 'November', 30),
    ('gregorian-ce', 12, 'December', 31);

-- Deterministic same-calendar day-ordinal. February is treated as 28 days; the leap
-- day is accounted for when the year is a Gregorian leap year and month > 2. A NULL
-- month or day yields NULL (partial dates are not force-orderable). The result is only
-- meaningful within one calendar_id; cross-calendar subtraction is never valid.
CREATE FUNCTION campaign_day_ordinal(
    p_calendar_id text,
    p_year integer,
    p_month smallint,
    p_day smallint
) RETURNS bigint
LANGUAGE plpgsql AS $$
DECLARE
    months_count smallint;
    ordinal bigint;
    leap_extra smallint := 0;
    month_days smallint;
    cumulative bigint;
    days_in_year smallint;
    leap_days_before bigint := 0;
    end_year integer;
BEGIN
    IF p_month IS NULL OR p_day IS NULL THEN
        RETURN NULL;
    END IF;
    SELECT c.months_in_year INTO months_count
      FROM campaign_calendars c WHERE c.calendar_id = p_calendar_id;
    IF NOT FOUND THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'unknown calendar: ' || p_calendar_id;
    END IF;
    IF p_month < 1 OR p_month > months_count THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'month out of range for calendar';
    END IF;
    SELECT cm.days_in_month INTO month_days
      FROM campaign_calendar_months cm
     WHERE cm.calendar_id = p_calendar_id AND cm.month_index = p_month;
    IF p_day < 1 OR p_day > month_days THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'day out of range for month';
    END IF;

    SELECT COALESCE(sum(prev.days_in_month), 0) INTO cumulative
      FROM campaign_calendar_months prev
     WHERE prev.calendar_id = p_calendar_id AND prev.month_index < p_month;

    SELECT COALESCE(sum(c.days_in_month), 0) INTO days_in_year
      FROM campaign_calendar_months c WHERE c.calendar_id = p_calendar_id;

    -- Gregorian leap contribution: leap days for completed years strictly before p_year,
    -- plus the current year's leap day when past February. Only the gregorian-ce spec
    -- defines leap years; an alternate fixed calendar seeds its own month lengths.
    IF p_calendar_id = 'gregorian-ce' THEN
        IF p_year > 0 THEN
            end_year := p_year - 1;
            leap_days_before := end_year / 4 - end_year / 100 + end_year / 400;
        END IF;
        IF (p_year % 4 = 0 AND (p_year % 100 <> 0 OR p_year % 400 = 0)) AND p_month > 2 THEN
            leap_extra := 1;
        END IF;
    END IF;

    ordinal := p_year::bigint * days_in_year
             + leap_days_before + cumulative + p_day::bigint + leap_extra;
    RETURN ordinal;
END;
$$;

-- Add campaign chronology columns to claims and relationships. All are nullable so
-- undated records remain valid without a placeholder. Each temporal concept from the
-- original schema (effective_from, effective_until, expected_at, observed_at) becomes
-- its own integer triple plus a shared calendar_id.
ALTER TABLE claims
    ADD COLUMN effective_from_year integer,
    ADD COLUMN effective_from_month smallint,
    ADD COLUMN effective_from_day smallint,
    ADD COLUMN effective_until_year integer,
    ADD COLUMN effective_until_month smallint,
    ADD COLUMN effective_until_day smallint,
    ADD COLUMN expected_year integer,
    ADD COLUMN expected_month smallint,
    ADD COLUMN expected_day smallint,
    ADD COLUMN observed_year integer,
    ADD COLUMN observed_month smallint,
    ADD COLUMN observed_day smallint,
    ADD COLUMN campaign_calendar_id text REFERENCES campaign_calendars(calendar_id);

ALTER TABLE relationships
    ADD COLUMN effective_from_year integer,
    ADD COLUMN effective_from_month smallint,
    ADD COLUMN effective_from_day smallint,
    ADD COLUMN effective_until_year integer,
    ADD COLUMN effective_until_month smallint,
    ADD COLUMN effective_until_day smallint,
    ADD COLUMN expected_year integer,
    ADD COLUMN expected_month smallint,
    ADD COLUMN expected_day smallint,
    ADD COLUMN observed_year integer,
    ADD COLUMN observed_month smallint,
    ADD COLUMN observed_day smallint,
    ADD COLUMN campaign_calendar_id text REFERENCES campaign_calendars(calendar_id);

-- Import candidates carry assertion prose, not structured dates, but the calendar
-- identity flows forward when a candidate is promoted. Default it to the campaign's
-- calendar so promoted claims inherit the right calendar_id.
ALTER TABLE import_candidates
    ADD COLUMN campaign_calendar_id text REFERENCES campaign_calendars(calendar_id);

-- Backfill: convert any existing timestamptz campaign dates to their integer-year
-- equivalents before dropping the old columns. The current campaign is Gregorian CE,
-- so extraction is year/month/day. The development database has a small number of
-- canonical claims (the TKT-0024 first promotion); their campaign dates are NULL, but
-- this backfill correctly handles any claim that carried a real in-game date.
UPDATE claims SET
    effective_from_year  = EXTRACT(year  FROM effective_from)::integer,
    effective_from_month = EXTRACT(month FROM effective_from)::smallint,
    effective_from_day   = EXTRACT(day   FROM effective_from)::smallint,
    effective_until_year  = EXTRACT(year  FROM effective_until)::integer,
    effective_until_month = EXTRACT(month FROM effective_until)::smallint,
    effective_until_day   = EXTRACT(day   FROM effective_until)::smallint,
    expected_year  = EXTRACT(year  FROM expected_at)::integer,
    expected_month = EXTRACT(month FROM expected_at)::smallint,
    expected_day   = EXTRACT(day   FROM expected_at)::smallint,
    observed_year  = EXTRACT(year  FROM observed_at)::integer,
    observed_month = EXTRACT(month FROM observed_at)::smallint,
    observed_day   = EXTRACT(day   FROM observed_at)::smallint,
    campaign_calendar_id = COALESCE(campaign_calendar_id, 'gregorian-ce')
    WHERE effective_from IS NOT NULL OR effective_until IS NOT NULL
       OR expected_at IS NOT NULL OR observed_at IS NOT NULL;

UPDATE claims SET campaign_calendar_id = 'gregorian-ce'
    WHERE campaign_calendar_id IS NULL
      AND (effective_from_year IS NOT NULL OR observed_year IS NOT NULL
           OR expected_year IS NOT NULL);

UPDATE relationships SET
    effective_from_year  = EXTRACT(year  FROM effective_from)::integer,
    effective_from_month = EXTRACT(month FROM effective_from)::smallint,
    effective_from_day   = EXTRACT(day   FROM effective_from)::smallint,
    effective_until_year  = EXTRACT(year  FROM effective_until)::integer,
    effective_until_month = EXTRACT(month FROM effective_until)::smallint,
    effective_until_day   = EXTRACT(day   FROM effective_until)::smallint,
    expected_year  = EXTRACT(year  FROM expected_at)::integer,
    expected_month = EXTRACT(month FROM expected_at)::smallint,
    expected_day   = EXTRACT(day   FROM expected_at)::smallint,
    observed_year  = EXTRACT(year  FROM observed_at)::integer,
    observed_month = EXTRACT(month FROM observed_at)::smallint,
    observed_day   = EXTRACT(day   FROM observed_at)::smallint,
    campaign_calendar_id = COALESCE(campaign_calendar_id, 'gregorian-ce')
    WHERE effective_from IS NOT NULL OR effective_until IS NOT NULL
       OR expected_at IS NOT NULL OR observed_at IS NOT NULL;

UPDATE relationships SET campaign_calendar_id = 'gregorian-ce'
    WHERE campaign_calendar_id IS NULL
      AND (effective_from_year IS NOT NULL OR observed_year IS NOT NULL
           OR expected_year IS NOT NULL);

-- Drop the old timestamptz campaign-date columns. Audit columns (recorded_at,
-- created_at, updated_at) and all source/proposal/receipt timestamps are untouched.
ALTER TABLE claims
    DROP COLUMN effective_from,
    DROP COLUMN effective_until,
    DROP COLUMN expected_at,
    DROP COLUMN observed_at,
    DROP COLUMN time_precision;

ALTER TABLE relationships
    DROP COLUMN effective_from,
    DROP COLUMN effective_until,
    DROP COLUMN expected_at,
    DROP COLUMN observed_at,
    DROP COLUMN time_precision;

-- The observed-claim check moves from a timestamptz NOT NULL to a campaign-year check.
-- The effective-range ordering check is expressed on year (a full day-ordinal range
-- check lives in application validation where the calendar spec is available).
ALTER TABLE claims
    DROP CONSTRAINT claims_check,
    ADD CONSTRAINT claims_observed_requires_year
        CHECK (state <> 'observed' OR observed_year IS NOT NULL),
    ADD CONSTRAINT claims_effective_range_order
        CHECK (effective_until_year IS NULL
               OR effective_from_year IS NULL
               OR effective_until_year >= effective_from_year);

ALTER TABLE relationships
    DROP CONSTRAINT relationships_check;

-- Replace the canonical claim-insert function so it reads the integer campaign columns
-- from the proposal payload instead of casting to timestamptz.
CREATE OR REPLACE FUNCTION apply_change_set(
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
                predicts_subject_action, recorded_at,
                effective_from_year, effective_from_month, effective_from_day,
                effective_until_year, effective_until_month, effective_until_day,
                expected_year, expected_month, expected_day,
                observed_year, observed_month, observed_day,
                campaign_calendar_id, session_id, created_at, updated_at
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
                NULLIF(selected_item.after_json->>'effective_from_year', '')::integer,
                NULLIF(selected_item.after_json->>'effective_from_month', '')::smallint,
                NULLIF(selected_item.after_json->>'effective_from_day', '')::smallint,
                NULLIF(selected_item.after_json->>'effective_until_year', '')::integer,
                NULLIF(selected_item.after_json->>'effective_until_month', '')::smallint,
                NULLIF(selected_item.after_json->>'effective_until_day', '')::smallint,
                NULLIF(selected_item.after_json->>'expected_year', '')::integer,
                NULLIF(selected_item.after_json->>'expected_month', '')::smallint,
                NULLIF(selected_item.after_json->>'expected_day', '')::smallint,
                NULLIF(selected_item.after_json->>'observed_year', '')::integer,
                NULLIF(selected_item.after_json->>'observed_month', '')::smallint,
                NULLIF(selected_item.after_json->>'observed_day', '')::smallint,
                NULLIF(selected_item.after_json->>'campaign_calendar_id', '')::text,
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
