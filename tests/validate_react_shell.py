"""Run the deterministic full-code React shell validation."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WINDMILL = ROOT / "windmill"
APP = WINDMILL / "f" / "dm_assistant" / "apps" / "library.raw_app"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def run(label: str, command: list[str], cwd: Path) -> None:
    print(f"==> {label}", flush=True)
    result = subprocess.run(command, cwd=cwd, check=False)
    if result.returncode:
        raise SystemExit(f"{label} failed with exit code {result.returncode}")


def main() -> None:
    npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
    require(npm is not None, "npm is required for React shell validation")
    wmill = WINDMILL / "node_modules" / ".bin" / ("wmill.cmd" if os.name == "nt" else "wmill")
    require(wmill.is_file(), "run npm ci in windmill before React shell validation")
    require((APP / "node_modules").is_dir(), "run npm ci in the librarian raw app")

    package = json.loads((APP / "package.json").read_text(encoding="utf-8"))
    require(package["dependencies"]["windmill-client"] == "1.775.2", "app client must match Windmill")
    require(package["dependencies"]["react"] == "19.0.0", "React must be exactly pinned")

    runtime_files = [
        path
        for path in APP.glob("*.ts*")
        if ".test." not in path.name
    ]
    runtime_text = "\n".join(path.read_text(encoding="utf-8") for path in runtime_files)
    require("DATABASE_URL" not in runtime_text.upper(), "UI contains a direct database boundary")
    require("windmill-client" not in runtime_text, "Windmill calls escaped the backend adapter")
    require("fetch(" not in (APP / "App.tsx").read_text(encoding="utf-8"), "view calls fetch directly")
    require("sessionStorage" in (APP / "App.tsx").read_text(encoding="utf-8"), "pending state is not session-backed")
    entrypoint = (APP / "index.tsx").read_text(encoding="utf-8")
    require("WindmillCampaignClient" in entrypoint, "deployed app bypasses Windmill CampaignClient")
    require("HttpCampaignClient" not in entrypoint, "deployed app performs direct browser fetch")
    query_backend = (APP / "backend" / "query_campaign.ts").read_text(encoding="utf-8")
    require("CAMPAIGN_CORE_URL" in query_backend, "campaign query does not use internal Core URL")
    require("DATABASE_URL" not in query_backend.upper(), "campaign query received a database boundary")

    run("React unit tests", [npm, "test"], APP)
    run("React strict typecheck", [npm, "run", "typecheck"], APP)
    run("Windmill raw-app build", [str(wmill), "app", "lint", str(APP)], WINDMILL)
    print("React shell validation passed: unit tests, strict types, and raw-app build.")


if __name__ == "__main__":
    main()
