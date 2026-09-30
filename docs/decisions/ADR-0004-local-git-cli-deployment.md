# ADR-0004: Local Git and CLI-Driven Windmill Deployment

- Status: proposed (user review 2026-09-28: the decision content matches current practice — local repo authoritative, Windmill exported in-repo, wmill-push deploys — but its Context concerns are not live during development: an external Git remote is irrelevant while the local repository is the authority, so push/synchronization worries are out of scope. Flip or supersede when the TrueNAS production story makes deployment topology a real decision again)
- Date: 2026-07-31

## Context

The repository must move between workstations and fully inform Codex in VS Code. An external Git service is not required.

## Decision

Keep the local Git repository authoritative. Export Windmill apps, scripts, and flows into it. Deploy them through `wmill sync push` or an equivalent controlled initialization step. Automatic bidirectional Git sync is optional.

## Consequences

- A container rebuild alone does not deploy Windmill workspace content.
- Local bare Git, Forgejo/Gitea, GitLab, or another reachable server can be used.
- Deployment scopes require review because synchronization can remove in-scope remote resources absent from source.
- Moving to another workstation requires only the repository, environment configuration, and access to the development services.
