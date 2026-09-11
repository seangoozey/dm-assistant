---
id: TKT-0073
title: Project only current claims into curated Documents sections
status: done
priority: P1
milestone: campaign-content-manager
depends_on: [TKT-0071, TKT-0072]
created: 2026-08-13
updated: 2026-08-13
---

# TKT-0073: Project Only Current Claims into Curated Documents Sections

## Outcome

Documents presents the current canonical campaign view while keeping original source text and superseded records available as clearly labeled provenance and history.

## Scope

- Build current-claim projections that exclude superseded or duplicate claims.
- Separate current DM plans, player plans, real-play facts, and historical source text.
- Label source wording as source evidence when it differs from the current canonical assertion.
- Provide a compact history view for prior and superseded claims.
- Refresh document counts and content immediately after application or reconciliation.

## Acceptance criteria

- [x] Current sections never present superseded claims as active alongside their replacements.
- [x] Original source wording remains accessible and is never silently rewritten.
- [x] Planning, truth state, agency, and condition details are distinguishable at a glance.
- [x] Candidate badges count only actionable pending/proposed work.
- [x] Applied, rejected, duplicate, and superseded records remain available through history/audit views.
- [x] Documents refresh after application without requiring a page reload.
- [x] Tests cover the Ruhrogue duplicate-plan case and multiple legitimate concurrent plans.

## Validation evidence

- Repository validation: 294 backend tests passed (28 environment-dependent skips), 35 React tests passed, strict TypeScript and Windmill raw-app build passed, and 38 retrieval cases passed.
- Deployed API verification: Coreferra exposes 1 current DM plan and 1 historical claim; Ruhrogue exposes 2 current claims (one lore fact and one DM plan) and 1 historical superseded claim.
- The source-document API excludes superseded claims from `canonical_claims`, returns them through `claim_history`, and supplies projection, condition, timestamp, and source-evidence fields.
- The test stack was restarted and the updated Windmill app deployed successfully on 2026-08-13.
