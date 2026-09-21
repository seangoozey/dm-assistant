---
id: TKT-0125
title: Universal page editability and guarded edit lifecycle (ADR-0016)
status: done
priority: P1
milestone: shared-campaign-knowledge
depends_on: [TKT-0111, TKT-0121]
created: 2026-09-16
updated: 2026-09-16
---

# TKT-0125: Universal page editability and guarded edit lifecycle (ADR-0016)

## Context (Sean, 2026-09-16)

"the page backed locations, and maybe other documents, don't have an edit button, they also don't have a description write button. If i use write description on one page, and then choose a different page, it maintains description write on the selected page. A universal rule needs to be that pages are editable and changing pages closes the edit mode without question if no changes have been made, and forces resolution first if they have."

Recorded as **ADR-0016** (accepted). Three observed defects:

1. Page-backed locations have no edit button — the entity-profile editor was only offered to page-less entries, and entity profiles were only loaded for page-less or character-doc entries.
2. Page-backed entries whose page is an imported document have no write-description affordance — the button existed only for the unpaged flag, so an entry paged by imported lore can't get its authored page from the page itself.
3. The description composer (and revise mode) survives page switches — a half-written draft silently travels to whatever entry is selected next.

## Scope

- **Edit affordance on every entry page** (non-character kinds): the profile editor opens regardless of page backing; profiles load for every entry view.
- **Write-description affordance wherever the current page is not an authored description** — unpaged and imported-paged entries alike.
- **Guarded lifecycle (the universal rule)**: the leave-editor guard covers identity-profile, character, claim-correction, and composer surfaces. Clean → close silently on switch; dirty → blocked with resolution (save where defined, discard always). loadCanonicalEntry hard-closes transient edit state on a genuine entry change as defense in depth behind the guard.
- Claim-correction editing gets a baseline snapshot so "no changes" is knowable.

## Open questions for Sean (other interface necessities)

1. **Escape key**: should Escape uniformly close/cancel open editors and the composer (with the same dirty guard)?
2. **Draft autosave**: browser-local autosave for composer prose so an accidental navigation or reload can't lose a half-written page?
3. **Imported-document annotation**: imported evidence pages are read-only by design — do you want a lightweight margin-notes surface there eventually, or is Records-under-the-hood sufficient?
4. Anything else you've noticed that feels missing on page surfaces — this ticket is the natural home for the next round.

## Out of scope

- Editing imported documents (immutable evidence, ADR-0012).
- TKT-0120's Draft action (separate build; lands in the composer guarded by this lifecycle).

## Validation evidence

Delivered 2026-09-16, deployed (ADR-0016 accepted and indexed in docs/decisions).

- **Every page editable**: entity profiles now load for every entry view (page-backed included); the Edit button is offered on all structured entry pages regardless of page backing; the profile editor renders over page-backed entries. Entity-sourced template fields (location type/parent, life status, roles) flow to page-backed entries too — profile edits must never display stale doc metadata.
- **Write-description everywhere it applies**: available whenever the current page is not already an authored description — unpaged entries and imported-paged entries alike. Filing beside imported evidence is the documented Far Realm shape (the imported doc stays evidence).
- **Guarded lifecycle**: the leave-editor guard covers identity-profile, character, claim-correction (new JSON baseline), and composer surfaces. Clean → silent close on switch (the composer-travels-between-pages bug is fixed twice over: the guard closes it, and loadCanonicalEntry hard-closes on a genuine entry change). Dirty → blocked with a composable notice (Save profile / Save changes where defined; Discard always); saving one surface while another stays dirty keeps the block until the rest resolve.
- **Tests**: React 124/124 incl. page-backed edit + write-description affordances, clean-composer switch close, dirty-draft block + discard-proceeds; the legacy profile-guard test updated to the generalized notice wording.
- Open questions above await Sean's next pass.

## Follow-up

- The open questions (Escape uniformity, draft autosave, imported-page annotation) stay parked here for Sean's answers.
