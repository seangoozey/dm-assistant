"""Single deterministic validation entry point for local and continuous checks."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(label: str, *arguments: str) -> None:
    print(f"==> {label}", flush=True)
    result = subprocess.run(
        [sys.executable, *arguments],
        cwd=ROOT,
        check=False,
    )
    if result.returncode:
        raise SystemExit(f"{label} failed with exit code {result.returncode}")


def main() -> None:
    run("Ruff", "-m", "ruff", "check", "campaign-core", "tests", "windmill")
    run("mypy", "-m", "mypy", "--config-file", "campaign-core/pyproject.toml")
    run(
        "Windmill mypy",
        "-m",
        "mypy",
        "--config-file",
        "campaign-core/pyproject.toml",
        "windmill/deploy_workspace.py",
        "windmill/f/dm_assistant/jobs/campaign_core_health.py",
    )
    run(
        "Campaign Core and interaction acceptance tests",
        "-m",
        "pytest",
        "-c",
        "campaign-core/pyproject.toml",
        "campaign-core/tests",
    )
    run("Compose policy", "tests/validate_compose_policy.py")
    run("Local test-stack lifecycle", "tests/validate_test_stack.py")
    run("Windmill source policy", "tests/validate_windmill_source.py")
    run("React shell", "tests/validate_react_shell.py")
    run("Retrieval corpus", "tests/validate_retrieval_cases.py")
    print("Repository deterministic validation passed.")


if __name__ == "__main__":
    main()
