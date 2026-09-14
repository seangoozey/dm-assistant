---
id: TKT-0114
title: DM settings page on the user menu
status: backlog
priority: P2
milestone: shared-campaign-knowledge
depends_on: [TKT-0112, TKT-0113]
created: 2026-09-13
updated: 2026-09-13
---

# TKT-0114: DM settings page on the user menu

## Context

The Log page (TKT-0112) and global toasts (TKT-0113) introduce behavior the DM should control, not accept. Sean (2026-09-13): "We're venturing into config territory." Settings get a home: a settings surface behind the DM user item in the top right.

## Scope when taken up

- **Settings entry point** on the DM user control (top right): opens a settings panel/page using the app's page conventions.
- **Initial candidates** (from the 2026-09-13 conversation):
  - Toasts: enable/disable, duration, position preference
  - Activity log: visibility, verbosity (errors-only vs. everything)
- **Other obvious candidates to inventory at pickup** (scrape the app): default Library mode (entries vs. sources), library panel collapse default, Identity card/compact default, capture form defaults (visibility), AI configuration exposure (the Core already exposes `getAIConfiguration`/activation receipts — surface read-only first, mutate only with a clear rule), graph/brainstorm options as those land.
- Storage: UI preferences stay client-side (localStorage, like the existing library-panel-collapse key); anything that changes Core behavior (AI activation) goes through Campaign Core's audited paths, never a local toggle.
- No per-user accounts machinery — single-DM system; "user" is presentation.

## Out of scope

- Multi-user support, roles, or auth.
