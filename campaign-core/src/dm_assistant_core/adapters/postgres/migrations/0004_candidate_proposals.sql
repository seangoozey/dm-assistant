ALTER TYPE workflow_kind ADD VALUE IF NOT EXISTS 'import_review';

ALTER TABLE import_candidates
    ADD COLUMN review_status text NOT NULL DEFAULT 'pending'
        CHECK (review_status IN ('pending', 'proposed', 'deferred', 'rejected', 'applied'));

CREATE TABLE proposal_candidate_bindings (
    proposal_item_id uuid PRIMARY KEY REFERENCES proposal_items(id),
    candidate_id uuid NOT NULL REFERENCES import_candidates(id),
    source_revision_id uuid NOT NULL REFERENCES source_revisions(id),
    source_span_id uuid NOT NULL REFERENCES source_spans(id),
    candidate_fingerprint text NOT NULL CHECK (candidate_fingerprint ~ '^[0-9a-f]{64}$'),
    created_at timestamptz NOT NULL
);

CREATE INDEX proposal_candidate_bindings_candidate_idx
    ON proposal_candidate_bindings (candidate_id, proposal_item_id);

CREATE TABLE candidate_dispositions (
    id uuid PRIMARY KEY,
    candidate_id uuid NOT NULL REFERENCES import_candidates(id),
    disposition text NOT NULL CHECK (disposition IN ('deferred', 'rejected')),
    reason text NOT NULL CHECK (length(trim(reason)) > 0),
    created_at timestamptz NOT NULL
);

CREATE INDEX candidate_dispositions_candidate_idx
    ON candidate_dispositions (candidate_id, created_at, id);

CREATE TRIGGER proposal_candidate_bindings_immutable
    BEFORE UPDATE OR DELETE ON proposal_candidate_bindings
    FOR EACH ROW EXECUTE FUNCTION reject_immutable_row_mutation();

CREATE TRIGGER candidate_dispositions_immutable
    BEFORE UPDATE OR DELETE ON candidate_dispositions
    FOR EACH ROW EXECUTE FUNCTION reject_immutable_row_mutation();

CREATE FUNCTION mark_applied_import_candidates() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.status <> 'applied' AND NEW.status = 'applied' THEN
        UPDATE import_candidates candidate
           SET review_status = 'applied', updated_at = NEW.applied_at
         WHERE candidate.review_status = 'proposed'
           AND EXISTS (
               SELECT 1
                 FROM proposal_candidate_bindings binding
                 JOIN proposal_items item ON item.id = binding.proposal_item_id
                WHERE binding.candidate_id = candidate.id
                  AND item.proposal_version_id = NEW.proposal_version_id
           )
           AND NOT EXISTS (
               SELECT 1
                 FROM proposal_candidate_bindings binding
                 JOIN proposal_items item ON item.id = binding.proposal_item_id
                WHERE binding.candidate_id = candidate.id
                  AND item.proposal_version_id = NEW.proposal_version_id
                  AND NOT EXISTS (
                      SELECT 1
                        FROM change_set_items applied_item
                        JOIN change_sets applied_set
                          ON applied_set.id = applied_item.change_set_id
                       WHERE applied_item.proposal_item_id = item.id
                         AND applied_set.status = 'applied'
                  )
           );
        UPDATE proposals proposal
           SET status = 'applied', closed_at = NEW.applied_at
         WHERE proposal.id = (
             SELECT version.proposal_id
               FROM proposal_versions version
              WHERE version.id = NEW.proposal_version_id
         )
           AND NOT EXISTS (
               SELECT 1
                 FROM proposal_items item
                WHERE item.proposal_version_id = NEW.proposal_version_id
                  AND NOT EXISTS (
                      SELECT 1
                        FROM change_set_items applied_item
                        JOIN change_sets applied_set
                          ON applied_set.id = applied_item.change_set_id
                       WHERE applied_item.proposal_item_id = item.id
                         AND applied_set.status = 'applied'
                  )
           );
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER change_sets_mark_applied_import_candidates
    AFTER UPDATE OF status ON change_sets
    FOR EACH ROW EXECUTE FUNCTION mark_applied_import_candidates();
