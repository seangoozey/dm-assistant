"""Validate the local browser-test lifecycle without starting Docker."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "deploy" / "test-stack.ps1"
OVERRIDE = ROOT / "deploy" / "compose.testing.yaml"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def main() -> None:
    script = SCRIPT.read_text(encoding="utf-8")
    compose = yaml.safe_load(OVERRIDE.read_text(encoding="utf-8"))

    require(set(compose) == {"services"}, "testing override may contain only services")
    require(
        set(compose["services"]) == {"campaign-core"},
        "testing override may change only Campaign Core",
    )
    require(
        compose["services"]["campaign-core"]["ports"]
        == ["127.0.0.1:${CAMPAIGN_CORE_TEST_PORT:-8001}:8000"],
        "Campaign Core test port must be loopback-only",
    )

    for action in ('"up"', '"status"', '"down"'):
        require(action in script, f"test stack script is missing {action}")
    require('"down", "--remove-orphans"' in script, "down must remove orphaned containers")
    require('"down", "--volumes"' not in script, "routine down must preserve database volumes")
    require("campaignCoreUrl" not in script, "Windmill app must not require a browser API override")
    require(
        'apps_raw/get/f/dm_assistant/apps/library"' in script,
        "test stack must print the authenticated Windmill raw-app route",
    )
    require("deploy_workspace.py" in script and "--apply" in script, "up must deploy the app")

    powershell = shutil.which("powershell") or shutil.which("pwsh")
    if powershell:
        parser_command = (
            "$tokens=$null; $errors=$null; "
            f"[System.Management.Automation.Language.Parser]::ParseFile('{SCRIPT}', "
            "[ref]$tokens, [ref]$errors) | Out-Null; "
            "if ($errors.Count) { $errors | ForEach-Object { Write-Error $_ }; exit 1 }"
        )
        result = subprocess.run(
            [powershell, "-NoProfile", "-Command", parser_command],
            cwd=ROOT,
            check=False,
        )
        require(result.returncode == 0, "PowerShell parser rejected deploy/test-stack.ps1")

    print("Local test-stack lifecycle validation passed.")


if __name__ == "__main__":
    main()
