import json
from pathlib import Path

import pytest

from dm_assistant_core.importer.cli import build_parser, create_batch, main, summarize

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = REPOSITORY_ROOT / "tests" / "fixtures" / "markdown_import"


def arguments(*extra: str) -> list[str]:
    return [
        "--root",
        str(FIXTURE_ROOT),
        "--root-identifier",
        "sanitized-fixture",
        "--read-only",
        "--scan-id",
        "cli-test",
        *extra,
    ]


def test_cli_requires_explicit_read_only_acknowledgement() -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args(
            ["--root", str(FIXTURE_ROOT), "--root-identifier", "fixture", "--dry-run"]
        )


def test_cli_dry_run_reports_only_aggregate_source_information(
    capsys: pytest.CaptureFixture[str],
) -> None:
    main(arguments("--dry-run"))

    output = json.loads(capsys.readouterr().out)
    assert output["admitted_file_count"] == 17
    assert output["excluded_paths_encountered"] == 9
    assert output["candidate_count"] == 18
    assert "files" not in output
    assert "content" not in output


def test_cli_batch_uses_transport_safe_exact_content() -> None:
    parsed = build_parser().parse_args(
        arguments(
            "--dry-run",
            "--reextract-path",
            "gm/campaign-bible.md",
        )
    )
    batch = create_batch(parsed)

    assert summarize(batch)["admitted_file_count"] == 17
    assert summarize(batch)["reextract_paths"] == ["gm/campaign-bible.md"]
    assert batch.model_validate_json(batch.model_dump_json()) == batch
