"""Static policy checks for the private Compose scaffold."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
COMPOSE_PATH = ROOT / "deploy" / "compose.yaml"
TRUENAS_PATH = ROOT / "deploy" / "compose.truenas.yaml"
ENV_EXAMPLE_PATH = ROOT / "deploy" / ".env.example"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    require(isinstance(data, dict), f"{path} must contain a YAML object")
    return data


def image_is_pinned(image: str) -> bool:
    return ":" in image and not image.endswith((":latest", ":main"))


def parse_env_example() -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in ENV_EXAMPLE_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        require(bool(separator), f"invalid environment line: {raw_line}")
        require(key not in values, f"duplicate environment key: {key}")
        values[key] = value
    return values


def serialized(value: Any) -> str:
    return yaml.safe_dump(value, sort_keys=True)


def main() -> None:
    compose = load_yaml(COMPOSE_PATH)
    truenas = load_yaml(TRUENAS_PATH)
    services = compose.get("services")
    require(isinstance(services, dict), "compose services are required")

    expected_services = {
        "windmill-db",
        "campaign-db",
        "windmill-server",
        "windmill-worker",
        "campaign-core",
        "legacy-source-check",
    }
    require(expected_services <= services.keys(), "one or more required services are missing")

    for service_name, service in services.items():
        image = service.get("image")
        require(isinstance(image, str) and image_is_pinned(image), f"{service_name} image is not pinned")

    published = {name: service.get("ports", []) for name, service in services.items() if service.get("ports")}
    require(set(published) == {"windmill-server"}, "only Windmill server may publish a host port")
    require(len(published["windmill-server"]) == 1, "Windmill server must publish exactly one port")

    for name in ("windmill-db", "campaign-db", "windmill-server", "windmill-worker", "campaign-core", "legacy-source-check"):
        require("healthcheck" in services[name], f"{name} requires a healthcheck")

    networks = compose.get("networks", {})
    require(networks.get("windmill-database", {}).get("internal") is True, "Windmill database network must be internal")
    require(networks.get("campaign-database", {}).get("internal") is True, "campaign database network must be internal")
    require(services["windmill-db"]["networks"] == ["windmill-database"], "Windmill DB network scope is too broad")
    require(services["campaign-db"]["networks"] == ["campaign-database"], "campaign DB network scope is too broad")

    windmill_text = serialized({name: services[name] for name in ("windmill-server", "windmill-worker")})
    core_text = serialized(services["campaign-core"])
    source_text = serialized(services["legacy-source-check"])
    require("CAMPAIGN_DB_PASSWORD" not in windmill_text, "Windmill services received campaign database credentials")
    require("WINDMILL_DB_PASSWORD" not in core_text, "Campaign Core received Windmill database credentials")
    require("DATABASE_URL" not in source_text, "source-check must receive no database credentials")
    require(services["legacy-source-check"].get("network_mode") == "none", "source-check must have no network")

    source_mounts = services["legacy-source-check"].get("volumes", [])
    require(len(source_mounts) == 1 and source_mounts[0].get("read_only") is True, "legacy source mount must be read-only")
    require(source_mounts[0].get("target") == "/sources/starfall", "legacy source mount target changed")

    volumes = compose.get("volumes", {})
    for name in ("windmill-db-data", "campaign-db-data", "windmill-worker-cache", "windmill-worker-logs"):
        require(name in volumes, f"missing persistent volume: {name}")

    truenas_volumes = truenas.get("volumes", {})
    for name in volumes:
        options = truenas_volumes.get(name, {}).get("driver_opts", {})
        require(options.get("o") == "bind", f"TrueNAS volume {name} must be a bind mapping")
        require(isinstance(options.get("device"), str), f"TrueNAS volume {name} needs a dataset variable")

    env = parse_env_example()
    windmill_password = env.get("WINDMILL_DB_PASSWORD", "")
    campaign_password = env.get("CAMPAIGN_DB_PASSWORD", "")
    require("replace-me" in windmill_password, "example Windmill password must remain a placeholder")
    require("replace-me" in campaign_password, "example campaign password must remain a placeholder")
    require(windmill_password != campaign_password, "example database passwords must be distinct")
    require(env.get("WINDMILL_DB_USER") != env.get("CAMPAIGN_DB_USER"), "database users must be distinct")

    core = services["campaign-core"]
    require(core.get("image") == "dm-assistant-campaign-core:0.1.0", "Campaign Core image must be pinned")
    require(core.get("build", {}).get("context") == "../campaign-core", "Campaign Core build context changed")
    require(core.get("read_only") is True, "Campaign Core filesystem must be read-only")
    require("CAMPAIGN_DATABASE_URL" in core.get("environment", {}), "Campaign Core database URL is required")
    require(not core.get("volumes"), "Campaign Core must not mount source or mutable host paths")

    print("Compose policy validation passed for 6 services, 2 isolated databases, and 1 published UI port.")


if __name__ == "__main__":
    main()
