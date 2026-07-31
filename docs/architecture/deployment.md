# Deployment and Source Control

## Development deployment

- Host privately on TrueNAS with Docker Compose.
- Do not expose Campaign Core, PostgreSQL, workers, or Cognee directly.
- Authentication integration is deferred while development remains private.
- Use pinned images and persistent TrueNAS datasets.

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

## Git and Windmill deployment

The local repository is authoritative. A local bare repository, Forgejo/Gitea, or other reachable Git service is acceptable; no external provider is required.

Suggested deployment:

1. Pull or check out the reviewed repository.
2. Start or update pinned containers.
3. Wait for health checks.
4. Apply Campaign Core migrations.
5. Run `wmill sync push` with narrow configured scopes.
6. Run smoke and acceptance tests.

Automatic bidirectional Git sync is optional. Preview synchronization because missing source resources can remove remote workspace objects inside the selected scope.

## Backup

Use logical PostgreSQL backups in addition to TrueNAS snapshots. Test restoring Windmill and Campaign databases separately. Source audio, imported snapshots, generated artifacts, and the Git repository have different retention and recovery needs.

## Later authentication

Remote access will use the existing reverse proxy and Authentik Proxy Provider in forward-auth mode. Human routes and provider webhook routes will have separate authentication behavior.
