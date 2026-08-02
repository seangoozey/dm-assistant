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
