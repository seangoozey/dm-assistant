-- TKT-0106: misspellings are their own decision. A surface like "Corefera"
-- (a typo of "Coreferra") resolves searches and links claims through an
-- entity_aliases row, but alias_kind='misspelling' keeps it out of the
-- Library's "also known as" presentation and makes the correction auditable:
-- it is resolvable, never a name.
ALTER TABLE identity_decisions DROP CONSTRAINT identity_decisions_kind_check;
ALTER TABLE identity_decisions ADD CONSTRAINT identity_decisions_kind_check
    CHECK (kind IN ('create_entity','add_alias','mark_role','dismiss','revert',
                    'mark_misspelling'));
