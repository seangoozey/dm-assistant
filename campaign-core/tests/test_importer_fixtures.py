from pathlib import Path

import yaml

from dm_assistant_core.acceptance import ImportFixtureManifest, ReconciliationFixture
from dm_assistant_core.acceptance.importer_fixtures import ImportClassification
from dm_assistant_core.domain import ClaimState, Visibility
from tests.support.importer_harness import (
    ReadTracker,
    ReconciliationStore,
    scan_fixture,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = REPOSITORY_ROOT / "tests" / "fixtures" / "markdown_import"
MANIFEST_PATH = REPOSITORY_ROOT / "tests" / "fixtures" / "markdown_import_manifest.yaml"
RECONCILIATION_PATH = (
    REPOSITORY_ROOT / "tests" / "fixtures" / "markdown_import_reconciliation.yaml"
)


def load_yaml(path: Path) -> object:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_manifest() -> ImportFixtureManifest:
    return ImportFixtureManifest.model_validate(load_yaml(MANIFEST_PATH))


def test_sanitized_corpus_matches_typed_expectations() -> None:
    manifest = load_manifest()
    tracker = ReadTracker()
    scan = scan_fixture(FIXTURE_ROOT, tracker)
    actual = {record.path: record for record in scan.files}

    assert set(actual) == {expected.path for expected in manifest.expected_files}
    for expected in manifest.expected_files:
        record = actual[expected.path]
        assert record.classification is expected.classification
        assert record.outcome is expected.outcome
        assert [candidate.state.value for candidate in record.candidates] == (
            expected.candidate_states
        )
        assert len(record.candidates) == expected.claim_candidates
        assert record.entity_candidates == expected.entity_candidates
        assert set(record.warnings) == set(expected.warnings)
        assert record.source_revisions == 1
        assert record.canonical_mutations == 0
        assert tracker.reads[expected.path] == 1


def test_scope_exclusions_are_pruned_before_content_processing() -> None:
    manifest = load_manifest()
    tracker = ReadTracker()
    scan = scan_fixture(FIXTURE_ROOT, tracker)
    admitted = {record.path for record in scan.files}

    assert set(scan.scope_exclusions) == {
        "art/",
        "backups/",
        "foundry/",
        "gm/location-evidence/",
        "gm/location-migration-inventory.md",
        "inbox/",
        "memory/",
        "other/",
        "root-note.md",
    }
    for excluded_path in manifest.excluded_paths:
        assert excluded_path not in admitted
        assert tracker.reads[excluded_path] == 0


def test_templates_and_navigation_indexes_create_no_live_candidates() -> None:
    scan = scan_fixture(FIXTURE_ROOT, ReadTracker())
    excluded_records = [
        record
        for record in scan.files
        if record.classification
        in {ImportClassification.TEMPLATE, ImportClassification.NAVIGATION_INDEX}
    ]

    assert len(excluded_records) == 2
    assert all(record.entity_candidates == 0 for record in excluded_records)
    assert all(not record.candidates for record in excluded_records)
    assert all(record.canonical_mutations == 0 for record in excluded_records)


def test_planning_and_receipt_paths_cannot_establish_truth() -> None:
    scan = scan_fixture(FIXTURE_ROOT, ReadTracker())
    records = {record.path: record for record in scan.files}
    bible = records["gm/campaign-bible.md"]
    receipt = records["gm/brainstorming/promoted.md"]

    assert {candidate.state for candidate in bible.candidates} == {
        ClaimState.POSSIBLE,
        ClaimState.PREPARED,
        ClaimState.INTENDED,
    }
    assert all(
        candidate.state not in {ClaimState.ESTABLISHED, ClaimState.OBSERVED}
        for candidate in bible.candidates
    )
    assert receipt.candidates == ()
    assert receipt.canonical_mutations == 0


def test_applied_session_delta_cannot_reapply_canonical_claims() -> None:
    scan = scan_fixture(FIXTURE_ROOT, ReadTracker())
    applied = next(record for record in scan.files if record.path == "sessions/notes/applied.md")

    assert [candidate.state for candidate in applied.candidates] == [ClaimState.OBSERVED]
    assert applied.canonical_mutations == 0
    assert "applied_delta_no_reapply" in {warning.value for warning in applied.warnings}


def test_mixed_status_and_pc_agency_are_section_aware() -> None:
    scan = scan_fixture(FIXTURE_ROOT, ReadTracker())
    records = {record.path: record for record in scan.files}
    npc = records["npcs/mixed-npc.md"]
    pc = records["pcs/example-pc.md"]
    prep = records["sessions/prep/next-session.md"]

    assert [(candidate.section, candidate.state) for candidate in npc.candidates] == [
        ("Established Facts", ClaimState.ESTABLISHED),
        ("Current Goals", ClaimState.INTENDED),
        ("Possibilities", ClaimState.POSSIBLE),
    ]
    private_note = next(
        candidate for candidate in pc.candidates if candidate.section == "Private GM Notes"
    )
    assert private_note.state is ClaimState.PREPARED
    assert private_note.visibility is Visibility.DM_ONLY
    assert private_note.conditional is True
    assert private_note.predicts_pc_action is False
    assert [(candidate.section, candidate.state) for candidate in prep.candidates] == [
        ("Recap", ClaimState.OBSERVED),
        ("Expected Outcomes", ClaimState.PREPARED),
    ]
    assert prep.candidates[0].evidence_only is True


def test_legacy_session_mapping_and_frontmatter_warnings_are_narrow() -> None:
    scan = scan_fixture(FIXTURE_ROOT, ReadTracker())
    records = {record.path: record for record in scan.files}

    assert (
        records["sessions/notes/legacy.md"].classification
        is ImportClassification.REAL_PLAY_EVIDENCE
    )
    assert (
        records["sessions/archive/legacy-wrong-path.md"].classification
        is ImportClassification.QUARANTINE
    )
    assert (
        records["lore/invalid-frontmatter.md"].classification
        is ImportClassification.QUARANTINE
    )
    assert (
        records["lore/missing-frontmatter.md"].classification
        is ImportClassification.QUARANTINE
    )
    assert not records["lore/invalid-frontmatter.md"].candidates
    assert not records["lore/missing-frontmatter.md"].candidates


def test_synthetic_reconciliation_preserves_identity_and_truth() -> None:
    fixture = ReconciliationFixture.model_validate(load_yaml(RECONCILIATION_PATH))
    store = ReconciliationStore(fixture)

    for expected_scan in fixture.scans:
        result = store.scan(expected_scan)
        assert list(result.outcomes) == expected_scan.expected_outcomes
        assert result.source_documents == expected_scan.expected_source_documents
        assert result.source_revisions == expected_scan.expected_source_revisions
        assert result.candidates == expected_scan.expected_candidates
        assert result.canonical_truth == expected_scan.expected_canonical_truth

    document = store.documents["synthetic-location-1"]
    assert document.paths == {"locations/old-name.md", "locations/new-name.md"}
    assert len(document.hashes) == 2
    assert len(document.canonical_truth) == 2


def test_importer_fixture_text_is_explicitly_synthetic() -> None:
    for path in FIXTURE_ROOT.rglob("*"):
        if not path.is_file() or path.suffix == ".yaml":
            continue
        text = path.read_text(encoding="utf-8")
        assert "synthetic" in text.casefold() or "fixture: synthetic" in text.casefold()
