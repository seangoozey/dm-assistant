---
id: TKT-0141
title: Presumed Retcon surface — unopposed changes to established facts auto-accept with an editable reason
status: backlog
priority: P2
milestone: trustworthy-librarian
depends_on: [TKT-0142]
created: 2026-09-21
updated: 2026-09-21
---

# TKT-0141: Presumed Retcon surface — unopposed changes to established facts auto-accept with an editable reason

## Context

Sean's ruling (2026-09-21, from the Romulus attribute case): when an **established** fact changes and there are **no conflicting observed claims**, the system should **auto-accept the change as a presumed retcon** — no blocking ceremony — with an **editable claim entry** where the presumed reason can be replaced by a specific one (transformation, correction, was-always-wrong…). This refines the retcon invariant rather than weakening it: the comparison still happens (checking for conflicting observed claims IS the comparison), and the explicit resolution becomes presumed-by-default plus editable-after. Real-play authority stays supreme: conflicts WITH observed claims still stop and route to the 0097 conflict queue. Built on the unified claim surface (TKT-0142) — the presumed-retcon entry is a claim card whose reason slot defaults to "presumed retcon."

## Scope when taken up

- **The presumption rule**: on superseding an established (non-observed) claim, check for conflicting observed claims on the same subject; none → supersession proceeds automatically with reason "presumed retcon"; some → existing stop-and-review behavior.
- **The editable entry**: the supersession receipt's reason is editable after the fact (audited like dispositions — the presumption and every later refinement are both on the record); the edit surface is the claim card's reason slot, pre-filled, with the specific-reason vocabulary (transformation / correction / was-always-wrong / free text).
- **Presumed retcons are findable**: a standing review filter (queue of presumed-but-unrefined retcon reasons) so presumptions left as defaults are visible — the productize rule; presumption is a fast path, not a way to lose the question.
- Attribute assignments (claim-backed per the 0139 ruling) inherit this surface: Romulus High Elf → Orc with no observed conflict auto-accepts as presumed retcon; the DM refines to "transformed at the table" when they care to.

## Out of scope

- Weakening observed-claim authority (observed conflicts always stop).
- Auto-refining reasons — only the DM edits a reason.

## Validation evidence

(to record when built)
