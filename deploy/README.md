# Private deployment scaffold

This directory defines the initial private Docker Compose stack for Windmill Community Edition, Campaign Core, and two separately credentialed PostgreSQL databases.

`compose.yaml` uses named volumes and loopback-only UI binding for development. `compose.truenas.yaml` replaces persistent volumes with pre-created TrueNAS dataset paths. Only the Windmill HTTP port is published. Campaign Core, both databases, and the worker remain internal.

## Campaign Core boundary

The `campaign-core` service builds the pinned local `dm-assistant-campaign-core:0.1.0` image from `campaign-core/Dockerfile`. It applies hash-verified, forward-only migrations and then starts the FastAPI service. Campaign Core remains internal and receives the only application credential capable of mutating campaign data.

The `legacy-source-check` service is profile-gated, has no network, receives no database credentials, and mounts only the configured Starfall root read-only. It is an infrastructure check, not an importer.

## Images

Production images are pinned in `compose.yaml`:

- Windmill CE `1.775.2`
- PostgreSQL `16.14-alpine3.23`
- Campaign Core `0.1.0`, built from Python `3.13.14-alpine3.23` with pinned Python dependencies

Review release notes and backup both databases before changing a pin. Do not replace pins with `latest` or `main`.

## Development configuration

1. Copy `deploy/.env.example` to `deploy/.env`.
2. Replace every `replace-me` value. Use different URL-safe passwords for the two databases.
3. Set `LEGACY_SOURCE_PATH` to the intended Starfall snapshot or live collection. Never grant write access.
4. Validate and start:

```powershell
docker compose --env-file deploy/.env -f deploy/compose.yaml config --quiet
docker compose --env-file deploy/.env -f deploy/compose.yaml up -d
docker compose --env-file deploy/.env -f deploy/compose.yaml ps
Invoke-WebRequest http://127.0.0.1:8000/api/health/status
docker compose --env-file deploy/.env -f deploy/compose.yaml exec -T campaign-core python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/health').read().decode())"
```

## Complete local UI test lifecycle

`deploy/test-stack.ps1` is the routine Windows entry point for the complete browser-test stack. It combines the production-shaped Compose file with `compose.testing.yaml`, which publishes Campaign Core only on `127.0.0.1:8001` for direct health inspection, waits for both HTTP health endpoints, deploys the reviewed Windmill workspace, and prints the authenticated raw-app URL (`/apps_raw/get/f/dm_assistant/apps/library`). The app itself reaches Campaign Core through a Windmill backend runnable and the internal application network. Routine shutdown preserves both database volumes.

Before the first run:

1. Complete the development configuration above, including `deploy/.env`.
2. Run `npm ci` in both `windmill/` and `windmill/f/dm_assistant/apps/library.raw_app/`.
3. Start Windmill once, complete its browser setup, and create the remote workspace.
4. Register that existing workspace as a CLI profile, for example:

```powershell
cd windmill
.\node_modules\.bin\wmill.cmd workspace add dm-assistant-dev dm-assistant-dev http://127.0.0.1:8000
cd ..
```

After that one-time setup, the normal cycle from the repository root is:

```powershell
.\deploy\test-stack.ps1 up
.\deploy\test-stack.ps1 status
.\deploy\test-stack.ps1 down
```

Use a different registered CLI profile or ports when necessary:

```powershell
.\deploy\test-stack.ps1 up -Workspace my-local-profile -WindmillPort 8080 -CampaignCorePort 8081
```

`up` builds and starts the containers and applies the scoped workspace deployment. Use `-SkipWorkspaceDeploy` only to inspect container health before the one-time Windmill workspace setup is complete. `down` deliberately does not pass `--volumes`; logins, workspaces, deployed resources, and Campaign data therefore survive the next `up`. Data deletion remains a separate, explicit manual operation and is not provided by this routine script.

Run the isolated source-mount check only when needed:

```powershell
docker compose --env-file deploy/.env -f deploy/compose.yaml --profile source-check up -d legacy-source-check
docker compose --env-file deploy/.env -f deploy/compose.yaml ps legacy-source-check
docker compose --env-file deploy/.env -f deploy/compose.yaml stop legacy-source-check
```

Docker Desktop accepts local Windows bind paths but rejects a UNC path such as `\\HOMESERVER\projects\projects\starfall` as a bind source. For a Windows container check, use a deliberately selected local read-only snapshot. Run live-source container checks on TrueNAS or another Linux host using the native, narrowly scoped `/mnt/...` dataset path. This limitation never authorizes copying, modifying, or reorganizing live data.

## TrueNAS deployment

Create dedicated datasets for:

```text
postgres-windmill/
postgres-campaign/
windmill-cache/
windmill-logs/
backups/
```

Do not point a dataset variable at a pool root or broad shared dataset. Ensure the PostgreSQL dataset ownership permits the pinned image's `postgres` user to write. Determine its numeric identity from the pinned image rather than assuming it:

```bash
docker run --rm postgres:16.14-alpine3.23 id postgres
```

Set `WINDMILL_BIND_ADDRESS` to the specific interface used by the private reverse proxy, or `0.0.0.0` only when host firewall and network policy restrict access. Then validate and deploy both files:

```bash
docker compose --env-file deploy/.env -f deploy/compose.yaml -f deploy/compose.truenas.yaml config --quiet
docker compose --env-file deploy/.env -f deploy/compose.yaml -f deploy/compose.truenas.yaml up -d
docker compose --env-file deploy/.env -f deploy/compose.yaml -f deploy/compose.truenas.yaml ps
```

Do not expose PostgreSQL, Campaign Core, worker, or SMTP ports. Authentication remains deferred only while the service is private; remote access must go through the planned reverse proxy and Authentik boundary.

## Credential boundaries

- Windmill server and worker receive only the Windmill database URL.
- Campaign Core receives only the campaign database URL.
- The source-check container receives no database URL and has no network.
- PostgreSQL services share neither a database, credential, network, nor persistent volume.
- Windmill workers do not receive credentials capable of directly mutating canonical tables.

The worker follows Windmill's documented PID-isolation configuration and does not mount the Docker socket. TKT-0007 revalidated the pinned worker on Docker Desktop: namespace isolation still requires the privileged worker mode used by this scaffold. The worker has no Docker socket, campaign source mount, or Campaign PostgreSQL credential; it receives only its Windmill database URL and the non-secret Campaign Core HTTP endpoint. Privileged mode remains an explicitly accepted private-development infrastructure risk. Changing it requires a separately tested worker-isolation design rather than silently disabling the sandbox.

## Windmill workspace source

Container lifecycle and workspace synchronization are separate operations. Compose rebuilds and restarts the pinned server, workers, and databases; it does not deploy scripts, flows, or apps stored in Windmill PostgreSQL.

Repository-owned workspace resources live under `windmill/`. Follow `windmill/README.md` to install the server-matched CLI, configure an external workspace profile, preview the narrow synchronization scope, and explicitly apply it. The wrapper always previews before applying and excludes secrets and all resource classes not currently owned by the repository.

## Logical backup

TrueNAS snapshots do not replace logical PostgreSQL backups. Load `deploy/.env` into the shell, create the configured backup dataset, and write one custom-format dump per database:

```bash
set -a
. deploy/.env
set +a
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p -- "$BACKUP_DATASET"
docker compose --env-file deploy/.env -f deploy/compose.yaml -f deploy/compose.truenas.yaml exec -T windmill-db pg_dump -U "$WINDMILL_DB_USER" -d "$WINDMILL_DB_NAME" --format=custom > "$BACKUP_DATASET/windmill-$timestamp.dump"
docker compose --env-file deploy/.env -f deploy/compose.yaml -f deploy/compose.truenas.yaml exec -T campaign-db pg_dump -U "$CAMPAIGN_DB_USER" -d "$CAMPAIGN_DB_NAME" --format=custom > "$BACKUP_DATASET/campaign-$timestamp.dump"
sha256sum "$BACKUP_DATASET/windmill-$timestamp.dump" "$BACKUP_DATASET/campaign-$timestamp.dump" > "$BACKUP_DATASET/dm-assistant-$timestamp.sha256"
```

Treat dump files as private campaign data. Keep them outside Git and apply restrictive dataset permissions.

## Restore verification

Test each dump independently against a disposable database before relying on it. These commands create new verification databases and do not replace the active databases:

```bash
set -a
. deploy/.env
set +a
docker compose --env-file deploy/.env -f deploy/compose.yaml -f deploy/compose.truenas.yaml exec -T windmill-db createdb -U "$WINDMILL_DB_USER" windmill_restore_check
docker compose --env-file deploy/.env -f deploy/compose.yaml -f deploy/compose.truenas.yaml exec -T windmill-db pg_restore -U "$WINDMILL_DB_USER" -d windmill_restore_check --no-owner < /absolute/path/to/windmill.dump
docker compose --env-file deploy/.env -f deploy/compose.yaml -f deploy/compose.truenas.yaml exec -T campaign-db createdb -U "$CAMPAIGN_DB_USER" campaign_restore_check
docker compose --env-file deploy/.env -f deploy/compose.yaml -f deploy/compose.truenas.yaml exec -T campaign-db pg_restore -U "$CAMPAIGN_DB_USER" -d campaign_restore_check --no-owner < /absolute/path/to/campaign.dump
```

Dropping verification databases or replacing an active database is intentionally not scripted. Before an actual recovery, stop dependent services, preserve the failed database and its volumes, restore into a new database, validate it, and change configuration only after review. Windmill and Campaign databases must be recoverable and cut over separately.

## Static validation

When Docker is unavailable, run the repository policy check:

```bash
python tests/validate_compose_policy.py
```

This verifies image pins, published ports, health checks, persistent volumes, credential separation, internal database networks, the read-only source mount, and TrueNAS dataset mappings. It does not replace `docker compose config`, container startup, or a restore drill.

The validator uses PyYAML because Compose and the existing acceptance fixtures use YAML. TKT-0010 owns pinning and integrating repository test dependencies into the standard test environment.
