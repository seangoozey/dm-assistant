-- TKT-0106: explicit faction membership as a first-class audited record.
-- The derived co-mention Members list is retrieval context, never a roster.
-- membership_records stores the DM's explicit decision: identity, member,
-- optional role title, provenance, supersession (leaving replaces silently).
CREATE TABLE membership_records (
    id uuid PRIMARY KEY,
    faction_id uuid NOT NULL REFERENCES entities(id),
    member_id uuid NOT NULL REFERENCES entities(id),
    role_title text,
    source_claim_id uuid REFERENCES claims(id),
    created_by_decision_id uuid REFERENCES identity_decisions(id),
    superseded_by uuid REFERENCES membership_records(id),
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX membership_records_current_unique
    ON membership_records (faction_id, member_id) WHERE superseded_by IS NULL;
CREATE INDEX membership_records_faction_idx ON membership_records (faction_id) WHERE superseded_by IS NULL;
CREATE INDEX membership_records_member_idx ON membership_records (member_id) WHERE superseded_by IS NULL;

CREATE FUNCTION apply_membership_decision(
    p_faction_id uuid,
    p_member_id uuid,
    p_role_title text,
    p_source_claim_id uuid,
    p_supersede boolean,
    p_idempotency_key text
) RETURNS jsonb
LANGUAGE plpgsql AS $$
DECLARE
    v_id uuid;
    v_prior record;
    v_faction record;
    v_member record;
BEGIN
    SELECT id, canonical_name, entity_type INTO v_faction FROM entities WHERE id = p_faction_id;
    IF NOT FOUND OR v_faction.entity_type <> 'faction' THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'membership requires a faction target';
    END IF;
    SELECT id, canonical_name INTO v_member FROM entities WHERE id = p_member_id;
    IF NOT FOUND THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'no identity matches that member';
    END IF;

    IF EXISTS (SELECT 1 FROM identity_decisions WHERE idempotency_key = p_idempotency_key
               AND kind = 'membership') THEN
        RETURN jsonb_build_object('idempotent_replay', true);
    END IF;

    SELECT * INTO v_prior FROM membership_records
     WHERE faction_id = p_faction_id AND member_id = p_member_id AND superseded_by IS NULL;

    IF p_supersede THEN
        IF NOT FOUND THEN
            RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'no current membership to remove';
        END IF;
        -- Supersession replaces the current row in place: the record keeps its
        -- identity while the superseded flag becomes the removal audit.
        UPDATE membership_records SET superseded_by = id WHERE id = v_prior.id;
    ELSE
        IF FOUND THEN
            RAISE EXCEPTION USING ERRCODE = 'P0001',
                MESSAGE = v_member.canonical_name || ' is already a member of ' || v_faction.canonical_name || '; remove first to change';
        END IF;
        INSERT INTO membership_records (id, faction_id, member_id, role_title, source_claim_id)
        VALUES (gen_random_uuid(), p_faction_id, p_member_id, nullif(p_role_title, ''),
                p_source_claim_id);
    END IF;

    INSERT INTO identity_decisions (id, kind, surface, normalized_surface, entity_id, details, idempotency_key)
    VALUES (gen_random_uuid(), 'membership',
            v_member.canonical_name || ' in ' || v_faction.canonical_name,
            lower(v_member.canonical_name || ' in ' || v_faction.canonical_name),
            p_faction_id,
            jsonb_build_object('faction_id', p_faction_id, 'member_id', p_member_id,
                               'member_name', v_member.canonical_name,
                               'faction_name', v_faction.canonical_name,
                               'role_title', nullif(p_role_title, ''),
                               'action', CASE WHEN p_supersede THEN 'remove' ELSE 'add' END),
            p_idempotency_key);
    RETURN jsonb_build_object('idempotent_replay', false);
END;
$$;

ALTER TABLE identity_decisions DROP CONSTRAINT identity_decisions_kind_check;
ALTER TABLE identity_decisions ADD CONSTRAINT identity_decisions_kind_check
    CHECK (kind IN ('create_entity','add_alias','mark_role','dismiss','revert',
                    'mark_misspelling','reconcile_links','membership'));
