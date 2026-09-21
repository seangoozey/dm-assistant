-- TKT-0115 / ADR-0017 CTS amendment: 'considered' joins the claim_state
-- enum as the floor of the Canonical Truth State spectrum — below 'possible'.
-- Considered = "worked through and found a route that precludes it";
-- Possible = "available to happen with no known blockers".
ALTER TYPE claim_state ADD VALUE IF NOT EXISTS 'considered' BEFORE 'possible';
