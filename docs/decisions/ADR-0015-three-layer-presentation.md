# ADR-0015: Three-Layer System — Canon Under the Hood, Authored Documents, Derived Presentation

- Status: accepted (user ruling 2026-09-15)
- Date: 2026-09-15
- Supplements ADR-0011 and ADR-0012; resolves the document-versus-entity presentation question raised during the identity work.

## Context

Library entry pages rendered canonical claims as the page body — assertion cards in recorded-at order with authority/state chrome. The DM's judgment: this is "underscoring data presented poorly… a list of arbitrarily ordered facts." What reads well (Background, Dossier) are authored or structured blocks. The open question since the identity review — how documents and entities present together — and the description-design debate (derived vs. authored, duplication vs. drift) both pressed on the same missing separation: what a page *is* versus what is *true*.

## Decision

The system separates three layers with distinct natures and one rule each.

1. **Canon, under the hood.** Claims, truth states, authorities, provenance, sources, supersession history — the trust model's machinery. Canon is never the default display surface. Its rule: *everything true lives here, complete and auditable, reachable by one deliberate action* (the Records affordance) — never buried, never decorated for browsing.

2. **Authored documents.** DM-typed prose filed as evidence-class canon input: entity descriptions, session notes, brainstorm thoughts. The only place where display intent and canon meet — written because they read well, filed because the DM wrote them. Their rule: *authored prose enters through the one reviewed door like any DM capture; explicit-lore ceiling; restating a claim is one source saying it, never two.*

3. **Derived presentation.** Every rendered page: per-entity-kind templates assemble formatted blocks from structured canon (status, location, roles, aliases as fields) and authored prose (Background, Description, Operations as reading blocks). Their rule: *display is derived from canon and can therefore never contradict it — look-and-feel is a pure presentation question with zero truth consequences, and templates change displays, never canon.*

The one system-wide "look under the hood" affordance: every entry and page exposes the same Records control (standard icon slot, same label, same position per the UI conventions) opening the audit view — claims with states/authorities, provenance, supersession history, sources. Search and retrieval remain canon-based beneath this layer, unchanged.

## Consequences

Claim-card lists disappear from default pages; the Records drill-down becomes the verify surface for retcon checks, conflict repair (TKT-0097), and provenance questions. Description documents (TKT-0111) are authored canon-input whose rendering is a template block (TKT-0121). Because presentation is derived, it is rebuildable and safe to iterate freely. The glossary (Help page) carries these definitions in DM language; this ADR is the engineering authority.

## Alternatives rejected

- Claims as the page body (status quo): auditable but unreadable; the card catalog is not the reading room.
- Descriptions as fully derived, non-evidentiary (first draft ruling): puts trusted DM knowledge in constitutional limbo; superseded 2026-09-15.
- Per-entity custom layouts: curation belongs to authored prose and per-kind templates, not to layout freedom that canon must then track.

## Acceptance

Accepted by user ruling. Implementation proceeds through TKT-0111 (authoring machinery) and TKT-0121 (templated pages, Records affordance everywhere).
