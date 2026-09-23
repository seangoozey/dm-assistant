# UI Conventions

The design language of the DM Assistant library app, extracted from `windmill/f/dm_assistant/apps/library.raw_app/index.css`. This is descriptive, not aspirational: it documents what exists so new UI reuses it instead of inventing classes. **Rule: before styling anything new, check this document and grep `index.css` for an equivalent.** A living example page renders every component at `Identity → … → Tools → Conventions` in the app itself.

## Design tokens

| Token | Value | Used for |
| --- | --- | --- |
| Ink | `#292821` | body text |
| Paper | `#f2f0e8` | page background (`.app-shell` adds a subtle radial wash) |
| Card | `#fffefa` | content panels, cards, editors |
| Panel tint | `#f0ede4` / `#f8f5ec` / `#fbf8ef` | secondary panel surfaces (queues, hovers) |
| Accent | `#82533a` | primary actions, active nav underline, icons, kickers |
| Accent hover | `#68412d` | primary button hover |
| Accent text | `#754831` / `#84513b` / `#8b5b43` | links, summaries, labels (variants, not mistakes) |
| Muted text | `#7d776c` / `#817a6e` / `#898376` | descriptions, counts, meta |
| Hairline | `#d6d0c3` / `#d1ccbe` / `#cbc5b7` | borders, dividers |
| Border radius | `8px` cards/panels · `6px` buttons/inputs · `4px` icon buttons · `50%`/`999px` pills |

Type stack: **Manrope** (UI, weights 400–700) · **Libre Caslon Display** (serif: headings, prose, claims) · **DM Mono** (uppercase kickers, labels, counts, code). Kicker pattern: `font: 500|600 8–10px "DM Mono", monospace; text-transform: uppercase; letter-spacing: .06–.13em; color: #82533a or muted`.

## Page structure

- Shell: `.topbar` (sticky, blurred) → `nav` (Library / Brainstorm / Identity / Migration / Tools) → `main`.
- Page widths: content pages `main.page-documents` / `.page-migration` / `.page-identity` → `width: calc(100% - 24px); max-width: 1600px`. Narrow reading pages use bare `main` (1080px). Pick deliberately.
- Page header rhythm: kicker (mono, accent) → `h2/h1` (Libre Caslon 34px) → right-aligned muted description → hairline border-bottom → ~56–62px top padding. See `.identity-page-header`, `.operations`, `.section-heading`.

## Buttons (never style a bare `<button>`)

| Class | Look | Use |
| --- | --- | --- |
| `.ask-row button`, `.secondary-button` | solid `#82533a`, white, 6px radius, 11px bold | primary actions |
| `.secondary-button` variant | transparent bg, `1px solid #9c7965`, `#754831` text | secondary/toolbar |
| `.text-button` | borderless, muted/accent text | tertiary inline actions |
| `.record-card-actions` / `.entry-page-actions` button | 28px transparent icon square; hover `#f2eee5` + accent border + `#82533a` icon | the compact upper-right edit/hide/note icons (Romulus's edit button lives here) |
| `.identity-toolbar button` | outline toggle; `.active` fills accent | view-mode toggles |
| `.decision-button` | solid accent, slightly smaller than form primaries | commit actions (Create entity) |
| `.decision-button.outline` | outline variant that fills on hover | suggestion actions (Alias → name) |

Icon buttons pair with `RecordIcon kind="edit"|"hide"|"show"|"note"`; SVGs are stroked, `stroke: currentColor; stroke-width: 1.7`.

**AI-action wand:** every button that triggers a model call (drafting prose, extracting claims, retrying a failed extraction) leads its label with the magic-wand icon (`<WandIcon />`, `.wand-icon`) — AI involvement is visible before the click. Buttons without the wand never call a model. Documented in Help as the glossary entry "AI action (✨ wand)".

## Panels & cards

- Card: `1px solid #cbc5b7; radius 8px; background #fffefa; padding 22–26px` (`.identity-full`, `.operation-card` uses the tinted `#e9e6dc` variant).
- Queue/list panel: `#f0ede4`, hairline row separators, row hover `#f8f5ec` (`.migration-queue`, `.identity-compact-list`).
- Notices: `.notice` (warm error/announcement), `role="status"` paragraphs inside panels for receipts.
- Empty states: serif line + short explanation (`empty-state`, `identity-empty`).
- Records affordance (ADR-0015): every entry exposes the SAME under-the-hood control — one icon in the standard `entry-page-actions` slot, label "Records", opening the audit view (claims, states, authorities, provenance, supersession). Same icon, same slot, same label on every surface; consistency is the contract.
- Role chips (faction rosters): `.role-chip` pill; `.role-chip.leadership` tinted accent variant. The ★ suffix marks a unique leadership seat and is explained by the roster's legend line — the star renders only from `is_leadership`, never from text.

## Entry pages (characters, locations, encounters)

- `.document-view > header`: mono uppercase label left, `entry-page-actions` icon slot right.
- `.entry-hero`: kicker + Caslon 34px name + `<dl>` of metadata chips (`dt` mono 8px, `dd` 12px). Empty fields render nothing — hide, never stub.
- `.entry-section` grid (two-column, level-2 spans both), `.entry-summary` intro.
- `.entry-claims.canonical-record`: "Campaign record / Current information" claim groups with `.record-card-actions` per claim.
- `.source-drawer`: collapsed provenance footer.

## Forms

- `.form-grid`: auto-fit label+input grid, 14px gaps. Labels: mono uppercase 9px accent.
- Inputs/selects: `1px solid #c8bcac`, 4–5px radius, `#fffefa` bg; focus ring `#b58a72`/`#82533a`.
- Alias inputs: comma-separated; trim on blur, never per keystroke (the space-eating bug).
- Actions row: `.step-actions` — text Cancel left, primary right.

## Rules of thumb

1. Grep before you write CSS; name things by role (`identity-queue`), not appearance.
2. No button moves or resizes on hover or click — state changes are color-only (fill, border, or darkened accent). Never `transform` on interactive states.
2. One accent color, one serif, one mono — a new color needs a reason.
3. Icon actions go in the standard 28px slot, not new bars.
4. Empty means absent, not "—".
5. Every list gets a count line (mono, uppercase): "SHOWING 20 OF 129 UNRESOLVED SURFACES".
6. Workspaces never lose data (user ruling 2026-09-21): every working surface auto-persists its working file — the Lore queue item saves Entity Kind, AI direction, and Description with its evidence; a refresh or accidental navigation loses nothing. New workspace fields join the auto-save, never a manual save step.
