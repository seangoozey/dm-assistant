---
id: TKT-0114
title: DM settings page on the user menu
status: done
priority: P2
milestone: shared-campaign-knowledge
depends_on: [TKT-0112, TKT-0113]
created: 2026-09-13
updated: 2026-09-15
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

## Delivery (2026-09-15, deployed)

- **`settings.ts`**: localStorage-backed store (`dm-assistant.settings`) with defaults, subscribe, `useSettings()` hook, and `resetSettingsForTest()`. Client-side only — nothing touches Core.
- **Entry point**: the DM identity chip in the topbar-right is now a button ("Open settings") opening the Settings page — no new nav button, no crowding.
- **Controls shipped** (convention-styled, apply immediately):
  - Notifications: Show toasts (off = bus skips the visible stack — the Log still records everything), toast duration 2–20s.
  - Activity log: Errors only (Log page filters to failures regardless of its filter buttons).
  - Navigation: show/hide Migration and Conventions — hidden pages leave the nav; clearing the checkbox restores them (pages themselves untouched).
- Toast bus consults settings at push time (`getSettings()`), duration per-toast; Log reads settings at render; nav filters via `useSettings()` re-render.
- Validation: settings store tests (defaults/persist/subscribe lifecycle) + toast-integration test (disabled skips stack but logs; re-enable restores) + App test (chip opens page, toggles apply live: Migration leaves/returns nav) — **118 passed**, `tsc` clean. Live-verified: chip opens the page with all three sections; hiding Migration removes it from the nav and restoring brings it back. The App test afterEach now resets the settings module (module-cached state, not just storage).
- Remaining candidates for later (ticket's "inventory at pickup"): default library mode, panel-collapse default, identity card/compact default, capture-form defaults, AI configuration read-only exposure.
