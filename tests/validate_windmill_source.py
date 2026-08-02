"""Validate the narrow, secret-free Windmill source deployment contract."""

from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WINDMILL = ROOT / "windmill"
CONFIG = WINDMILL / "wmill.yaml"
PACKAGE = WINDMILL / "package.json"
LOCK = WINDMILL / "package-lock.json"
DEPLOY = WINDMILL / "deploy_workspace.py"
ALLOWED_FILES = {
    "f/dm_assistant/apps/library.raw_app/App.test.tsx",
    "f/dm_assistant/apps/library.raw_app/App.tsx",
    "f/dm_assistant/apps/library.raw_app/backend/inspect_job.lock",
    "f/dm_assistant/apps/library.raw_app/backend/inspect_job.ts",
    "f/dm_assistant/apps/library.raw_app/backend/inspect_job.yaml",
    "f/dm_assistant/apps/library.raw_app/backend/query_campaign.lock",
    "f/dm_assistant/apps/library.raw_app/backend/query_campaign.ts",
    "f/dm_assistant/apps/library.raw_app/backend/query_campaign.yaml",
    "f/dm_assistant/apps/library.raw_app/backend/review_campaign.lock",
    "f/dm_assistant/apps/library.raw_app/backend/review_campaign.ts",
    "f/dm_assistant/apps/library.raw_app/backend/review_campaign.yaml",
    "f/dm_assistant/apps/library.raw_app/backend/start_health_check.lock",
    "f/dm_assistant/apps/library.raw_app/backend/start_health_check.ts",
    "f/dm_assistant/apps/library.raw_app/backend/start_health_check.yaml",
    "f/dm_assistant/apps/library.raw_app/campaignClient.test.ts",
    "f/dm_assistant/apps/library.raw_app/campaignClient.ts",
    "f/dm_assistant/apps/library.raw_app/index.css",
    "f/dm_assistant/apps/library.raw_app/index.tsx",
    "f/dm_assistant/apps/library.raw_app/jobPlatform.test.ts",
    "f/dm_assistant/apps/library.raw_app/jobPlatform.ts",
    "f/dm_assistant/apps/library.raw_app/operationState.ts",
    "f/dm_assistant/apps/library.raw_app/package-lock.json",
    "f/dm_assistant/apps/library.raw_app/package.json",
    "f/dm_assistant/apps/library.raw_app/queryCampaignBackend.test.ts",
    "f/dm_assistant/apps/library.raw_app/raw_app.yaml",
    "f/dm_assistant/apps/library.raw_app/reviewCampaignBackend.test.ts",
    "f/dm_assistant/apps/library.raw_app/reviewState.ts",
    "f/dm_assistant/apps/library.raw_app/tsconfig.json",
    "f/dm_assistant/folder.meta.yaml",
    "f/dm_assistant/jobs/campaign_core_health.py",
    "f/dm_assistant/jobs/campaign_core_health.script.lock",
    "f/dm_assistant/jobs/campaign_core_health.script.yaml",
}
IGNORED_PARTS = {"node_modules", "dist", "coverage", ".vitest"}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def main() -> None:
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    require(config["includes"] == ["f/dm_assistant/**"], "Windmill include scope widened")
    for key in (
        "skipVariables",
        "skipResources",
        "skipResourceTypes",
        "skipSecrets",
        "skipFlows",
        "skipWorkspaceDependencies",
    ):
        require(config.get(key) is True, f"{key} must remain enabled")
    for key in (
        "includeSchedules",
        "includeTriggers",
        "includeUsers",
        "includeGroups",
        "includeSettings",
        "includeKey",
        "plainSecrets",
    ):
        require(config.get(key) is False, f"{key} must remain disabled")
    require(config.get("skipScripts") is False, "scripts must remain deployable")
    require(config.get("skipApps") is False, "the reviewed librarian app must remain deployable")
    require(config.get("skipFolders") is False, "folder metadata must remain deployable")
    require(config.get("locksRequired") is True, "script locks must be required")

    actual_files = {
        path.relative_to(WINDMILL).as_posix()
        for path in (WINDMILL / "f").rglob("*")
        if path.is_file() and not IGNORED_PARTS.intersection(path.relative_to(WINDMILL).parts)
    }
    require(actual_files == ALLOWED_FILES, "unexpected file in Windmill synchronization scope")

    package = json.loads(PACKAGE.read_text(encoding="utf-8"))
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    require(package["devDependencies"] == {"windmill-cli": "1.775.2"}, "CLI is not exactly pinned")
    require(lock["packages"][""]["devDependencies"] == package["devDependencies"], "lockfile CLI mismatch")

    tracked_paths = [CONFIG, DEPLOY, *(WINDMILL / path for path in sorted(actual_files))]
    tracked_text = "\n".join(path.read_text(encoding="utf-8") for path in tracked_paths)
    secret_patterns = (
        r"(?i)campaign_database_url",
        r"(?i)postgres(?:ql)?://",
        r"(?i)(?:api[_-]?token|password)\s*[:=]\s*[^\s$<{]",
        r"(?i)wmill_token",
    )
    for pattern in secret_patterns:
        require(re.search(pattern, tracked_text) is None, f"secret-like content matched {pattern}")

    deploy_text = DEPLOY.read_text(encoding="utf-8")
    preview_position = deploy_text.index("dry_run=True")
    apply_position = deploy_text.index("dry_run=False")
    require(preview_position < apply_position, "deployment must preview before apply")
    for flag in ("--skip-secrets", "--skip-variables", "--skip-resources", "--lint"):
        require(flag in deploy_text, f"deployment wrapper is missing {flag}")
    require("--show-diffs" not in deploy_text, "deployment wrapper may expose sensitive diffs")
    require("--include-secrets" not in deploy_text, "deployment wrapper may include secrets")
    require("--skip-apps" not in deploy_text, "deployment wrapper prevents the reviewed app")

    print(f"Windmill source policy validation passed for {len(actual_files)} scoped files and CLI 1.775.2.")


if __name__ == "__main__":
    main()
