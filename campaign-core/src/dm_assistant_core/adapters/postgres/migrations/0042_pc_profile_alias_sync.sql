-- Auditable record of the identity-alias mutations a profile save applied.
-- The profile editor manages its own `profile` namespace in entity_aliases;
-- rows from other surfaces are never touched by profile saves.
ALTER TABLE pc_profile_receipts ADD COLUMN alias_sync jsonb;
