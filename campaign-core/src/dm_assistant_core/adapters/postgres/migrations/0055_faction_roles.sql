-- TKT-0108: faction-scoped role catalog with unique leadership seats.
-- Roles are titles held within one faction (Inquisitor, Grand Inquisitor),
-- never identities and never aliases. is_leadership carries both meanings:
-- unique holder within the faction and the UI legend star. A role row can
-- outlive its holder — a vacant seat survives member removal for succession.
CREATE TABLE faction_roles (
    id uuid PRIMARY KEY,
    faction_id uuid NOT NULL REFERENCES entities(id),
    name text NOT NULL,
    is_leadership boolean NOT NULL DEFAULT false,
    created_by_decision_id uuid REFERENCES identity_decisions(id),
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX faction_roles_faction_name_idx
    ON faction_roles (faction_id, lower(name));
CREATE INDEX faction_roles_faction_idx ON faction_roles (faction_id);

CREATE FUNCTION apply_role_decision(
    p_faction_id uuid,
    p_member_id uuid,
    p_role_name text,
    p_role_is_leadership boolean,
    p_source_claim_id uuid,
    p_idempotency_key text
) RETURNS jsonb
LANGUAGE plpgsql AS $$
DECLARE
    v_decision uuid := gen_random_uuid();
    v_faction record;
    v_member record;
    v_prior record;
    v_role record;
    v_holder record;
    v_role_name text;
    v_action text;
    v_is_leadership boolean;
    v_role_exists boolean := false;
BEGIN
    SELECT id, canonical_name, entity_type INTO v_faction FROM entities WHERE id = p_faction_id;
    IF NOT FOUND OR v_faction.entity_type <> 'faction' THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'role decisions require a faction target';
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
    IF NOT FOUND THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001',
            MESSAGE = v_member.canonical_name || ' is not on the roster of ' || v_faction.canonical_name;
    END IF;

    v_role_name := nullif(regexp_replace(btrim(coalesce(p_role_name, '')), '\s+', ' ', 'g'), '');
    IF v_role_name IS NULL THEN
        -- Clearing a role keeps the membership; only the seat is vacated.
        IF v_prior.role_title IS NULL THEN
            RAISE EXCEPTION USING ERRCODE = 'P0001',
                MESSAGE = v_member.canonical_name || ' holds no role in ' || v_faction.canonical_name;
        END IF;
        v_action := 'clear_role';
        v_is_leadership := false;
    ELSE
        SELECT * INTO v_role FROM faction_roles
         WHERE faction_id = p_faction_id AND lower(name) = lower(v_role_name);
        v_role_exists := FOUND;
        IF NOT FOUND THEN
            -- Define-on-assign: the leadership flag is honored only here, so a
            -- later assignment can never silently flip a role's definition.
            v_is_leadership := coalesce(p_role_is_leadership, false);
        ELSE
            v_role_name := v_role.name;
            v_is_leadership := v_role.is_leadership;
            IF v_is_leadership THEN
                -- A leadership seat refuses a second holder by name; succession
                -- is two explicit decisions, never a silent transfer.
                SELECT me.canonical_name INTO v_holder
                 FROM membership_records mr
                 JOIN entities me ON me.id = mr.member_id
                 WHERE mr.faction_id = p_faction_id AND mr.role_title = v_role.name
                   AND mr.superseded_by IS NULL AND mr.member_id <> p_member_id
                 LIMIT 1;
                IF FOUND THEN
                    RAISE EXCEPTION USING ERRCODE = 'P0001',
                        MESSAGE = v_role.name || ' is the unique leadership seat of '
                                  || v_faction.canonical_name || ' and is currently held by '
                                  || v_holder.canonical_name || '; change or clear their role first';
                END IF;
            END IF;
            IF v_prior.role_title IS NOT DISTINCT FROM v_role.name THEN
                RAISE EXCEPTION USING ERRCODE = 'P0001',
                    MESSAGE = v_member.canonical_name || ' already holds ' || v_role.name
                              || ' in ' || v_faction.canonical_name;
            END IF;
        END IF;
        v_action := 'assign_role';
    END IF;

    INSERT INTO identity_decisions (id, kind, surface, normalized_surface, entity_id, details, idempotency_key)
    VALUES (v_decision, 'membership',
            v_member.canonical_name || ' in ' || v_faction.canonical_name,
            lower(v_member.canonical_name || ' in ' || v_faction.canonical_name),
            p_faction_id,
            jsonb_build_object(
                'action', v_action,
                'faction_id', p_faction_id, 'member_id', p_member_id,
                'member_name', v_member.canonical_name,
                'faction_name', v_faction.canonical_name,
                'role_name', CASE WHEN v_action = 'assign_role' THEN v_role_name END,
                'prior_role_title', v_prior.role_title,
                'is_leadership', v_is_leadership,
                'source_claim_id', p_source_claim_id),
            p_idempotency_key);

    IF v_action = 'assign_role' AND NOT v_role_exists THEN
        INSERT INTO faction_roles (id, faction_id, name, is_leadership, created_by_decision_id)
        VALUES (gen_random_uuid(), p_faction_id, v_role_name, v_is_leadership, v_decision);
    END IF;

    -- Role changes ride the membership supersession chain: the prior row keeps
    -- the old seat in history, the new current row carries the new one.
    UPDATE membership_records SET superseded_by = id WHERE id = v_prior.id;
    INSERT INTO membership_records (id, faction_id, member_id, role_title, source_claim_id, created_by_decision_id)
    VALUES (gen_random_uuid(), p_faction_id, p_member_id,
            CASE WHEN v_action = 'assign_role' THEN v_role_name END,
            p_source_claim_id, v_decision);
    RETURN jsonb_build_object('idempotent_replay', false);
END;
$$;
