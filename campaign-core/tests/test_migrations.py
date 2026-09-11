from dm_assistant_core.adapters.postgres.migrate import load_migrations


def test_initial_migration_covers_core_schema_and_safety_triggers() -> None:
    migrations = load_migrations()
    sql = "\n".join(migration.sql for migration in migrations)
    required_tables = {
        "source_documents",
        "source_revisions",
        "source_spans",
        "source_extractions",
        "entities",
        "entity_aliases",
        "claims",
        "claim_evidence",
        "relationships",
        "relationship_evidence",
        "workflow_sessions",
        "proposals",
        "proposal_versions",
        "proposal_items",
        "approvals",
        "change_sets",
        "change_set_items",
        "receipts",
        "review_items",
        "derived_artifacts",
        "artifact_inputs",
        "import_runs",
        "import_observations",
    }

    for table in required_tables:
        assert f"CREATE TABLE {table}" in sql
    assert "reject_immutable_row_mutation" in sql
    assert "enforce_pc_agency" in sql


def test_migration_versions_and_checksums_are_unique() -> None:
    migrations = load_migrations()

    assert len({migration.version for migration in migrations}) == len(migrations)
    assert len({migration.checksum for migration in migrations}) == len(migrations)


def test_atomic_application_is_a_single_database_function() -> None:
    migration = next(item for item in load_migrations() if item.version == "0002_atomic_change_set")

    assert "CREATE FUNCTION apply_change_set(" in migration.sql
    assert "FOR UPDATE" in migration.sql
    assert "pg_advisory_xact_lock" in migration.sql
    assert "INSERT INTO receipts" in migration.sql
    assert "idempotent_replay', true" in migration.sql
    assert "unsupported canonical mutation" in migration.sql


def test_markdown_import_migration_preserves_evidence_and_receipts() -> None:
    migration = next(item for item in load_migrations() if item.version == "0003_markdown_import")

    assert "CREATE TABLE source_document_paths" in migration.sql
    assert "CREATE TABLE import_candidates" in migration.sql
    assert "CREATE TABLE import_candidate_evidence" in migration.sql
    assert "ADD COLUMN path_policy_version" in migration.sql
    assert "opened_by_import_run_id" in migration.sql
    assert "CREATE TRIGGER import_runs_immutable" in migration.sql
    assert "CREATE TRIGGER import_observations_immutable" in migration.sql


def test_candidate_proposal_migration_binds_evidence_and_application_state() -> None:
    migration = next(
        item for item in load_migrations() if item.version == "0004_candidate_proposals"
    )

    assert "ADD COLUMN review_status" in migration.sql
    assert "CREATE TABLE proposal_candidate_bindings" in migration.sql
    assert "CREATE TABLE candidate_dispositions" in migration.sql
    assert "CREATE FUNCTION mark_applied_import_candidates" in migration.sql
    assert "AFTER UPDATE OF status ON change_sets" in migration.sql


def test_source_extraction_migration_tracks_parser_versions_immutably() -> None:
    migration = next(
        item for item in load_migrations() if item.version == "0005_source_extractions"
    )

    assert "CREATE TABLE source_extractions" in migration.sql
    assert "PRIMARY KEY (source_revision_id, parser_version)" in migration.sql
    assert "INSERT INTO source_extractions" in migration.sql
    assert "CREATE TRIGGER source_extractions_immutable" in migration.sql


def test_record_taxonomy_migration_adds_identity_kinds_tags_and_fail_closed_review() -> None:
    migration = next(item for item in load_migrations() if item.version == "0006_record_taxonomy")

    assert "CREATE TABLE kind_definitions" in migration.sql
    assert "CREATE TABLE kind_versions" in migration.sql
    assert "CREATE TABLE records" in migration.sql
    assert "ADD COLUMN entity_kind_id" in migration.sql
    assert "unsupported_legacy_entity_kind" in migration.sql
    assert "unsupported entity kind" in migration.sql
    assert "CREATE TABLE tags" in migration.sql
    assert "CREATE TABLE entity_tag_assignments" in migration.sql
    assert "change_set_items_apply_entity_tags" in migration.sql
    assert "'entity', 'other'" not in migration.sql


def test_entity_metadata_migration_adds_exact_mutation_and_kind_evolution_history() -> None:
    migration = next(
        item for item in load_migrations() if item.version == "0007_entity_metadata_changes"
    )

    assert "CREATE TABLE kind_evolution_events" in migration.sql
    assert "CREATE TABLE kind_evolution_members" in migration.sql
    assert "CREATE FUNCTION apply_entity_metadata_change_set(" in migration.sql
    assert "entity metadata changed after the proposal was reviewed" in migration.sql
    assert "PC and NPC agency kinds cannot be reclassified" in "\n".join(
        item.sql for item in load_migrations()
    )
    assert "CREATE FUNCTION apply_campaign_change_set(" in migration.sql


def test_first_class_plan_migration_enforces_agency_and_outcome_evidence() -> None:
    migration = next(item for item in load_migrations() if item.version == "0008_first_class_plans")

    assert "CREATE TABLE plans" in migration.sql
    assert "player_communicated_nonbinding" in migration.sql
    assert "completion or failure requires separate observed claims" in migration.sql
    assert "CREATE FUNCTION apply_plan_change_set" in migration.sql


def test_campaign_chronology_migration_separates_audit_and_campaign_time() -> None:
    migration = next(
        item for item in load_migrations() if item.version == "0009_campaign_chronology"
    )

    assert "CREATE TABLE campaign_calendars" in migration.sql
    assert "CREATE TABLE campaign_calendar_months" in migration.sql
    assert "CREATE FUNCTION campaign_day_ordinal" in migration.sql
    assert "ADD COLUMN effective_from_year integer" in migration.sql
    assert "ADD COLUMN observed_year integer" in migration.sql
    assert "ADD COLUMN campaign_calendar_id" in migration.sql
    # The old timestamptz campaign-date columns are dropped in the same migration.
    assert "DROP COLUMN effective_from" in migration.sql
    assert "DROP COLUMN observed_at" in migration.sql
    assert "DROP COLUMN time_precision" in migration.sql
    # Existing timestamptz campaign dates are backfilled to integer components before the drop.
    assert "EXTRACT(year  FROM effective_from)" in migration.sql
    assert "EXTRACT(year  FROM observed_at)" in migration.sql
    assert "campaign_calendar_id = 'gregorian-ce'" in migration.sql
    # The claim-insert function is replaced to read integer columns.
    assert "effective_from_year" in migration.sql
    assert "observed_year" in migration.sql
    # Audit timestamps remain timestamptz.
    assert "recorded_at')::timestamptz" in migration.sql


def test_campaign_runtime_state_tracks_only_the_current_ingame_date_cursor() -> None:
    migration = next(
        item for item in load_migrations() if item.version == "0028_campaign_runtime_state"
    )
    assert "CREATE TABLE campaign_runtime_state" in migration.sql
    assert "current_ingame_date" in migration.sql
    assert "campaign_day_ordinal" in migration.sql


def test_brainstorm_sessions_bind_immutable_thought_evidence() -> None:
    migration = next(
        item for item in load_migrations() if item.version == "0036_brainstorm_sessions"
    )
    assert "CREATE TABLE brainstorm_sessions" in migration.sql
    assert "CREATE TABLE brainstorm_thoughts" in migration.sql
    assert "source_revision_id uuid NOT NULL REFERENCES source_revisions" in migration.sql
    assert "candidate_id uuid NOT NULL REFERENCES import_candidates" in migration.sql
    assert "brainstorm_thoughts_immutable" in migration.sql


def test_brainstorm_context_adds_mentions_and_ordered_session_pins() -> None:
    migration = next(
        item for item in load_migrations() if item.version == "0037_brainstorm_context"
    )
    assert "ADD COLUMN mentions_json jsonb NOT NULL" in migration.sql
    assert "CREATE TABLE brainstorm_pins" in migration.sql
    assert "entity_id uuid NOT NULL REFERENCES entities" in migration.sql
    assert "UNIQUE (workflow_session_id, position)" in migration.sql


def test_brainstorm_evidence_pin_migration_preserves_exact_context() -> None:
    migration = next(
        item for item in load_migrations() if item.version == "0038_brainstorm_evidence_pins"
    )
    assert "CREATE TABLE brainstorm_evidence_pins" in migration.sql
    assert "assertion text NOT NULL" in migration.sql
    assert "citation text NOT NULL" in migration.sql


def test_rules_elements_migration_adds_mechanics_and_export_profile() -> None:
    migration = next(item for item in load_migrations() if item.version == "0010_rules_elements")

    assert "CREATE TABLE rules_element_mechanics" in migration.sql
    assert "rules_kind text NOT NULL CHECK" in migration.sql
    assert "'spell', 'feat', 'ability'" in migration.sql
    # The rules_card artifact kind and the markdown_card export profile are registered.
    assert "'rules_card'" in migration.sql
    assert "'export_profile'" in migration.sql
    assert "'markdown_card'" in migration.sql
    # The artifact_inputs table gains an entity_id column for rules-element provenance.
    assert "ADD COLUMN entity_id uuid REFERENCES entities(id)" in migration.sql
    # A trigger persists mechanics when a rules-element entity is applied.
    assert "apply_created_rules_element_mechanics" in migration.sql
    assert "rules_element_mechanics requires rules_kind and summary" in migration.sql
    # The deprecated 'other' artifact kind is not dropped; historical receipts survive.
    assert "DROP TYPE" not in migration.sql


def test_candidate_extractions_migration_adds_enrichment_table() -> None:
    migration = next(
        item for item in load_migrations() if item.version == "0011_candidate_extractions"
    )

    assert "CREATE TABLE candidate_extractions" in migration.sql
    assert "candidate_id uuid NOT NULL REFERENCES import_candidates(id)" in migration.sql
    assert "confidence numeric(5, 4)" in migration.sql
    # Only extraction-proposable states are allowed.
    assert "'observed', 'established', 'intended', 'prepared', 'possible'" in migration.sql
    # Extractions are immutable once written.
    assert "candidate_extractions_immutable" in migration.sql


def test_candidate_extraction_runs_make_reextraction_append_only() -> None:
    migration = next(
        item for item in load_migrations() if item.version == "0012_candidate_extraction_runs"
    )

    assert "CREATE TABLE candidate_extraction_runs" in migration.sql
    assert "ADD COLUMN extraction_run_id" in migration.sql
    assert "ALTER COLUMN extraction_run_id SET NOT NULL" in migration.sql
    assert "candidate_extraction_runs_immutable" in migration.sql
    assert "DELETE FROM candidate_extractions" not in migration.sql


def test_extraction_segment_coverage_is_persisted_with_each_run() -> None:
    migration = next(
        item for item in load_migrations() if item.version == "0013_extraction_segment_coverage"
    )

    assert "ADD COLUMN segments_json" in migration.sql
    assert "ADD COLUMN coverage_json" in migration.sql
    assert "ADD COLUMN source_segment_ids" in migration.sql
    assert "candidate_extractions_source_segments_nonempty" in migration.sql


def test_extraction_failures_are_immutable_derived_diagnostics() -> None:
    migration = next(
        item for item in load_migrations() if item.version == "0015_extraction_failure_analysis"
    )

    assert "CREATE TABLE candidate_extraction_failures" in migration.sql
    assert "raw_response text" in migration.sql
    assert "model_profile_key text" in migration.sql
    assert "prompt_version text" in migration.sql
    assert "candidate_extraction_failures_immutable" in migration.sql


def test_assertion_primary_claims_make_extraction_predicate_optional() -> None:
    migration = next(
        item for item in load_migrations() if item.version == "0016_assertion_primary_claims"
    )

    assert "ALTER COLUMN predicate DROP NOT NULL" in migration.sql
    assert "predicate IS NULL OR length(trim(predicate)) > 0" in migration.sql


def test_subject_resolution_is_persisted_as_a_bounded_core_classification() -> None:
    migration = next(
        item for item in load_migrations() if item.version == "0017_subject_resolution"
    )

    assert "ADD COLUMN subject_resolution" in migration.sql
    assert "'focal_entity', 'named_identity', 'non_entity'" in migration.sql


def test_unresolved_subjects_are_added_without_rewriting_prior_migration() -> None:
    migration = next(
        item
        for item in load_migrations()
        if item.version == "0018_unresolved_subject_resolution"
    )

    assert "DROP CONSTRAINT candidate_extractions_subject_resolution_check" in migration.sql
    assert "'unresolved'" in migration.sql


def test_claim_structure_becomes_optional_without_rewriting_prior_migrations() -> None:
    migration = next(
        item for item in load_migrations() if item.version == "0019_optional_claim_structure"
    )

    assert "ALTER COLUMN subject_entity_id DROP NOT NULL" in migration.sql


def test_pc_profile_edits_are_versioned_and_receipted() -> None:
    migration = next(
        item for item in load_migrations() if item.version == "0020_pc_document_profiles"
    )

    assert "CREATE TABLE pc_document_profiles" in migration.sql
    assert "CREATE TABLE pc_profile_revisions" in migration.sql
    assert "CREATE TABLE pc_profile_receipts" in migration.sql
    assert "idempotency_key text NOT NULL UNIQUE" in migration.sql


def test_explicit_claim_conditions_are_captured_from_applied_proposals() -> None:
    migration = next(
        item for item in load_migrations() if item.version == "0021_explicit_claim_conditions"
    )

    assert "CREATE TABLE claim_conditions" in migration.sql
    assert "conditional claim requires an explicit trigger" in migration.sql
    assert "CREATE TRIGGER claims_capture_explicit_condition" in migration.sql


def test_claim_reconciliation_decisions_are_auditable() -> None:
    migration = next(
        item for item in load_migrations() if item.version == "0022_claim_reconciliation_decisions"
    )

    assert "CREATE TABLE claim_reconciliation_decisions" in migration.sql
    assert "'retain_both', 'duplicate', 'supersede'" in migration.sql
    assert "receipt_id uuid NOT NULL UNIQUE REFERENCES receipts(id)" in migration.sql


def test_committed_claim_correction_is_confined_to_an_atomic_migration_function() -> None:
    migration = next(
        item for item in load_migrations() if item.version == "0023_correct_canonical_claim"
    )

    assert "CREATE FUNCTION correct_canonical_claim" in migration.sql
    assert "INSERT INTO claims" in migration.sql
    assert "INSERT INTO claim_supersessions" in migration.sql
    assert "requested_idempotency_key" in migration.sql


def test_claim_correction_hashing_dependency_is_installed_append_only() -> None:
    migration = next(
        item for item in load_migrations() if item.version == "0024_pgcrypto_for_claim_correction"
    )

    assert "CREATE EXTENSION IF NOT EXISTS pgcrypto" in migration.sql
