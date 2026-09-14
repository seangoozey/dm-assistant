-- TKT-0106: undo as an audited decision. A revert references the receipt it
-- reverses; both stay in history (brainstorm-rejection semantics: reversing
-- an effect never removes its audit trail). v1 supports add_alias reverts:
-- the alias row is removed and the entity's derived claim links are
-- reconciled against its remaining names — links still justified by the
-- canonical name or a surviving alias are kept.
ALTER TABLE identity_decisions DROP CONSTRAINT identity_decisions_kind_check;
ALTER TABLE identity_decisions ADD CONSTRAINT identity_decisions_kind_check
    CHECK (kind IN ('create_entity','add_alias','mark_role','dismiss','revert'));
