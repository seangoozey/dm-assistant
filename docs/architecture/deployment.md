# Deployment and Source Control

## Development deployment

- Host privately on TrueNAS with Docker Compose.
- Do not expose Campaign Core, PostgreSQL, workers, or Cognee directly.
- Authentication integration is deferred while development remains private.
- Use pinned images and persistent TrueNAS datasets.
- Use the scaffold, environment boundary, and operational commands in `deploy/README.md`.

## Planned services

- Windmill server.
- General Windmill worker.
- Windmill PostgreSQL database.
- Campaign Core API.
- Campaign PostgreSQL database.
- Windmill full-code React application.
- Optional Cognee and transcription workers later.

## Dataset categories

```text
postgres-windmill/
postgres-campaign/
source-imports/
audio-originals/
transcripts/
generated-artifacts/
backups/
```

Mount legacy campaign snapshots read-only. Do not mount broad TrueNAS datasets into general workers.

The Markdown connector additionally requires the explicit `--read-only` acknowledgement and a versioned path-policy argument. Its source mount is read-only and it receives only the Campaign Core URL, never `CAMPAIGN_DATABASE_URL`. Use `--dry-run` for aggregate classification verification without submitting source content.

## Git and Windmill deployment

The local repository is authoritative. A local bare repository, Forgejo/Gitea, or other reachable Git service is acceptable; no external provider is required.

Suggested deployment:

1. Pull or check out the reviewed repository.
2. Start or update pinned containers.
3. Wait for health checks.
4. Start Campaign Core; its bootstrap applies pending hash-verified migrations before serving requests. Its database credential remains absent from Windmill services, which invoke the typed change-set API instead of canonical tables.
5. Run `python windmill/deploy_workspace.py --workspace <profile>` and review the dry-run result.
6. Apply the exact reviewed source with `--apply`; the wrapper repeats the preview before the push.
7. Run smoke and acceptance tests.

Automatic bidirectional Git sync is optional. Preview synchronization because missing source resources can remove remote workspace objects inside the selected scope.

The initial `wmill.yaml` owns only `f/dm_assistant/**` scripts, folder metadata, and the reviewed campaign-librarian raw app. Variables, resources, resource types, secrets, flows, schedules, triggers, users, groups, settings, encryption keys, and workspace dependencies remain outside synchronization until a reviewed ticket intentionally adds them. Container rebuilds never substitute for this workspace deployment step.

The Windmill-hosted React shell reaches Campaign Core only through its typed backend runnable and the worker's internal `CAMPAIGN_CORE_URL`; Campaign Core remains private and no browser CORS configuration is required. A future independently hosted frontend may use `HttpCampaignClient` behind a same-origin `/campaign-core` reverse proxy. If that separate frontend uses a different origin during development, configure Campaign Core's `CAMPAIGN_CORS_ORIGINS` with that exact origin. Do not expose Campaign Core publicly in the private deployment merely to avoid configuring the proxy.

## Backup

Use logical PostgreSQL backups in addition to TrueNAS snapshots. Test restoring Windmill and Campaign databases separately. Source audio, imported snapshots, generated artifacts, and the Git repository have different retention and recovery needs.

## Later authentication

Remote access will use the existing reverse proxy and Authentik Proxy Provider in forward-auth mode. Human routes and provider webhook routes will have separate authentication behavior.
