# Windmill workspace source

This directory is the authoritative source for the deliberately small Windmill workspace scope. It currently owns only the `f/dm_assistant/**` folder, one infrastructure health job, and the campaign librarian raw app. Campaign truth and domain decisions remain in Campaign Core.

## Install and authenticate

The CLI version matches the pinned Windmill server. From this directory, install it exactly from the committed lockfile:

```powershell
npm ci
```

Configure a workspace profile outside the repository. Tokens must never be placed in `wmill.yaml`, source files, command history, or committed environment files:

```powershell
.\node_modules\.bin\wmill workspace add dm-assistant-dev dm-assistant-dev http://127.0.0.1:8000
```

The CLI prompts for authentication and stores its profile in the user's external configuration directory. The reproducible workspace bootstrap uses the workspace-local `admin` identity represented by `u/admin` in folder ownership. Use a dedicated token for that identity, restricted operationally to this target workspace, and rotate or revoke it independently of repository source.

## Preview and deploy

Preview is the default and cannot mutate the workspace:

```powershell
python deploy_workspace.py --workspace dm-assistant-dev
```

After reviewing the preview, explicitly request application. The wrapper runs a fresh preview first, verifies that the scoped source bytes did not change, and only then runs the non-interactive push:

```powershell
python deploy_workspace.py --workspace dm-assistant-dev --apply
```

Run the apply command a second time after initial deployment. A clean preview and zero remote changes demonstrate idempotency. Missing repository resources may be deleted remotely inside `f/dm_assistant/**`, so scope changes require review.

## Scope and secrets

`wmill.yaml` includes only `f/dm_assistant/**`. Variables, resources, resource types, secrets, flows, schedules, triggers, users, groups, workspace settings, encryption keys, and workspace dependencies are excluded. Apps are enabled only because the checked source policy admits the exact librarian raw-app tree. The deployment wrapper repeats the safety-critical skips on the command line. Secret-shaped filenames are excluded as an additional guard.

Runtime secrets and environment-specific resources are provisioned directly in the target workspace through an independent operational process. They are not pulled into this source tree. Do not use `--include-secrets`, `--plain-secrets`, or `--show-diffs` in deployment automation.

The Compose worker receives the non-secret `CAMPAIGN_CORE_URL` service endpoint. The health job does not accept a caller-supplied URL, preventing workspace callers from redirecting it to arbitrary internal endpoints. The worker still receives no Campaign PostgreSQL credential.

## Containers versus workspace content

Docker Compose manages the pinned Windmill server, workers, database, networks, and volumes. Rebuilding or restarting those containers does not synchronize workspace resources. Conversely, this CLI deployment changes only the selected workspace resources and does not rebuild images, migrate Campaign PostgreSQL, or restart services.

The normal sequence is: update and health-check containers, install the pinned CLI, preview workspace synchronization, apply it, then run smoke checks. Windmill workers receive no Campaign PostgreSQL credentials; jobs call Campaign Core's HTTP API.

`npm audit` currently reports the low-severity `GHSA-g7r4-m6w7-qqqr` advisory in the CLI's transitive `esbuild` development dependency. It concerns running esbuild's development server on Windows; this deployment workflow does not run that server. There is no compatible audit-proposed upgrade, and downgrading the CLI would break the server-version pin, so the finding is accepted for this CLI-only use and should be reassessed when the pinned Windmill release changes.

## Campaign librarian app

The raw app lives at `f/dm_assistant/apps/library.raw_app`. Its `CampaignClient` is the only campaign-read boundary, and its `JobPlatform` adapter is the only Windmill job boundary. `WindmillCampaignClient` invokes the `query_campaign` backend runnable, which calls the worker's internal `CAMPAIGN_CORE_URL`; the raw-app browser sandbox never fetches Campaign Core directly. The portable `HttpCampaignClient` remains available for future hosting outside Windmill. The first job is a Campaign Core health check; the browser receives a job identifier and polls a separate inspection operation, so progress and terminal failures remain visible. A versioned pending-job receipt in session storage allows polling to resume after refresh.

Install and validate the app independently:

```powershell
cd f/dm_assistant/apps/library.raw_app
npm ci
npm test
npm run typecheck
cd ..\..\..\..
.\node_modules\.bin\wmill app lint f/dm_assistant/apps/library.raw_app
```

The Windmill deployment needs no browser API URL or CORS override. Both the retrieval runnable and health job use the worker's non-secret `CAMPAIGN_CORE_URL`, and neither receives a Campaign PostgreSQL credential. A future independently hosted frontend should provide `HttpCampaignClient` with a same-origin reverse-proxy URL or an explicitly allowed development origin.
