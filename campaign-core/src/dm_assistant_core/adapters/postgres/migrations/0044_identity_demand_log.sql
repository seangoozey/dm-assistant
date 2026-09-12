-- Retrieval-demand telemetry for the identity review queue (TKT-0106 Phase 2).
-- Derived, best-effort, and rebuildable: it records how often real lookups
-- reached for a name that resolves to nothing, so the queue ranks by measured
-- demand rather than raw text frequency. Never campaign truth.
CREATE TABLE identity_demand_log (
    normalized_surface text PRIMARY KEY,
    surface text NOT NULL,
    source text NOT NULL,
    occurrences integer NOT NULL CHECK (occurrences > 0),
    first_seen timestamptz NOT NULL DEFAULT now(),
    last_seen timestamptz NOT NULL DEFAULT now()
);
