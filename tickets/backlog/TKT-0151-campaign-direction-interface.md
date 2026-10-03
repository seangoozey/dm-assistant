---
id: TKT-0151
title: The Campaign — an overarching direction identity with its own kind and template
status: backlog
priority: P2
milestone: trustworthy-librarian
depends_on: []
created: 2026-10-02
updated: 2026-10-02
---

# TKT-0151: The Campaign — an overarching direction identity with its own kind and template

## Context

Sean's ruling (2026-10-02): "There needs to be an interface that is overarching campaign direction that isn't owned by any given other entity. This was the purpose of bible notes… purely speculative direction notes and long term schemes… groupable/organizable… If Timeline is an identity so is this. It would need its own unique template as well."

Design rulings confirmed same day: **name "Campaign"**; **new kind `campaign`** (dedicated template by construction — the Timeline/`event` and encounter precedents); **authored sections** as the organizing shape (the Timeline/`::` style — the DM authors section headings, direction material organizes under them).

## What it is

The Campaign is a **unique identity** (ADR-0021's pattern: the Timeline is an identity; so is this) that owns **speculative direction** — long-term schemes, plot arcs, chapter structures, hidden-truth monitoring — material that belongs to no other entity. It extends the pattern: Timeline owns *history*; Campaign owns *direction*.

- **Material**: direction notes as claims (Truth States: possible/considered/intended — speculative by nature, per the invariants: plans are pressure, never outcomes; future dates are expectations), plus the existing `campaign_direction` PLANS associating to it (the "Campaign Bible — Three-Chapter Structure" plan is its first citizen).
- **Groupable/organizable**: authored sections (e.g., Chapters / Arcs / Schemes / Hidden Truths) — the DM authors the headings; notes organize under them; re-groupable.
- **Not an owner of other records' truth**: direction ABOUT Romulus belongs to Romulus; the Campaign owns the *direction itself* (schemes, structures, monitoring).
- **The GM-plans super-document connection**: Sean's earlier ruling (2026-10-02, the Zander hidden-truth migration) wanted "a gm plans super document some time in the future to monitor these" — the Campaign's Hidden Truths section is the natural home. Fold that here.

## Scope when taken up

1. **Kind machinery** (the 0075 playbook): domain enum + guidance, registry migration (id 20000000-…-00a, namespace entity), UI kind list, glossary entry ("Campaign (Entity)").
2. **The identity**: mint Campaign once (kind `campaign`) — via the mint path (extend its kind parameter beyond encounter|event).
3. **The template**: dedicated Campaign page — authored sections over direction claims; each section renders its claims (speculative states visible: possible/considered chips); plans (campaign_direction) associated; hidden-truth monitoring section. Authoring: description-composer style (claims promote through review into sections — never a prose blob; ADR-0018 mandatory review).
4. **The bible note's plan associates** to Campaign; future direction captures (brainstorm promotions of campaign-scope schemes) can bind here.

## Out of scope

- Session/encounter capture surfaces.
- Auto-organizing notes (authored sections are the DM's judgment).
- The Timeline's ordered template (0042's own build).

## Validation evidence

(to record when built)
