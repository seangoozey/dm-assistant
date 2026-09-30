# Development Plan

This plan is the maintained execution summary. The earlier, more narrative [DM Assistant App Planning Document](reference/DM%20Assistant%20App%20Planning%20Document.docx) is retained as a planning baseline and source of historical context. If they disagree, the current Markdown specifications, accepted ADRs, and completed tickets take precedence.

## Where the system stands (2026-09-28)

**The Promotion Pipeline arc is built and closed.** ADR-0018's four slices (Description, Lore, Brainstorm, repair lane) shipped and were proven in real use; TKT-0136 closed 2026-09-27. Every path to canon goes through mandatory statement review and one receipted Approve action — no bypasses exist (the auto-application premise of the old TKT-0040 was retired as contradicted by this). Later refinements all landed: `::` claim breakpoints with ADR-0019 autosave (0146), claim-backed attribute minting with presumed-retcon supersession (0143), Document/Entity alignment — one renderer and one editor per Kind, sheets as evidence (0147), and the AI Promotion Assistant on Lore plus the Description duplicate check (0137, awaiting model activation for real-data runs).

**The Qualified Entity standard governs** (`docs/product/qualified-entity.md`; TKT-0139/0140 closed): the live audit holds the bar permanently — 71 of 120 entities qualified, zero vocabulary failures, zero corrupted profiles. The finite migration campaign is delivered. Per Sean's 2026-09-28 ruling, finishing the remaining 49 zero-claim entities is baseline ongoing usage ("writing prose for Entities is a baseline purpose of this app and thus has no end"), not a campaign deliverable — the standing enforcement is what matters: nothing new enters empty, and degradation reappears in the audit.

**The domain constitution is coherent** — 19 ADRs; every accepted decision is implemented except the deliberately parked graph track (ADR-0014 remains proposed with it).

## Next execution priority: orphaned claims (TKT-0138)

Sean's ruling (2026-09-28): **data that exists but is unassigned and thus invisible is the relevant gap.** 186 non-superseded claims have no owning entity; no surface lists them today; audit Q3 reports pending. TKT-0138 (ready, P1) builds the standing review: the Core list endpoint with deterministic suggested owners, the Lore bridge as the primary migration path (checked orphans seed a lore item, Consider-marked, ready to Link), direct assign-to-record for obvious homes, a receipted "no owner needed" for ambient history — flipping audit Q3 to computed and folding the Q5 flip (attribute minting landed with 0143, but the audit still reports it pending). The initial-attribution write path already landed (migrations 0067/0068); the queue builds on a working write.

## Then: the unification chain

1. **TKT-0142 — unified claim surface**: one claim card component behind every claim operation (the "russian doll" fix); the Promotion Review row is the seed; absorbs the conflict-display concern from the retired 0040.
2. **TKT-0141 — presumed retcon surface** and **TKT-0145 — session-review re-home** (retires the phase-1 flag dependency): both build on the 0142 card.
3. **TKT-0144 — brainstorm general review**: a rulings conversation with the open Wrath of Romulus session as the living fixture.

## Standing tracks

- **TKT-0137 activation**: the promotion purpose needs Sean's receipted activation in Settings (AI models) and a fresh go for real-data runs; the success bar is recall for consideration, not top-rank precision.
- **TKT-0099 remainder**: @mention queueing in composers; conflict surfacing in creation review (rides with 0142).
- Ready when picked up: **TKT-0135** (last vocabulary-implementation tail), **TKT-0130** (retrieval chronology), **TKT-0119** (responsive strategy), **TKT-0100/0101** (dictionary + mentions, carrying the recorded rulings), **TKT-0042** (timeline), **TKT-0043** (failed-plan review queue — a live AGENTS.md invariant awaiting its turn).
- **Parked with the graph ruling (2026-09-14: promising, not fully ready for a real test; revisit after the DB-completeness front settles)**: TKT-0094/0095 umbrellas and TKT-0096/0103/0104/0105/0107.

## Completed foundations (historical context)

- **Trustworthy librarian**: TrueNAS Compose stack, Campaign Core + migrations, read-only importer with immutable receipts, structured entities/claims/sources/provenance, lexical retrieval with exact citations, live evidence import, exact proposal/approval/application commands, the first scoped live promotion with grounded retrieval proof.
- **Planning workspace and direct capture**: OpenRouter provider with controlled model profiles, grounded extraction harness, source browser, session-note direct capture with @mentions, campaign clock, the chronology walk (45 sessions dated).
- **Identity and presentation arcs**: identity review (281 decisions, 118 identities), faction roles and membership, three-layer presentation (ADR-0015), editable pages with one guarded lifecycle (ADR-0016), domain vocabulary declaration (ADR-0017, implemented via 0132–0134), Dossier curation, conflict surface v1 (0097), the life-status dimension, AI prose writer + async drafting + editable prompts, toasts/Log bus, glossary Help page.
- **The pipeline arc**: all four ADR-0018 surfaces, the Phase 2 Migrations campaign surface with the qualified-entity audit, attribute minting, `::` breakpoints + autosave, Document/Entity alignment, the AI promotion assistant.
- **Session support, as built**: live session runs, encounter progress and table notes, session-note capture into reviewed statements, and the campaign calendar. (The original milestone's "automatic unambiguous updates with receipts" was superseded by mandatory review; the retcon comparison workflow exists narrowly via 0097 and generalizes via 0141; the failed-plan queue remains TKT-0043.)

## Future ambitions still standing (unstarted, from the original milestones)

- Audio upload, transcript preservation, and Audio Brainstorm synthesis.
- The fuller Real Play environment polish: requested encounter read-alouds (creative generation stays opt-in per the invariants).
- Foundry VTT export proof of concept; Google Recorder or an intermediary connector after access verification.
- Deeper knowledge-graph integration if the parked evaluation track ever shows value.

## Cutover principle

The legacy system remains active until the replacement reaches feature and reliability parity. Development imports are one-way and incremental. Final cutover requires a brief legacy-write freeze, final delta import, parity checks, backup, and rollback plan. Separately, in-app legacy behavior stays available behind Settings until its replacement proves out in real use, then retires (the phase-1 Migration wizard is shelved behind its flag pending TKT-0145's re-home); nothing canonical is deleted in a cutover — superseded material stays queryable in revision history.
