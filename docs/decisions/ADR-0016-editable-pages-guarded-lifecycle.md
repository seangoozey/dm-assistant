# ADR-0016: Every page is editable, and edit mode has a guarded lifecycle

- Status: accepted (user ruling 2026-09-16)
- Context: TKT-0125

## Context

The Library presents entry pages from three sources: synthesized from claims (page-less identities), authored description documents, and imported evidence documents (lore writeups, encounters, session notes). Editing affordances had grown per-surface instead of per-rule: page-backed locations had no edit button at all (the entity-profile editor was only offered to page-less entries), page-backed entries with an imported page had no write-description affordance, and the description composer stayed open across page switches — carrying a half-written draft onto whichever entry was selected next.

Sean's ruling (2026-09-16): "A universal rule needs to be that pages are editable and changing pages closes the edit mode without question if no changes have been made, and forces resolution first if they have."

## Decision

1. **Every page is editable.** Editing is never withheld by page source. For imported evidence documents — immutable by ADR-0012's provenance line — "editing the page" means editing the *entity record* (profile editor: name, aliases, kind, location fields, life status) or authoring a description page beside the imported evidence. The document itself stays read-only evidence; the entity is canon.
2. **Write-description is available on every entry page whose current page is not already an authored description** — page-less entries and entries paged by an imported document both get the affordance. Filing an authored page for an imported-paged entry does not demote the imported document; it remains evidence (the Far Realm / scattered-evidence shape is normal).
3. **Guarded edit lifecycle.** Switching pages, entries, or documents while an editor is open:
   - with **no changes made**, the edit mode closes silently and the switch proceeds;
   - with **changes made**, the switch is blocked and the user resolves first — save (where saving is a defined action) or discard.
   The guard covers every editor surface uniformly: identity-profile editor, character (PC/NPC) editor, claim-correction editor, and the description composer (including revise mode). Nothing resets an editor with uncommitted changes without asking.

## Consequences

- The leave-editor guard is the single choke point for selection changes; new editor surfaces join it rather than wiring their own close-on-switch behavior.
- Composer dirtiness is text-vs-seed based: any text in a fresh composer, or any change from the seeded revision text, counts as changes.
- The guard's blocked notice composes its actions from which surfaces are dirty (Save profile / Save changes where defined; Discard always).
- loadCanonicalEntry hard-closes transient edit state when the *entry actually changes* (defense in depth behind the guard, which remains the enforcement point for dirty surfaces).

## Alternatives considered

- **Close-on-switch unconditionally (always discard):** rejected — loses in-progress prose and violates "forces resolution first".
- **Per-surface guards:** rejected — this is how the composer bug happened; the rule must be universal by construction.
- **Making imported documents editable:** rejected — burning the evidence layer is settled standing law (ADR-0012, document-backing rationale).
