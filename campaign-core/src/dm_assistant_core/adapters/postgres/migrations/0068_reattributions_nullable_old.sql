-- Step 1 (TKT-0140): initial attributions record a NULL old owner — the
-- audit trail says "no previous owner," not a fake one.
ALTER TABLE claim_reattributions ALTER COLUMN old_entity_id DROP NOT NULL;
