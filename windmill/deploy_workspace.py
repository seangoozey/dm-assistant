"""Preview and optionally apply the repository-owned Windmill workspace source."""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CLI_VERSION = "1.775.2"
WORKSPACE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
SYNC_SAFETY_FLAGS = (
    "--skip-variables",
    "--skip-resources",
    "--skip-resource-types",
    "--skip-secrets",
    "--skip-flows",
    "--skip-workspace-dependencies",
    "--lint",
)
IGNORED_SOURCE_PARTS = {"node_modules", "dist", "coverage", ".vitest"}


def source_digest() -> str:
    """Hash the reviewed source scope so preview and apply use identical bytes."""
    digest = hashlib.sha256()
    paths = [
        ROOT / "wmill.yaml",
        ROOT / "wmill-lock.yaml",
        *(ROOT / "f" / "dm_assistant").rglob("*"),
    ]
    scoped_files = (
        item
        for item in paths
        if item.is_file()
        and not IGNORED_SOURCE_PARTS.intersection(item.relative_to(ROOT).parts)
    )
    for path in sorted(scoped_files, key=lambda item: item.as_posix()):
        digest.update(path.relative_to(ROOT).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def cli_path() -> Path:
    suffix = ".cmd" if os.name == "nt" else ""
    path = ROOT / "node_modules" / ".bin" / f"wmill{suffix}"
    if not path.is_file():
        raise SystemExit("Windmill CLI is missing; run 'npm ci' in the windmill directory")
    return path


def sync_command(workspace: str, *, dry_run: bool) -> list[str]:
    command = [
        str(cli_path()),
        "sync",
        "push",
        "--workspace",
        workspace,
        *SYNC_SAFETY_FLAGS,
    ]
    command.append("--dry-run" if dry_run else "--yes")
    return command


def run(command: list[str]) -> None:
    completed = subprocess.run(command, cwd=ROOT, check=False)
    if completed.returncode:
        raise SystemExit(completed.returncode)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Preview a narrow Windmill sync, then optionally apply those exact source bytes."
    )
    parser.add_argument(
        "--workspace",
        required=True,
        help="Name of a preconfigured external wmill workspace profile.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply only after a successful preview; without this flag the command is preview-only.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not WORKSPACE_PATTERN.fullmatch(args.workspace):
        raise SystemExit("workspace profile contains unsupported characters")
    before = source_digest()
    print(f"Windmill CLI {CLI_VERSION}: previewing workspace '{args.workspace}'", flush=True)
    run(sync_command(args.workspace, dry_run=True))
    if source_digest() != before:
        raise SystemExit("Windmill source changed during preview; review and run again")
    if not args.apply:
        print("Preview complete; no remote changes were applied.", flush=True)
        return
    print("Preview passed; applying the exact previewed source.", flush=True)
    run(sync_command(args.workspace, dry_run=False))
    if source_digest() != before:
        raise SystemExit("Windmill source changed during apply; inspect the remote workspace")


if __name__ == "__main__":
    main()
