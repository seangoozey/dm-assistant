# ADR-0006: First-Class Plans and Agency Boundaries

- Status: accepted
- Date: 2026-08-02

## Context

Campaign material contains DM development direction, intentions of DM-controlled actors, and plans that players communicate. Treating all three as claims, entity kinds, or a generic intent field either loses stable identity or implies knowledge the DM does not possess. A plan also does not prove that its intended outcome occurred.

## Decision

Add `plan` as a typed record family sharing the stable `records.id` identity. Its controlled `plan_kind` vocabulary is exactly `campaign_direction`, `in_world_plan`, and `player_plan`. Plans contain structured descriptive fields and lifecycle, but never a truth state.

`campaign_direction` is DM-only guidance and has no owner. `in_world_plan` is DM-authored and must be owned by an NPC or faction. `player_plan` is a nonbinding, revocable record of what a player communicated; it must identify the PC, player attribution, communication time, and source evidence. It is never a prediction of the PC's future action or knowledge of the player's internal intent.

The lifecycle is exactly `active`, `completed`, `failed`, `abandoned`, and `superseded`. Every transition is reviewed and receipted. A transition to `completed` or `failed` requires separate `observed` claims; the transition cannot create those claims or establish an outcome by itself.

Plans may reference source spans, other plans, and owner records with real foreign keys. Projections are permitted only as explicitly labeled derived context grounded in an active in-world plan. They do not become observed evidence.

## Consequences

- Named schemes retain one identity across documents and can relate to larger plans.
- Campaign direction remains distinct from actor intentions and player communications.
- The system can reason from DM-authored NPC/faction plans without predicting players.
- Plan state and evidence remain independently auditable.

## Alternatives considered

- Entity kinds for plans: rejected because plans have their own lifecycle and ownership rules.
- Claim state alone: rejected because a named, cross-referenced plan needs stable identity and structure.
- One generic intent kind: rejected because it erases the PC knowledge boundary.
