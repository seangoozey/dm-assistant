CREATE TYPE claim_state AS ENUM (
    'observed', 'established', 'intended', 'prepared', 'possible',
    'proposed', 'disputed', 'superseded', 'rejected'
);

CREATE TYPE authority_kind AS ENUM (
    'real_play', 'dm_correction', 'explicit_lore', 'npc_intention',
    'preparation', 'brainstorm', 'unclassified', 'derived'
);

CREATE TYPE workflow_kind AS ENUM (
    'ask', 'brainstorm', 'lore_entry', 'real_play', 'audio_brainstorm',
    'session_debrief', 'encounter_creation'
);

CREATE TYPE proposal_status AS ENUM (
    'draft', 'pending', 'approved', 'applied', 'rejected', 'superseded'
);

CREATE TYPE change_set_status AS ENUM ('pending', 'applying', 'applied', 'failed');

CREATE TYPE artifact_kind AS ENUM (
    'read_aloud', 'transcript', 'foundry_export', 'markdown_export',
    'retrieval_index', 'other'
);

CREATE TABLE source_documents (
    id uuid PRIMARY KEY,
    source_kind text NOT NULL,
    connector text NOT NULL,
    original_path text NOT NULL,
    external_id text,
    first_seen_at timestamptz NOT NULL,
    UNIQUE (connector, original_path)
);

CREATE UNIQUE INDEX source_documents_connector_external_id_uq
    ON source_documents (connector, external_id)
    WHERE external_id IS NOT NULL;

CREATE TABLE source_revisions (
    id uuid PRIMARY KEY,
    source_document_id uuid NOT NULL REFERENCES source_documents(id),
    content_hash text NOT NULL CHECK (content_hash ~ '^[0-9a-f]{64}$'),
    raw_content bytea NOT NULL,
    source_time timestamptz,
    importer_version text NOT NULL,
    captured_at timestamptz NOT NULL,
    UNIQUE (source_document_id, content_hash)
);

CREATE TABLE source_spans (
    id uuid PRIMARY KEY,
    source_revision_id uuid NOT NULL REFERENCES source_revisions(id),
    section_path text,
    start_offset integer NOT NULL CHECK (start_offset >= 0),
    end_offset integer NOT NULL CHECK (end_offset >= start_offset),
    excerpt_hash text NOT NULL CHECK (excerpt_hash ~ '^[0-9a-f]{64}$')
);

CREATE TABLE workflow_sessions (
    id uuid PRIMARY KEY,
    kind workflow_kind NOT NULL,
    started_at timestamptz NOT NULL,
    closed_at timestamptz,
    parent_session_id uuid REFERENCES workflow_sessions(id),
    CHECK (closed_at IS NULL OR closed_at >= started_at),
    CHECK (parent_session_id IS NULL OR parent_session_id <> id)
);

CREATE TABLE proposals (
    id uuid PRIMARY KEY,
    workflow_session_id uuid NOT NULL REFERENCES workflow_sessions(id),
    status proposal_status NOT NULL,
    created_at timestamptz NOT NULL,
    closed_at timestamptz,
    CHECK (closed_at IS NULL OR closed_at >= created_at)
);

CREATE TABLE proposal_versions (
    id uuid PRIMARY KEY,
    proposal_id uuid NOT NULL REFERENCES proposals(id),
    version_number integer NOT NULL CHECK (version_number > 0),
    content_hash text NOT NULL CHECK (content_hash ~ '^[0-9a-f]{64}$'),
    created_at timestamptz NOT NULL,
    supersedes_version_id uuid REFERENCES proposal_versions(id),
    UNIQUE (proposal_id, version_number),
    CHECK (supersedes_version_id IS NULL OR supersedes_version_id <> id)
);

CREATE TABLE proposal_items (
    id uuid PRIMARY KEY,
    proposal_version_id uuid NOT NULL REFERENCES proposal_versions(id),
    sequence integer NOT NULL CHECK (sequence > 0),
    mutation_kind text NOT NULL,
    target_type text NOT NULL,
    target_id uuid,
    before_json jsonb,
    after_json jsonb NOT NULL,
    UNIQUE (proposal_version_id, sequence)
);

CREATE TABLE approvals (
    id uuid PRIMARY KEY,
    proposal_version_id uuid NOT NULL REFERENCES proposal_versions(id),
    scope_json jsonb NOT NULL CHECK (jsonb_typeof(scope_json) = 'array'),
    approved_at timestamptz NOT NULL,
    revoked_at timestamptz,
    CHECK (revoked_at IS NULL OR revoked_at >= approved_at)
);

CREATE TABLE change_sets (
    id uuid PRIMARY KEY,
    idempotency_key text NOT NULL UNIQUE,
    workflow_session_id uuid NOT NULL REFERENCES workflow_sessions(id),
    proposal_version_id uuid REFERENCES proposal_versions(id),
    status change_set_status NOT NULL,
    requested_at timestamptz NOT NULL,
    applied_at timestamptz,
    CHECK ((status = 'applied') = (applied_at IS NOT NULL))
);

CREATE TABLE change_set_items (
    id uuid PRIMARY KEY,
    change_set_id uuid NOT NULL REFERENCES change_sets(id),
    proposal_item_id uuid REFERENCES proposal_items(id),
    outcome text NOT NULL,
    before_json jsonb,
    after_json jsonb,
    UNIQUE (change_set_id, proposal_item_id)
);

CREATE TABLE receipts (
    id uuid PRIMARY KEY,
    change_set_id uuid NOT NULL UNIQUE REFERENCES change_sets(id),
    input_source_revision_id uuid REFERENCES source_revisions(id),
    decision_json jsonb NOT NULL,
    conflict_json jsonb NOT NULL DEFAULT '{}'::jsonb,
    outcome text NOT NULL,
    issued_at timestamptz NOT NULL
);

CREATE TABLE entities (
    id uuid PRIMARY KEY,
    entity_type text NOT NULL,
    canonical_name text NOT NULL,
    created_by_change_set_id uuid NOT NULL REFERENCES change_sets(id),
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    CHECK (length(trim(canonical_name)) > 0)
);

CREATE TABLE entity_aliases (
    id uuid PRIMARY KEY,
    entity_id uuid NOT NULL REFERENCES entities(id),
    namespace text NOT NULL,
    alias text NOT NULL,
    normalized_alias text NOT NULL,
    alias_kind text NOT NULL,
    source_revision_id uuid NOT NULL REFERENCES source_revisions(id),
    UNIQUE (namespace, normalized_alias)
);

CREATE TABLE claims (
    id uuid PRIMARY KEY,
    subject_entity_id uuid NOT NULL REFERENCES entities(id),
    predicate text,
    object_entity_id uuid REFERENCES entities(id),
    assertion_text text NOT NULL CHECK (length(trim(assertion_text)) > 0),
    state claim_state NOT NULL,
    authority authority_kind NOT NULL,
    confidence numeric(5, 4) NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    visibility text NOT NULL CHECK (visibility IN ('dm_only', 'party', 'character')),
    is_conditional boolean NOT NULL DEFAULT false,
    predicts_subject_action boolean NOT NULL DEFAULT false,
    recorded_at timestamptz NOT NULL,
    effective_from timestamptz,
    effective_until timestamptz,
    expected_at timestamptz,
    observed_at timestamptz,
    time_precision text,
    session_id uuid REFERENCES workflow_sessions(id),
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    CHECK (object_entity_id IS NULL OR object_entity_id <> subject_entity_id),
    CHECK (effective_until IS NULL OR effective_from IS NULL OR effective_until >= effective_from),
    CHECK (state <> 'observed' OR observed_at IS NOT NULL)
);

CREATE TABLE claim_evidence (
    claim_id uuid NOT NULL REFERENCES claims(id),
    source_span_id uuid NOT NULL REFERENCES source_spans(id),
    evidence_role text NOT NULL,
    PRIMARY KEY (claim_id, source_span_id, evidence_role)
);

CREATE TABLE claim_supersessions (
    superseding_claim_id uuid NOT NULL REFERENCES claims(id),
    superseded_claim_id uuid NOT NULL REFERENCES claims(id),
    resolution_change_set_id uuid NOT NULL REFERENCES change_sets(id),
    reason text NOT NULL,
    PRIMARY KEY (superseding_claim_id, superseded_claim_id),
    CHECK (superseding_claim_id <> superseded_claim_id)
);

CREATE TABLE relationships (
    id uuid PRIMARY KEY,
    from_entity_id uuid NOT NULL REFERENCES entities(id),
    to_entity_id uuid NOT NULL REFERENCES entities(id),
    relationship_type text NOT NULL,
    assertion_text text NOT NULL,
    state claim_state NOT NULL,
    authority authority_kind NOT NULL,
    confidence numeric(5, 4) NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    visibility text NOT NULL CHECK (visibility IN ('dm_only', 'party', 'character')),
    recorded_at timestamptz NOT NULL,
    effective_from timestamptz,
    effective_until timestamptz,
    expected_at timestamptz,
    observed_at timestamptz,
    time_precision text,
    session_id uuid REFERENCES workflow_sessions(id),
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    CHECK (from_entity_id <> to_entity_id),
    CHECK (state <> 'observed' OR observed_at IS NOT NULL)
);

CREATE TABLE relationship_evidence (
    relationship_id uuid NOT NULL REFERENCES relationships(id),
    source_span_id uuid NOT NULL REFERENCES source_spans(id),
    evidence_role text NOT NULL,
    PRIMARY KEY (relationship_id, source_span_id, evidence_role)
);

CREATE TABLE review_items (
    id uuid PRIMARY KEY,
    kind text NOT NULL,
    status text NOT NULL,
    subject_type text NOT NULL,
    subject_id uuid NOT NULL,
    details jsonb NOT NULL,
    opened_by_change_set_id uuid NOT NULL REFERENCES change_sets(id),
    resolved_by_change_set_id uuid REFERENCES change_sets(id),
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL
);

CREATE TABLE derived_artifacts (
    id uuid PRIMARY KEY,
    kind artifact_kind NOT NULL,
    format_version text NOT NULL,
    content_hash text NOT NULL CHECK (content_hash ~ '^[0-9a-f]{64}$'),
    location text NOT NULL,
    created_at timestamptz NOT NULL,
    producer_version text NOT NULL
);

CREATE TABLE artifact_inputs (
    artifact_id uuid NOT NULL REFERENCES derived_artifacts(id),
    claim_id uuid REFERENCES claims(id),
    relationship_id uuid REFERENCES relationships(id),
    source_revision_id uuid REFERENCES source_revisions(id),
    CHECK (num_nonnulls(claim_id, relationship_id, source_revision_id) = 1),
    UNIQUE NULLS NOT DISTINCT (artifact_id, claim_id, relationship_id, source_revision_id)
);

CREATE TABLE import_runs (
    id uuid PRIMARY KEY,
    connector text NOT NULL,
    started_at timestamptz NOT NULL,
    finished_at timestamptz,
    importer_version text NOT NULL,
    idempotency_key text NOT NULL UNIQUE,
    status text NOT NULL,
    receipt_json jsonb NOT NULL,
    CHECK (finished_at IS NULL OR finished_at >= started_at)
);

CREATE TABLE import_observations (
    id uuid PRIMARY KEY,
    import_run_id uuid NOT NULL REFERENCES import_runs(id),
    source_document_id uuid REFERENCES source_documents(id),
    source_revision_id uuid REFERENCES source_revisions(id),
    classification text NOT NULL,
    outcome text NOT NULL,
    warning_json jsonb NOT NULL DEFAULT '[]'::jsonb
);

CREATE FUNCTION reject_immutable_row_mutation() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION '% is immutable', TG_TABLE_NAME;
END;
$$;

CREATE TRIGGER source_documents_immutable
    BEFORE UPDATE OR DELETE ON source_documents
    FOR EACH ROW EXECUTE FUNCTION reject_immutable_row_mutation();
CREATE TRIGGER source_revisions_immutable
    BEFORE UPDATE OR DELETE ON source_revisions
    FOR EACH ROW EXECUTE FUNCTION reject_immutable_row_mutation();
CREATE TRIGGER source_spans_immutable
    BEFORE UPDATE OR DELETE ON source_spans
    FOR EACH ROW EXECUTE FUNCTION reject_immutable_row_mutation();
CREATE TRIGGER proposal_versions_immutable
    BEFORE UPDATE OR DELETE ON proposal_versions
    FOR EACH ROW EXECUTE FUNCTION reject_immutable_row_mutation();
CREATE TRIGGER proposal_items_immutable
    BEFORE UPDATE OR DELETE ON proposal_items
    FOR EACH ROW EXECUTE FUNCTION reject_immutable_row_mutation();
CREATE TRIGGER receipts_immutable
    BEFORE UPDATE OR DELETE ON receipts
    FOR EACH ROW EXECUTE FUNCTION reject_immutable_row_mutation();

CREATE FUNCTION enforce_pc_agency() RETURNS trigger
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
           OR NOT NEW.is_conditional
       ) THEN
        RAISE EXCEPTION 'PC campaign direction must be conditional, DM-only planning';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER claims_pc_agency
    BEFORE INSERT OR UPDATE ON claims
    FOR EACH ROW EXECUTE FUNCTION enforce_pc_agency();

