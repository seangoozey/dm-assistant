-- TKT-0035: AI-extracted claim dimensions for non-canonical candidates.
-- Candidates carry deterministic section text and path-derived classification. This table
-- adds the AI extraction enrichment: proposed subject, predicate, object, state, authority,
-- confidence, and the supporting excerpt — all marked as AI-extracted provenance so the
-- human reviewer sees them as proposals, not fact. The candidate itself is unchanged.
-- Extraction output is never canonical; promotion remains the existing human proposal path.

CREATE TABLE candidate_extractions (
    id uuid PRIMARY KEY,
    candidate_id uuid NOT NULL REFERENCES import_candidates(id),
    subject text NOT NULL CHECK (length(trim(subject)) > 0),
    predicate text NOT NULL CHECK (length(trim(predicate)) > 0),
    object_entity text CHECK (object_entity IS NULL OR length(trim(object_entity)) > 0),
    assertion_text text NOT NULL CHECK (length(trim(assertion_text)) > 0),
    supporting_excerpt text NOT NULL CHECK (length(trim(supporting_excerpt)) > 0),
    state text NOT NULL CHECK (state IN ('observed', 'established', 'intended', 'prepared', 'possible')),
    authority text NOT NULL CHECK (authority IN ('real_play', 'explicit_lore', 'npc_intention', 'preparation', 'brainstorm', 'unclassified')),
    visibility text NOT NULL CHECK (visibility IN ('dm_only', 'party', 'character')),
    confidence numeric(5, 4) NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    extractor_version text NOT NULL CHECK (length(trim(extractor_version)) > 0),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (candidate_id, subject, predicate, assertion_text)
);

CREATE INDEX candidate_extractions_candidate_id_idx ON candidate_extractions (candidate_id);

CREATE TRIGGER candidate_extractions_immutable
    BEFORE UPDATE OR DELETE ON candidate_extractions
    FOR EACH ROW EXECUTE FUNCTION reject_immutable_row_mutation();
