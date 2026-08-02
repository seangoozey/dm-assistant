"""Command-line entry point for scanning a read-only tree and calling Campaign Core."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from dm_assistant_core.importer.models import ImportReceipt, MarkdownScanBatch
from dm_assistant_core.importer.scanner import MarkdownScanner, MarkdownScannerConfig


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Import a read-only Starfall Markdown tree")
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--root-identifier", required=True)
    parser.add_argument("--core-url")
    parser.add_argument("--importer-version", default="markdown-importer/1.0")
    parser.add_argument("--parser-version", default="markdown-parser/1.0")
    parser.add_argument("--path-policy-version", default="starfall-path-policy/1.0")
    parser.add_argument(
        "--read-only",
        action="store_true",
        required=True,
        help="required acknowledgement that the configured source is read-only",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--scan-id")
    parser.add_argument(
        "--reextract-path",
        action="append",
        default=[],
        help=(
            "read-only relative path to re-extract with the requested parser version; "
            "repeat for additional paths"
        ),
    )
    return parser


def create_batch(arguments: argparse.Namespace) -> MarkdownScanBatch:
    scanner = MarkdownScanner(
        MarkdownScannerConfig(
            root=arguments.root,
            root_identifier=arguments.root_identifier,
            importer_version=arguments.importer_version,
            parser_version=arguments.parser_version,
            path_policy_version=arguments.path_policy_version,
            read_only=arguments.read_only,
            scan_id=arguments.scan_id,
            reextract_paths=tuple(sorted(arguments.reextract_path, key=str.casefold)),
        )
    )
    return scanner.scan()


def summarize(batch: MarkdownScanBatch) -> dict[str, Any]:
    classifications = Counter(source.classification.value for source in batch.files)
    outcomes = Counter(source.proposed_outcome.value for source in batch.files)
    warnings = Counter(
        warning.value for source in batch.files for warning in source.warnings
    )
    return {
        "root_identifier": batch.root_identifier,
        "admitted_file_count": len(batch.files),
        "excluded_paths_encountered": len(batch.excluded_paths_encountered),
        "candidate_count": sum(len(source.candidates) for source in batch.files),
        "reextract_paths": list(batch.reextract_paths),
        "classifications": dict(sorted(classifications.items())),
        "proposed_outcomes": dict(sorted(outcomes.items())),
        "warnings": dict(sorted(warnings.items())),
    }


def submit(batch: MarkdownScanBatch, core_url: str) -> ImportReceipt:
    request = Request(
        f"{core_url.rstrip('/')}/imports/markdown/scan",
        data=batch.model_dump_json().encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=300) as response:
        return ImportReceipt.model_validate_json(response.read())


def main(arguments: list[str] | None = None) -> None:
    parser = build_parser()
    parsed = parser.parse_args(arguments)
    batch = create_batch(parsed)
    if parsed.dry_run:
        print(json.dumps(summarize(batch), indent=2, sort_keys=True))
        return
    if not parsed.core_url:
        parser.error("--core-url is required unless --dry-run is selected")
    receipt = submit(batch, parsed.core_url)
    print(receipt.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
