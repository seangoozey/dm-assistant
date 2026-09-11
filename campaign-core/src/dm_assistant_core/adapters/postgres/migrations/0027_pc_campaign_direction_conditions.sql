-- PC-directed campaign development is non-predictive, but it is not inherently conditional.
CREATE OR REPLACE FUNCTION enforce_pc_agency() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    subject_type text;
BEGIN
    SELECT entity_type INTO subject_type FROM entities WHERE id = NEW.subject_entity_id;
    IF subject_type = 'pc' AND NEW.predicts_subject_action THEN
        RAISE EXCEPTION 'future PC actions cannot be predicted or prescribed';
    END IF;
    IF subject_type = 'pc'
       AND NEW.authority IN ('preparation', 'brainstorm')
       AND (
           NEW.state NOT IN ('prepared', 'possible')
           OR NEW.visibility <> 'dm_only'
       ) THEN
        RAISE EXCEPTION 'PC campaign direction must remain non-canonical DM-only planning';
    END IF;
    RETURN NEW;
END;
$$;

