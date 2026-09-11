from __future__ import annotations

from collections import Counter
from hashlib import sha256
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from dm_assistant_core.acceptance import ImportFixtureManifest
from dm_assistant_core.importer import (
    MarkdownScanBatch,
    MarkdownScanner,
    MarkdownScannerConfig,
    SourceSafetyError,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = REPOSITORY_ROOT / "tests" / "fixtures" / "markdown_import"
MANIFEST_PATH = REPOSITORY_ROOT / "tests" / "fixtures" / "markdown_import_manifest.yaml"


def config(root: Path = FIXTURE_ROOT, scan_id: str = "fixture-scan") -> MarkdownScannerConfig:
    return MarkdownScannerConfig(
        root=root,
        root_identifier="sanitized-fixture",
        importer_version="markdown-importer/1.0",
        parser_version="markdown-parser/1.0",
        path_policy_version="starfall-path-policy/1.0",
        read_only=True,
        scan_id=scan_id,
    )


def manifest() -> ImportFixtureManifest:
    raw = yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))
    return ImportFixtureManifest.model_validate(raw)


def test_production_scanner_matches_every_sanitized_fixture() -> None:
    expected_manifest = manifest()
    reads: Counter[str] = Counter()

    def tracked_read(path: Path) -> bytes:
        relative = path.relative_to(FIXTURE_ROOT).as_posix()
        reads[relative] += 1
        return path.read_bytes()

    scanner = MarkdownScanner(config(), tracked_read)
    batch = scanner.scan()
    actual = {source.path: source for source in batch.files}

    assert set(actual) == {item.path for item in expected_manifest.expected_files}
    for expected in expected_manifest.expected_files:
        source = actual[expected.path]
        assert source.classification is expected.classification
        assert source.proposed_outcome is expected.outcome
        assert [candidate.state.value for candidate in source.candidates] == (
            expected.candidate_states
        )
        assert len(source.candidates) == expected.claim_candidates
        assert source.entity_candidates == expected.entity_candidates
        assert set(source.warnings) == set(expected.warnings)
        assert reads[expected.path] == 1
        assert scanner.read_counts[expected.path] == 1
        assert source.content_hash == sha256(source.content).hexdigest()
        assert source.filesystem_modified_at.tzinfo is not None

    for excluded in expected_manifest.excluded_paths:
        assert reads[excluded] == 0
        assert scanner.read_counts[excluded] == 0
    assert set(batch.excluded_paths_encountered) == {
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


def test_scan_batch_round_trips_exact_binary_content() -> None:
    batch = MarkdownScanner(config()).scan()

    encoded = batch.model_dump_json()
    restored = MarkdownScanBatch.model_validate_json(encoded)

    assert restored == batch
    assert all(source.content for source in restored.files)


def test_nested_planning_sections_are_independent_repeated_and_exact() -> None:
    bible = next(
        source
        for source in MarkdownScanner(config()).scan().files
        if source.path == "gm/campaign-bible.md"
    )
    source_text = bible.content.decode("utf-8")

    assert [candidate.section for candidate in bible.candidates] == [
        "Planning Areas / Possible Threads",
        "Planning Areas / Prepared Pressures",
        "Planning Areas / Current Intentions",
        "Planning Areas / Repeated Notes",
        "Planning Areas / Repeated Notes",
    ]
    assert [candidate.state.value for candidate in bible.candidates] == [
        "possible",
        "prepared",
        "intended",
        "possible",
        "possible",
    ]
    assert len({candidate.fingerprint for candidate in bible.candidates}) == 5
    assert all(
        source_text[candidate.start_offset : candidate.end_offset].strip()
        == candidate.assertion_text
        for candidate in bible.candidates
    )
    assert all(candidate.section != "Planning Areas" for candidate in bible.candidates)


def test_new_scan_gets_a_new_retry_key_but_resubmitted_batch_is_stable() -> None:
    first = MarkdownScanner(config(scan_id="scan-one")).scan()
    second = MarkdownScanner(config(scan_id="scan-two")).scan()

    assert first.idempotency_key != second.idempotency_key
    assert first.model_copy() == first


def test_reextract_scope_is_transport_safe_and_changes_the_retry_key() -> None:
    ordinary = MarkdownScanner(config(scan_id="same-scan")).scan()
    scoped = MarkdownScanner(
        config(scan_id="same-scan").model_copy(
            update={"reextract_paths": ("gm/campaign-bible.md",)}
        )
    ).scan()

    assert scoped.reextract_paths == ("gm/campaign-bible.md",)
    assert scoped.idempotency_key != ordinary.idempotency_key
    assert MarkdownScanBatch.model_validate_json(scoped.model_dump_json()) == scoped


def test_symbolic_link_escape_is_rejected_before_read(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    source_root.mkdir()
    (source_root / "lore").mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "private.md").write_text("not admitted", encoding="utf-8")
    link = source_root / "lore" / "escape"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"symbolic links unavailable for this test user: {error}")
    reads = 0

    def forbidden_read(_path: Path) -> bytes:
        nonlocal reads
        reads += 1
        raise AssertionError("escape target was read")

    with pytest.raises(SourceSafetyError, match="escapes source root"):
        MarkdownScanner(config(source_root), forbidden_read).scan()
    assert reads == 0


def test_runtime_configuration_requires_explicit_read_only_acknowledgement() -> None:
    with pytest.raises(ValidationError, match="read_only"):
        MarkdownScannerConfig.model_validate(
            {
                "root": FIXTURE_ROOT,
                "root_identifier": "fixture",
                "importer_version": "1",
                "parser_version": "1",
                "path_policy_version": "1",
            }
        )


def test_path_and_frontmatter_classification_conflict_is_quarantined(
    tmp_path: Path,
) -> None:
    root = tmp_path / "source"
    npc_root = root / "npcs"
    npc_root.mkdir(parents=True)
    (npc_root / "conflict.md").write_text(
        "---\ntype: encounter\nstatus: canon\nfixture: synthetic\n---\n"
        "## Prepared Scenario\nThis conflicts with the NPC path.\n",
        encoding="utf-8",
    )

    source = MarkdownScanner(config(root)).scan().files[0]

    assert source.classification.value == "quarantine"
    assert source.proposed_outcome.value == "quarantined"
    assert [warning.value for warning in source.warnings] == ["classification_conflict"]
    assert source.candidates == ()


def test_live_shaped_canon_status_and_sections_are_classified_without_path_guessing(
    tmp_path: Path,
) -> None:
    root = tmp_path / "source"
    npc_root = root / "npcs"
    npc_root.mkdir(parents=True)
    (npc_root / "example.md").write_text(
        "---\ntype: npc\nstatus: alive\ncanon_status: canon\nfixture: synthetic\n---\n"
        "## Canon Summary\nA supplied durable fact.\n\n"
        "## Goals & Motivations\nA supplied present objective.\n\n"
        "## References\n[[missing-source]]\n",
        encoding="utf-8",
    )

    source = MarkdownScanner(config(root)).scan().files[0]

    assert source.classification.value == "durable_evidence"
    assert [(item.section, item.state.value) for item in source.candidates] == [
        ("Canon Summary", "established"),
        ("Goals & Motivations", "intended"),
    ]
    assert [warning.value for warning in source.warnings] == ["unresolved_link"]


def test_pc_derived_summaries_do_not_duplicate_biography_or_session_evidence(
    tmp_path: Path,
) -> None:
    root = tmp_path / "source"
    pc_root = root / "pcs"
    pc_root.mkdir(parents=True)
    (pc_root / "example.md").write_text(
        "---\ntype: pc\ncanon_status: canon\nplayer: Ryan\nstatus: active\n---\n"
        "# Example\n\n"
        "## Canon Summary\nDerived biography summary.\n\n"
        "## Character Details\n- **Player:** Ryan\n\n"
        "## Background / History\nDerived background summary.\n\n"
        "## Current Status\nDerived from session notes.\n\n"
        "## Relationships\nDerived relationship summary.\n\n"
        "## Private GM Notes\nConditional campaign direction.\n\n"
        "## Original Biography Source\nThe intact player biography.\n",
        encoding="utf-8",
    )

    source = MarkdownScanner(config(root)).scan().files[0]

    assert [(item.section, item.state.value) for item in source.candidates] == [
        ("Private GM Notes", "prepared"),
    ]


def test_path_qualified_wiki_links_resolve_to_their_exact_admitted_file(
    tmp_path: Path,
) -> None:
    root = tmp_path / "source"
    (root / "npcs").mkdir(parents=True)
    (root / "locations").mkdir(parents=True)
    (root / "npcs" / "mixed-npc.md").write_text(
        "---\ntype: npc\nstatus: canon\nfixture: synthetic\n---\n"
        "# Mixed NPC\n\n## Established Facts\n\nA durable fact.\n",
        encoding="utf-8",
    )
    (root / "locations" / "example-location.md").write_text(
        "---\ntype: location\nstatus: canon\nfixture: synthetic\n---\n"
        "# Example Location\n\n## Established Facts\n\n"
        "Exact path [[npcs/mixed-npc]], explicit suffix [[npcs/mixed-npc.md]], "
        "display alias [[mixed-npc|The Archivist]], "
        "and relative form [[../npcs/mixed-npc]] all resolve. "
        "A dead link stays unresolved: [[missing-annex]].\n",
        encoding="utf-8",
    )

    files = {source.path: source for source in MarkdownScanner(config(root)).scan().files}
    location = files["locations/example-location.md"]

    assert [warning.value for warning in location.warnings] == ["unresolved_link"]


def test_path_qualified_link_to_a_wrong_directory_stays_unresolved(
    tmp_path: Path,
) -> None:
    root = tmp_path / "source"
    (root / "npcs").mkdir(parents=True)
    (root / "locations").mkdir(parents=True)
    (root / "npcs" / "mixed-npc.md").write_text(
        "---\ntype: npc\nstatus: canon\nfixture: synthetic\n---\n"
        "# Mixed NPC\n\n## Established Facts\n\nA durable fact.\n",
        encoding="utf-8",
    )
    (root / "locations" / "example-location.md").write_text(
        "---\ntype: location\nstatus: canon\nfixture: synthetic\n---\n"
        "# Example Location\n\n## Established Facts\n\n"
        "Wrong directory is not rescued: [[locations/mixed-npc]].\n",
        encoding="utf-8",
    )

    files = {source.path: source for source in MarkdownScanner(config(root)).scan().files}

    assert [warning.value for warning in files["locations/example-location.md"].warnings] == [
        "unresolved_link"
    ]


def test_ambiguous_bare_basename_reports_ambiguous_link(tmp_path: Path) -> None:
    root = tmp_path / "source"
    (root / "npcs").mkdir(parents=True)
    (root / "locations").mkdir(parents=True)
    (root / "gm" / "brainstorming").mkdir(parents=True)
    for directory, record_type in (("npcs", "npc"), ("locations", "location")):
        (root / directory / "shared-vault.md").write_text(
            f"---\ntype: {record_type}\nstatus: canon\nfixture: synthetic\n---\n"
            f"# Shared Vault\n\n## Established Facts\n\nOne entrance.\n",
            encoding="utf-8",
        )
    (root / "gm" / "brainstorming" / "notes.md").write_text(
        "---\ntype: brainstorm\nfixture: synthetic\n---\n"
        "# Notes\n\nA bare link hits two records: [[shared-vault]].\n",
        encoding="utf-8",
    )

    files = {source.path: source for source in MarkdownScanner(config(root)).scan().files}

    notes = files["gm/brainstorming/notes.md"]
    assert "ambiguous_link" in {warning.value for warning in notes.warnings}


def test_templates_are_not_resolvable_link_targets(tmp_path: Path) -> None:
    root = tmp_path / "source"
    (root / "templates").mkdir(parents=True)
    (root / "gm" / "brainstorming").mkdir(parents=True)
    (root / "templates" / "npc-template.md").write_text(
        "---\ntype: npc\nstatus: canon\nfixture: synthetic\n---\n"
        "# Template\n\n## Established Facts\n\n[Not yet established.]\n",
        encoding="utf-8",
    )
    (root / "gm" / "brainstorming" / "notes.md").write_text(
        "---\ntype: brainstorm\nfixture: synthetic\n---\n"
        "# Notes\n\nA link to a template stays unresolved: [[npc-template]].\n",
        encoding="utf-8",
    )

    files = {source.path: source for source in MarkdownScanner(config(root)).scan().files}

    notes = files["gm/brainstorming/notes.md"]
    assert "unresolved_link" in {warning.value for warning in notes.warnings}
