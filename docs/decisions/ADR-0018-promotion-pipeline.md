# ADR-0018: The Promotion Pipeline — one Proposal → Candidate → Claim progression for every surface

- Status: proposed (shaping rulings accepted 2026-09-20; full acceptance pending Sean's read of the framework doc)
- Date: 2026-09-20
- Uses ADR-0012 (provenance-first), ADR-0015 (three layers, flow-surface ruling), ADR-0017 (vocabulary, CTS). Framework detail: [architecture/promotion-pipeline.md](../architecture/promotion-pipeline.md).

## Context

Three surfaces need to consume working material into canon — Description filing, Lore creation, Brainstorm promotion — and in-app writing already leaves material that was written but never promoted correctly. Migration solved this class of problem first, for imports, as a six-step wizard; the results were poor for the DM: the safety sequence became the navigation, forms exposed the data model, structure was a prerequisite (ADR-0012's correction), and approval was a three-beat ceremony. The direct session reviewer later proved the same invariants can be met by a single scan-correct-commit artifact. Sean ruled: build one reusable pipeline for all surfaces, key constraint user ease, backend reusable behind a shared front-end experience, AI support accepted at fixed seams, and the pipeline must also intake unpromoted in-app material.

## Decision

1. Every surface that turns working material into canon uses one progression, the **Promotion Pipeline**: **Proposal** (authored intent in a surface, no structural prerequisites, never a separate screen) → **Candidate** (a deterministically derived, atomic preview showing text, subject, Truth State, provenance, and consequence, with all other dimensions inherited from surface + provenance defaults behind one disclosure) → **Claim** (one "Approve promotion" action).
2. Safety is satisfied inside the commit contract, not by step count: the click submits the rendered list; Core builds the immutable proposal version, binds approval to exactly that version, applies, and receipts — in one idempotent transaction (the session-reviewer pattern, generalized). Deterministic checks surface as inline candidate flags before the button works; conflicts resolve through the TKT-0097 receipted pattern.
3. One reusable backend facade (`derive` + `approve_promotion`) assembles the full decision payload server-side from defaults; the front-end payload carries only what the DM saw and touched.
4. One reusable front-end component — the **Promotion Review list**: compact, scan-able, all approvable elements at a glance, fixed inline, one Approve promotion button (user ruling 2026-09-20). Surfaces keep their idioms around it.
5. The pipeline is also the **repair lane** for in-app material that was written but not correctly promoted: stalled artifacts reopen as proposals, candidates may carry *replaces claim #Z* consequences, commits receipt supersessions, and a standing unpromoted-material audit feeds the queue.
6. AI sits at four seams only — draft the proposal, gather evidence, suggest candidates (marked, never auto-included), suggest subjects — and never gates or executes the commit.

## Consequences

Description, Lore, Brainstorm promotion, session review, and repair intake converge on one review surface and one commit service; the Migration wizard keeps its queue for imports and later collapses its steps 3–6 into the same component under TKT-0131. Per-surface commit endpoints stop diverging: the 20-field decision assembly becomes server-side defaults. "Approve promotion" becomes the universal commit verb; the glossary gains a Promotion Pipeline entry when implementation lands. The unpromoted-material audit joins the standing data-quality reviews (link audit, conflict queue).

## Alternatives rejected

- Extend the Migration wizard to new surfaces — rejected: it is the documented failure mode (sequence-as-navigation, structure-as-gate).
- Per-surface endpoints with a shared UI component only — rejected: leaves three diverging commit paths and re-implements defaults per surface.
- Durable pending proposals for every surface — rejected: creates a proposal queue to manage where no queue semantics exist; single-action binding gives exact-version safety without pending state (durable rows remain only for the import queue).
- AI extraction gating the commit — rejected: TKT-0045–0062 established model output is enrichment, never a prerequisite.

## Acceptance

Shaping rulings from Sean (2026-09-20): compact scan-able candidate list with everything at a glance, "Approve promotion" verb, the name "Promotion Pipeline", repair lane requirement. Full acceptance after framework-doc review; implementation through TKT-0136.
