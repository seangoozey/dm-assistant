# The Promotion Pipeline

Status: accepted framework (user ruling 2026-09-20, recorded as ADR-0018 — accepted after the ownership-model, open-ended-surfaces, and consequence-vs-conflict refinements); shaping rulings: compact scan-able candidate list, "Approve promotion" commit verb, the name "Promotion Pipeline"; implementation tracked in TKT-0136.

## Purpose

One reusable progression — **Proposal → Candidate → Claim** — behind every surface, current and future, that turns working material into canon. The initial adopters are Description filing, Lore creation, Brainstorm promotion, session-note review, and the repair of in-app material that was written but never promoted correctly; the set is expected to grow as the project does, and the design assumes that (see "How a surface joins the pipeline"). The design constraint that governs every choice: **user ease**, defined as *the DM touches only what is wrong*.

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

> **Description-surface amendment (2026-09-24):** the Description reviews CLAIMS, not derived statements — the description is an ordered claim composition; prose is the reading layer and never splits into claims. See ADR-0018's amendment.

The system derives atomic candidate claims from the proposal: citation mirrors (Description), statement splits (session notes), selected thoughts (Brainstorm), linked or re-attributable evidence (Lore), corrected assertions (repair). Derivation is **deterministic**. AI may *suggest* candidates — suggestions are visually marked, never auto-included, and never gate the commit path.

Each candidate shows exactly what a DM can judge at a glance:

| Element | Behavior |
|---|---|
| **Assertion text** | Editable inline |
| **Subject** | Depends on the ownership model (below): bound surfaces show the fixed owner; free surfaces require a per-candidate resolution — existing entity via search-and-create picker, never a UUID field |
| **Truth State** | Defaulted by surface (table below); changeable inline |
| **Provenance** | Immutable cite of where it came from |
| **Consequence** | The mechanical commit consequence — exact by definition, because the transaction itself defines it: *new claim on X · moves from Y · replaces claim #Z* |
| **Conflict flag** | A detection, not a consequence — best-effort and honestly scoped (see below): *known conflict: #W — resolve*. An absent flag is **not** a clean bill of health |

Every other dimension — authority, visibility, confidence, conditionality mechanics, recorded_at, effective/expected/observed dates — is **inherited by default from surface + provenance** and lives behind one expandable *dimensions* disclosure per candidate. The DM opens it only when something is deliberately unusual.

The candidate list, as rendered, **is** the one visible, versioned pending action the short-confirmation invariant requires (see Binding, below).

### Stage 3 — Claim (the commit, one transaction)

One button — **"Approve promotion"**, suffixed with what the transaction bundles (e.g. *Approve promotion · 3 claims + description*, *· new Fleurite Treasury + 2 claims*). It submits exactly the visible list in one idempotent Campaign Core transaction: entities created, claims created, re-attributions recorded, documents filed, supersessions receipted. The receipt lands in the toast/Log event bus.

Deterministic checks surface as **inline candidate flags before the button works**. A *detected* conflict requires its explicit 0097-style resolution (dismiss with receipt, or supersede); an ambiguity requires its subject choice; a PC-agency or time violation flags red and cannot be included. Nothing explodes at commit time, and nothing applies partially — a flagged candidate blocks only itself, but commit is unavailable while any included candidate is unresolved.

### What the conflict flag can and cannot say

The system cannot generally say what a given claim conflicts with. Detection today is narrow: the verified-death temporal detector and the other deterministic checks. Free-text claims can contradict semantically — "Person X is ugly" conflicts with "Person X is cute" — and the system will not see it. The flag therefore means **a conflict the current detectors know how to find**, and an absent flag means no *known* conflict, never *no conflict*. The DM's reading of the list remains the real contradiction check; the flag is a narrow safety net, not an understanding.

Forward-looking management can widen the net over time — structured Attribute domains catch enum-level contradictions, and an AI pre-commit review pass could flag semantic tension (a new seam only if ruled in later). Widening changes what the flag reports; it never changes the flag's meaning, and no surface should be worded as if the system understands contradiction generally.

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

## Ownership models: bound-subject and free-subject surfaces

Surfaces differ structurally in who owns the candidates — not just in defaults (user ruling 2026-09-20):

**Bound-subject — Description.** The proposal is implicit about its owner: the Entity already exists, and every candidate derived from the description prose is owned by it. The subject is page context, not a per-row control. Subject machinery is absent by design. Statement review is mandatory (user ruling 2026-09-21): every statement in the prose gets an explicit include-or-exclude decision — the slice-1 "File description" bypass is transitional and is removed when the review is ready to be the only path.

**Bound-subject — Lore.** Same implicit ownership, but the owner is *created by the commit*: exactly one new record, and the proposal's derived candidates belong to it. Linked evidence that re-attributes INTO the new record is the one place ownership moves, and it moves by explicit *moves from Y* consequence, never by inference.

**Free-subject — Brainstorm.** Not like the others at all: a brainstorm has no owner and can touch many Entities — some already existing, some needing creation. This demands machinery intrinsic to Brainstorm:

- **Per-candidate subject resolution is load-bearing**: each candidate must resolve to an existing Entity or to *create new record* before it can be included. No subject is ever inferred (the session-note ruling: mentions link related records without inferring subject roles).
- **Entity-creation candidates**: *create new record* spawns its own candidate row (NEW RECORD kicker, canonical name + kind), and the claims that chose it group under it — several claims may share one new record, and one promotion may create several.
- **Multi-record bundles**: the commit's consequence suffix grows accordingly (*Approve promotion · 5 claims + 2 records*), and claims referencing records created in the same transaction are keyed by bundle-local reference, since their UUIDs do not exist yet.

Session-note statements share the free-subject model (a note touches many entities), so this machinery serves session capture too, and later the Migration claim step when it adopts the pipeline. The repair lane inherits its surface's model: reopening an unpromoted description is bound; reopening unpromoted brainstorm thoughts is free.

## How a surface joins the pipeline

The set of consuming surfaces is open-ended — the project is in development and today's adopters will not be the final list. A surface adopts by **declaring four things**; everything else (the Promotion Review list, the binding transaction, deterministic checks, receipts, AI seams) is shared machinery it inherits unchanged:

1. **Ownership model** — bound with an existing owner, bound with a created owner, or free.
2. **A defaults-table row** — state, authority, and what provenance carries.
3. **A derivation rule** — how the surface's proposal text yields candidates (citation mirrors, statement splits, selected thoughts, …).
4. **Bundle suffix wording** — what its commit names beyond the claim count (a description document, a new record, …).

A new surface is therefore a configuration, not a new pipeline. Adding one must never require touching the commit transaction, the review component's contract, or the invariants.

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

The 20-field `CreateClaimDecision` does not disappear — it becomes the server's job to assemble from defaults, with the payload carrying only what the DM saw and touched: assertion text, subject target, Truth State, and any explicitly opened dimension overrides. Free-subject payloads reference records created inside the same commit by bundle-local key (`"subject": {"new_record": "r1"}`), resolved to UUIDs by the server within the transaction — the client never sends or receives provisional UUIDs.

## The reusable front end

One component — the **Promotion Review list** — embedded by every consuming surface; each surface keeps its own idiom around it (ADR-0015's flow-surface ruling stands). Per the 2026-09-20 ruling: a compact scan-able list with **all approvable elements at a glance** — scan the list, fix inline, Approve promotion. Consequence lines and flags render on the row, not behind clicks; dimensions are the only thing collapsed.

Failures and receipts flow through the toast/Log event bus. The commit button states the count and the bundle. No wizard chrome, no step headers, no separate approval screen — anywhere.

The component renders the ownership model, not a generic form: bound surfaces show the owner once as page context above the list; free surfaces render a required subject chip on every row, and entity-creation candidates appear as NEW RECORD rows that group their claims beneath them. Pickers (Truth State, subject) are combo-edits; when an AI suggestion exists it co-displays in the same control — green when AI and system agree, otherwise the system's value in blue beside the AI's in orange (user ruling 2026-09-21; tokens defined in ui-conventions when built). The DM's pick always wins; suggestions never merge silently into a default.

## AI support seams (fixed, DM-gated)

1. Draft the proposal — prose/3 harness, fire-and-forget into the Drafts tray (shipped).
2. Gather evidence — retrieval + graph neighborhood (shipped).
3. Suggest candidates from proposal text — optional, marked as suggestions, never auto-included, never required.
4. Suggest subject resolution — entity search against canonical names and aliases (shipped as the mention/search machinery).
5. Never: auto-commit, auto-include, or gating the commit path on any model output.

## What never changes

Real-play authority and the CTS transition rules; one owner per assertion (re-attribution with receipts); all-or-none application; the single Campaign Core transaction as the only canonical mutation route; PC-agency and time rules; no auto-promotion or batch approval without individual review; derived artifacts never outrank Campaign PostgreSQL and originals. The Migration import queue, extraction jobs, and disposition audit continue unchanged for the import use case; the wizard's steps 3–6 collapse into the Promotion Review list when TKT-0131 takes that up.
