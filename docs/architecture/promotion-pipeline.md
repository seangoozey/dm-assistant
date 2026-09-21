# The Promotion Pipeline

Status: proposed framework (shaping rulings 2026-09-20: compact scan-able candidate list, "Approve promotion" commit verb, the name "Promotion Pipeline"); recorded as ADR-0018; implementation tracked in TKT-0136.

## Purpose

One reusable progression — **Proposal → Candidate → Claim** — behind every surface that turns working material into canon: Description filing, Lore creation, Brainstorm promotion, session-note review, and the repair of in-app material that was written but never promoted correctly. The design constraint that governs every choice: **user ease**, defined as *the DM touches only what is wrong*.

## Diagnosis: what Migration taught

The Migration wizard satisfies every promotion invariant, but it implements the safety sequence as the user's navigation: six screens that walk the machine's state machine. Every safety mechanism became a step, every step became a form, and the forms exposed the data model — subject/predicate/object text fields, state/authority/visibility dropdowns per claim (TKT-0046/0047), raw UUID entry for entity resolution, then a version-confirm → approve → apply ceremony. ADR-0012 later proved the deepest error: structure as a *prerequisite* "delayed review and encouraged artificial entities."

The direct session reviewer (TKT-0038/0084) was built against that grain for in-the-moment capture, and it satisfies the **same invariants** while feeling like one action: a statement with inherited dimensions and a "Commit claim and continue" button that verifies and applies against the server-bound version in a single step.

**Thesis:** safety is a property of the commit contract, not of the UI's step count. The user should never walk the machine's state machine; the machine renders its state as one artifact the user scans, corrects, and approves once.

What worked and is retained wholesale: provenance-first with optional structure (ADR-0012), server-derived verbatim evidence (TKT-0060), deterministic fail-closed checks, the single atomic apply transaction, auditable receipts, and no auto-promotion ever.

## The three stages

### Stage 1 — Proposal (authored intent, in a surface)

The working material: description prose, a lore synopsis plus gathered evidence, brainstorm thought text, session-note statements, imported source text — or an existing in-app artifact being reopened for repair (see the repair lane below). This is where AI belongs: drafting the proposal (prose/3, shipped) and gathering evidence (retrieval + graph neighborhood, shipped).

Two hard rules, both paid for during Migration:

- **No structural prerequisites.** A proposal never needs subjects, predicates, or objects filled in before it can be reviewed. Structure is enrichment, never a gate.
- **Never a separate screen.** A proposal lives in the surface where the DM is already working. The pipeline adds a review zone to existing surfaces; it does not add a wizard.

### Stage 2 — Candidate (the atomic preview, derived)

The system derives atomic candidate claims from the proposal: citation mirrors (Description), statement splits (session notes), selected thoughts (Brainstorm), linked or re-attributable evidence (Lore), corrected assertions (repair). Derivation is **deterministic**. AI may *suggest* candidates — suggestions are visually marked, never auto-included, and never gate the commit path.

Each candidate shows exactly what a DM can judge at a glance:

| Element | Behavior |
|---|---|
| **Assertion text** | Editable inline |
| **Subject** | Entity chip with search-and-create picker; never a UUID field |
| **Truth State** | Defaulted by surface (table below); changeable inline |
| **Provenance** | Immutable cite of where it came from |
| **Consequence** | What committing it does: *new claim on X · moves from Y · replaces claim #Z · conflicts with #W — resolve* |

Every other dimension — authority, visibility, confidence, conditionality mechanics, recorded_at, effective/expected/observed dates — is **inherited by default from surface + provenance** and lives behind one expandable *dimensions* disclosure per candidate. The DM opens it only when something is deliberately unusual.

The candidate list, as rendered, **is** the one visible, versioned pending action the short-confirmation invariant requires (see Binding, below).

### Stage 3 — Claim (the commit, one transaction)

One button — **"Approve promotion"**, suffixed with what the transaction bundles (e.g. *Approve promotion · 3 claims + description*, *· new Fleurite Treasury + 2 claims*). It submits exactly the visible list in one idempotent Campaign Core transaction: entities created, claims created, re-attributions recorded, documents filed, supersessions receipted. The receipt lands in the toast/Log event bus.

Deterministic checks surface as **inline candidate flags before the button works**. A conflict requires its explicit 0097-style resolution (dismiss with receipt, or supersede); an ambiguity requires its subject choice; a PC-agency or time violation flags red and cannot be included. Nothing explodes at commit time, and nothing applies partially — a flagged candidate blocks only itself, but commit is unavailable while any included candidate is unresolved.

### Binding: how ease and the approval invariant coexist

The invariants require versioned, exact-bound, atomic approval. The pipeline satisfies them inside the commit rather than before it — the pattern the session reviewer already proved:

1. The click sends the full rendered candidate payload plus an idempotency key.
2. Core builds the immutable proposal version from that payload, binds the approval to exactly that version and item set, applies it, and writes the receipt — **all in one transaction**.
3. Any drift between what is rendered and what the server can derive (a concurrent edit, a superseded source) fails the transaction with a readable error; nothing half-applies.

There is no prior approval to invalidate because approval never precedes the version; there is no pending-proposal queue to manage because the version is created and consumed atomically. Durable proposal rows remain only where queue semantics are the point (the Migration import queue), unchanged.

## The defaults table

Ease = defaults do the work. Overridable per candidate; nothing is hidden permanently.

| Surface / lane | State default | Authority default | Provenance carries |
|---|---|---|---|
| Session-note statement | Observed | Real play | campaign date, verbatim span |
| Description citation mirror | inherits cited claim | inherits cited claim | reference, never duplicate |
| Lore creation | Established | Explicit lore | draft synopsis; linked evidence keeps its own state; re-attribution receipts |
| Brainstorm promotion | Considered | Brainstorm | thought + session |
| Repair: unpromoted authored material | Established | Explicit lore | the original artifact and its capture receipt |
| Repair: re-dimensioning an existing claim | (existing state) | (existing authority) | supersession receipt pointing at the claim being replaced |
| Import (Migration, adopts later) | as extracted | as extracted | source span |

## The repair lane (written in-app, not yet promoted correctly)

In-app writing surfaces leave material at intermediate states: a drafted entity that exists but has no claims (an empty shell), brainstorm thoughts filed as evidence but never promoted, a session capture with pending statements, a description whose gathered references drifted. The pipeline is also the intake for these — the same three stages, seeded differently:

- **Stage 1** reuses the stalled artifact as the proposal: the entity's authored documents and gathered evidence, the unpromoted thought text, the pending candidates.
- **Stage 2** derives candidates from it (claims the description implies, the thought's assertions, the pending statements) and may show a *replaces claim #Z* consequence when correcting material that was promoted wrongly.
- **Stage 3** commits through the same single transaction, with supersession receipts when replacing existing claims.

A standing **unpromoted-material audit** (Tools-panel pattern, like the link audit) finds repair intake candidates: entities with zero claims but authored documents, unpromoted brainstorm thoughts, direct captures with pending statements, entities whose only claims are Considered. Recurring data-quality gaps become standing in-app review features, never one-time manual fixes.

## The reusable backend

One facade service (`application/promotion.py`) over the **existing** machinery — change sets, candidate proposals, claim creation, re-attribution, supersession, document filing — not a parallel system:

- `derive(surface, proposal_refs, hints)` → candidate list with server-filled defaults and deterministic check results. A read; nothing pending is persisted.
- `approve_promotion(payload, idempotency_key)` → the single binding transaction above; returns a receipt (change-set ID, claim IDs, entity IDs, re-attribution and supersession receipts).

The 20-field `CreateClaimDecision` does not disappear — it becomes the server's job to assemble from defaults, with the payload carrying only what the DM saw and touched: assertion text, subject target, Truth State, and any explicitly opened dimension overrides.

## The reusable front end

One component — the **Promotion Review list** — embedded by every consuming surface; each surface keeps its own idiom around it (ADR-0015's flow-surface ruling stands). Per the 2026-09-20 ruling: a compact scan-able list with **all approvable elements at a glance** — scan the list, fix inline, Approve promotion. Consequence lines and flags render on the row, not behind clicks; dimensions are the only thing collapsed.

Failures and receipts flow through the toast/Log event bus. The commit button states the count and the bundle. No wizard chrome, no step headers, no separate approval screen — anywhere.

## AI support seams (fixed, DM-gated)

1. Draft the proposal — prose/3 harness, fire-and-forget into the Drafts tray (shipped).
2. Gather evidence — retrieval + graph neighborhood (shipped).
3. Suggest candidates from proposal text — optional, marked as suggestions, never auto-included, never required.
4. Suggest subject resolution — entity search against canonical names and aliases (shipped as the mention/search machinery).
5. Never: auto-commit, auto-include, or gating the commit path on any model output.

## What never changes

Real-play authority and the CTS transition rules; one owner per assertion (re-attribution with receipts); all-or-none application; the single Campaign Core transaction as the only canonical mutation route; PC-agency and time rules; no auto-promotion or batch approval without individual review; derived artifacts never outrank Campaign PostgreSQL and originals. The Migration import queue, extraction jobs, and disposition audit continue unchanged for the import use case; the wizard's steps 3–6 collapse into the Promotion Review list when TKT-0131 takes that up.
