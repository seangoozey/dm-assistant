# ADR-0021: Encounters Own Their Claims; Sessions and Brainstorms Assign Ownership at Commit

- Status: accepted (user rulings 2026-09-28: the encounter-ownership decision, then the mechanism — "yes on everything except timeline")
- Date: 2026-09-28

## Context

Claim ownership by capture source had no standing decision (surfaced during TKT-0138). The problem: an encounter authored by the DM intrinsically changes truth about NPCs, locations, and factions — but requiring the author to sort every statement's true subject per claim buries the user in paperwork. Meanwhile sessions and brainstorms already have a reviewed commit step where ownership can be assigned naturally.

## Decision

1. **An encounter OWNS its own claims.** Authoring an encounter is free-form: its statements become claims owned by the encounter itself, with NO per-claim subject sorting required. Cross-references carry the load: **every reference to a known record in encounter material is auto-mentioned** (the 0100/0101 recognition machinery), so the co-mentioned NPCs/locations/factions receive the retrieval and co-reference benefit of the encounter's claims without owning them. Mentions are what make encounter-ownership harmless — the auto-mention requirement is load-bearing, not decorative.
2. **Sessions and Brainstorms do NOT own claims.** They are **Lore-in-progress interfaces**: until committed, their generated claims are unowned working material; **during a commit, the proposal breaks into candidates and ownership is assigned** per candidate (the Promotion Pipeline's reviewed commit). Unowned session/brainstorm claims in the database are commits whose ownership step never ran — completing them is finishing the commit, not a new kind of work.

## The mechanism (ruled 2026-09-28): encounters ARE Entities

The Entity definition holds the answer: an Entity is the digital representation of an identity, and an identity is whatever the campaign refers back to and accumulates truth about — an event qualifies, and **an encounter is a table event** (authored document, participants as mentions, outcomes as claims, chronology). The session/encounter distinction stands: a session is the OCCASION (a context, ADR-0013, unchanged); an encounter is a thing that HAPPENED with content of its own.

- **Encounters are Entities of kind `encounter`.** Ownership (`subject_entity_id`), the Qualified bar, pages, and mentions all apply unchanged — no parallel ownership mechanism. This amends TKT-0139's scope note ("encounters aren't Entities"), which predated this conversation.
- **Kind criterion** (the faction-ladder precedent): an event earns Entity-hood when it is *authored or referenced* — every encounter document mints its encounter entity; lore events become entities on demand when a reviewed surface (the Lore queue) meets their name in prose. Nothing auto-mints from thin air.
- The 67 encounter-doc orphans resolve as **one action per encounter document** ("assign all 10 claims on the-descent.md to the encounter") — mint the encounter entities from their documents (reviewed batch), then assign.

## The Timeline amendment (ruled 2026-09-28, refined same day): reference first, ownership where earned

**Except the timeline.** The Timeline is a UNIQUE event — all historical lore — with a **dedicated document template**, but its relationship to dated material is primarily REFERENCE, not absorption:

- **Dates are mention targets.** The mention machinery (everywhere it runs — 0100/0101) tags dates as mentions; the Timeline picks up date-mentioned claims **for viewing purposes**, with **ownership left alone** — a dated claim about the Raven King stays owned by the Raven King and merely appears in the timeline view.
- **The Timeline CAN own date records** — its own document's historical content (`lore/timeline.md`'s records — the ambient history with no other home) — but it does not absorb ownership of dated records generally.
- **The document template needs reference viewing**: it renders owned records AND referenced (date-mentioned / dated) claims from across the library, ordered by chronology — the template IS the ordered view. TKT-0042 carries this build; its own document's orphans (the 36) route to its ownership.

## Consequences

- Encounter claims keep their state as authored (the prepared-vs-played distinction remains a per-claim judgment available at authoring, not a gate).
- The auto-mention forcing function (0100/0101) is elevated: it is the mechanism that lets encounter ownership work, and encounter material is a first-class consumer of it.
- TKT-0148's session-reviewer work is the direct implementation of decision 2 for sessions; Brainstorm already behaves this way; Lore binds by construction.
- The orphan cleanup (TKT-0138) routes by source: encounter-doc orphans → their encounter (pending the mechanism above); session/brainstorm orphans → finish the commit (direct assign or Lore bridge for records that don't exist yet).
