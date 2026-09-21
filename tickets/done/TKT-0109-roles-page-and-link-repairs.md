---
id: TKT-0109
title: Roles page, editor navigation guard, faction template fields, document-link repairs
status: done
priority: P1
milestone: shared-campaign-knowledge
depends_on: [TKT-0106, TKT-0108]
created: 2026-09-13
updated: 2026-09-13
---

# TKT-0109: Roles page, editor navigation guard, faction template fields, document-link repairs

## Context (all user-reported 2026-09-13)

1. Clicking Edit on a faction, then opening a different faction without saving/canceling, left the editor open against a null draft → "Identity profile could not be loaded." on most factions. Sean's ruling: moving away with **no pending changes auto-cancels** the edit; moving away with **pending changes forces the issue** (Save or Discard prompt).
2. Roles needed a home beyond per-member seating: existing roles should be linkable to a faction directly, with a **Roles page** listing every role, where it is linked, and unlinked (vacant) roles, with a dropdown to seat an entity. Placement question ("main Library branch?") resolved as a main-nav page: the Library tree is entity entries, and roles are faction-scoped titles, never identities — aggregating across factions belongs at page level.
3. Faction pages should list filled template fields (Aliases, Location, Roles) — like character pages list theirs.
4. "Council of Unity says Heart of Unity" — the entity→document affinity matcher borrowed sibling-subject documents on partial token overlap. Sean: "we're going to have to traverse all records and make sure they're linked correctly, there have been too many failures."

## Implemented

- **Editor navigation guard** (`App.tsx`): `leaveEditorGuard` wraps every sidebar selection path (entries, plans, source-backed documents, tree documents, dossier open-full, Roles page faction navigation). Clean edits close silently; dirty edits block the switch with a red "Unsaved identity profile changes" prompt offering **Save profile** (commits, then proceeds) and **Discard changes**. `loadCanonicalEntry` no longer clobbers an open draft on same-entry reloads (roster operations), and switching always closes the editor first — the null-draft error path is gone.
- **Document-affinity matcher** (`selectEntrySource`): exact filename match first; otherwise every distinctive filename token must belong to the entity's name (dropping qualifiers is fine — "Monastery of Arkin" → monastery.md; generic lore suffixes history/myth/lore/legend allowed — thanore-history.md). A foreign word means sibling subject matter: no borrow.
- **Live link audit** (read-only, `.local/audit_links.py` over all 118 entities): 56 borrows kept, 21 wrong-page borrows dropped by the new rules — including the reported Council of Unity ← heart-of-unity.md **and** ← unity.md (a filename that exactly matches another entity's name is that entity's page, even when this entity's name contains it), Heart of Unity ← unity.md, Mythis Minor ← mythis.md, Monastery of Arkin ← npcs/Arkin.md, five sibling-character cross-borrows (Jace↔Lily Valamacke, Kira/Shira Lana ← Vika-Lana.md, Andice Thromius ← zander-thromius.md), Golden Dawn ← church-of-the-golden-dawn.md, Thromius Exemption ← zander-thromius.md, White Cloaks ← original-white-cloaks.md, and locations/factions borrowing encounter or handout documents. All presentation-level: the matcher runs live per render, so the fix applies immediately with no stored links to repair.
- **Faction hero fields**: faction entry pages render filled template fields — Aliases, Location (base_location), Roles ("Grand Inquisitor ★ — Eustice"; "Vacant") — from entity data, never from a borrowed document's frontmatter.
- **Roles page** (main nav, after Identity): cross-faction listing grouped by faction with role chips (★ leadership), holders, Vacant seats, per-role **Seat a member** dropdown (from that faction's roster) and per-holder **Vacate**; faction names navigate to the Library entry; **Define a role** form links a new role to a faction (name + Leadership ★ unique seat) without seating anyone. Core: migration 0056 (`apply_role_decision` define-only branch, action `define_role`), `RoleDefinitionDecision` + `FactionRoleSummary` models, `POST /identity/decisions/define-role`, `GET /identity/roles`.

### Follow-up (2026-09-13, deployed): Identity Review role declarations on the Roles page

Sean found the Roles page empty despite having declared roles during Identity Review — those live in the `mark_role` decision audit (7 surfaces: Inquisitor, Grand Inquisitor, Commander, Outrider, Herald, Herald of Arkin, Fleurite Exile), which the faction catalog never read. Added `GET /identity/role-declarations` (declared surfaces not yet in any `faction_roles` catalog, case-insensitively matched) and a Roles-page section "Declared during Identity Review — unlinked": each surface gets a faction dropdown, a Leadership ★ checkbox, and **Link** (the audited define-role decision; the surface leaves the unlinked list). Docker test `test_role_declarations_bridge_identity_review` (23 identity tests pass); React test for the link flow (90 pass, `tsc` clean); verified live — all 7 declarations render with link controls. Sean also asked whether only factions can hold roles: answered in-session — see the ticket discussion; scope stays faction-bound because a role's value is roster machinery (holders, unique seats, succession = membership). A declared role with no natural faction (Herald of Arkin) signals a missing organization entity, creatable through Identity Review.

### Follow-up (2026-09-13, deployed): faction-edit bug audit and Library branch sweep

Sean reported factions "blinking" on member removal and asked for an audit of faction edit plus every Library branch. Found and fixed (all UI-layer, Core untouched):

- **The blink**: every roster/role operation reloads the entry, and `loadCanonicalEntry` set `docLoading` first — the whole detail panel flashed "Loading document…" for the fetch duration. Same-entry reloads now skip the loading state (a genuine entry switch still shows it); stale member-search results are cleared on entry switches.
- **Invisible refusals**: add/remove member failures ("already a member") were routed to the Identity page's message, invisible while editing in the Library. Both operations now surface their outcome (red alert on refusal, receipt on success) in the editor itself, matching the role-assignment pattern.
- **Name-resolution removal**: Remove resolved member names through entity search (a failure mode of its own). Roster rows carry `member_id`; removal now uses it directly.
- **Location hero showed borrowed-document frontmatter** instead of the entity's edited profile fields. All non-character entry views now take entity-sourced template fields that win over doc frontmatter: Aliases (faction/location/item/worldbuilding), Location (factions), Location type + Parent location (locations).
- **Role select mismatch**: a member whose `role_title` predates the catalog (free-text legacy) rendered as "No role". The control now shows the held role as an "(outside catalog)" option.

React 92 passed (adds: no-flash roster removal with in-editor receipt, editor-visible membership refusal, location template fields), `tsc` clean. Live sweep verified one entry per branch — FACTION (Carpet Rollers: Status/Aliases/Location), ITEM (Aeon Stone), LOCATION (Faeroth Manor: Location type/Status/Canon status/Parent location), NPC (Romulus), PC (Zander Thromius), WORLDBUILDING (Starfall) — heroes and Edit controls render, nothing stuck loading.

### Follow-up (2026-09-13, deployed): derived co-mentions are never a removable roster

Removing Andice Thromius from the Inquisitors failed with "no current membership to remove" — the Inquisitors have zero membership rows; the UI had rendered the derived co-mention fallback with Remove buttons and role controls. Fixed at the model level: `members` is now exclusively the explicit roster; derived co-mention names moved to a separate `related` field (display context only, suppressed forever once any membership row has ever existed). The entry page labels them "Appears with — Co-mentioned in shared records; not an explicit roster"; the editor shows a "No explicit roster yet" explainer with Add (never Remove) for such factions; the Roles page seat dropdown is roster-only automatically. Full docker suite 529 passed; React 93→97 with the derived-associations regression test; verified live on the Inquisitors.

### Follow-up (2026-09-13, deployed): one Worldbuilding group; page-less entries are the uncompleted ones

Sean's ruling: the lore **sources are the thing** — canonical worldbuilding entries without documents are the incomplete side, so the Library must not present two "Worldbuilding" groups. Implemented: lore documents merged into the single Worldbuilding kind group (one alphabetized list; the separate source family is gone — exact-name documents stay hidden behind the entity that homes them), and every kind group now flags **page-less** entities with a "no page" marker (computed with the same matcher rules that decide an entry's page; tooltip explains the entry owes a description — TKT-0111 is the completion path). Live verification: one group of 14; flagged = Aeon Stone, Golden Dawn, Ley Lines, Mantle of Magic, Starfall, Thromius Exemption; Dusk of Creation correctly unflagged (creation-myth.md is its page via the lore-suffix rule); the marker also surfaced real gaps elsewhere — all 13 factions page-less, 30 queue-created NPCs, and Penelope Clinkhammer lacking a PC sheet. React 100 passed.

## Out of scope / follow-ups

- TKT-0110: standing in-app link audit (the traversal Sean asked for, productized as a review surface rather than a one-time script).
- Global (cross-faction) role dedupe; role renaming/retirement.

## Validation evidence (2026-09-13, deployed)

- **Docker integration**: 22 identity tests pass (adds `test_role_definitions_precede_seating`: vacant seat definition, case-insensitive duplicate refusal, non-faction refusal, definition survives seating). Full local suite 460 passed / 68 skipped.
- **React**: 89 passed, `tsc --noEmit` clean. New tests: auto-cancel + forced save-or-discard on entry switch (including save-then-proceed), matcher rules (foreign token, lore suffix, exact-name clash), faction hero template fields, and the Roles page define→seat→vacate flow.
- **Live verification**: migration `0056_role_definitions` applied; app healthy. Roles page renders in the nav with the define form (13 factions) and empty state. Council of Unity now shows its own faction page (hero: Aliases; Operations; derived Members) instead of Heart of Unity's or Unity's document. Editor guard verified in the browser: clean edit → switching auto-cancels with no error; dirty edit → switch blocked with the red prompt, Discard proceeds to the target.
- Pending: Sean's visual acceptance and first real role seating.

## Closure

Delivered 2026-09-13 through multiple deployed rounds, all actively used: Roles page with define/link/seat/vacate, editor navigation guard, matcher fixes (21 wrong-page borrows dropped), faction template fields, derived-vs-roster split, unified Worldbuilding group with page-less flags. Closed at ticket audit.
