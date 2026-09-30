---
id: TKT-0146
title: Description claim breakpoints — the :: authoring notation and the candidate builder
status: done
priority: P2
milestone: trustworthy-librarian
depends_on: [TKT-0136]
created: 2026-09-24
updated: 2026-09-28
---

# TKT-0146: Description claim breakpoints — the `::` authoring notation and the candidate builder

## Context

The Description surface redesign (ADR-0018 amendment 2026-09-24) ruled that a description is an ordered collection of claims — the prose is the reading layer, never split mechanically per sentence. The open question was the split unit: sentences are the wrong delimiter ("one sentence can carry two assertions; three can carry one"). Sean's mechanism ruling (2026-09-24): the author marks claim breakpoints in the prose with a special character — **`::`** — and the candidate builder allows editing and regrouping during review. Tested against the real Far Realm Entity prose: `::` breaks yield **9 assertion-shaped claims versus the sentence splitter's 14 fragment rows**, with narrative glue staying glue.

The description review itself (Sean's clarified model after the mis-build of 2026-09-24): rows derive FROM THE PROSE (rebinding ownership of other claims here is not the point — gathered claims stay references in the panel); rows are editable during the stage; Approve promotes the claims AND tags them as the ordered list that makes up the description, stored ON THE DOCUMENT — behaving like the Dossier except the Description is a COLLECTION of claims rather than one claim per card. The description text itself is never promoted.

Note: the mis-built claim-composition UI (gathered-claims rows + Own checkboxes) must be reverted as part of this build.

## Scope when taken up

- **Marker derivation**: when the prose contains `::`, split ONLY on markers (exact author intent — no sentence fallback mixed in). No markers → **no breaks**: the review opens with one whole-prose row (Sean's ruling over coarse fallback), and the author returns to the prose to add breaks. The unit is the assertion, not the sentence.
- **The candidate builder's regroup ops** (four, in review): edit text; **merge with the row below** (glue case); **split a row** (one group carrying two assertions); drop. Row order = the ordered list. No long-distance merging (breaks prose correspondence).
- **Storage and rendering**: the prose files VERBATIM with markers (the authored revision surface — Revise later needs the breakpoints back); render strips `::` so the reading layer never shows them. The document's ordered claim list is the real structure (Dossier-like collection).
- **Live feedback**: a claims-detected counter under the textarea ("N claims detected"), so marker state is visible without review.
- **Commit**: claims created from rows (edited text = the claim text, author from the surface), the description document filed with the ordered claim ids, prose stored with markers, rendered stripped. No statement-splitting derive for the description surface; the existing derive endpoint remains Lore-only.
- **Staleness behavior**: prose edits after review regenerate rows WITH A WARNING (no silent edit preservation — diff-based preservation is future work if the toil shows).
- **AI drafting integration** (prompt rule: place `::` between assertions) so machine drafts arrive pre-broken in the same notation. The broader assistant question — an AI that could SUGGEST breakpoints — is ruled a later date (Sean: "an AI couldn't help automate breakpoints. That's for a later date").

## Out of scope

- Ownership re-binding in the description review (not the point — Step 1 and the Lore surface own that).
- AI breakpoint suggestions.
- Diff-based edit preservation across re-derives.

## Validation evidence

(to record when built; the :: split test on the FRE prose — 9 groups vs 14 sentence rows — is the motivating evidence)

### DELIVERED 2026-09-24 — :: breakpoints live on the Description surface

- **Marker derivation** (`splitClaimGroups`): `::` present → split ONLY on markers; no markers → **one whole-prose row** (no-breaks fallback, Sean's ruling). Live counter under the textarea ("N claims detected" / "No claims detected — add :: …").
- **The candidate builder** (`DescriptionClaimReview`): rows from the prose with the four regroup ops — edit (textarea per row), **merge into the claim above**, **split at the caret** (sentence-boundary fallback), **drop** — plus move-up/down for ordering and per-row Truth State (Established/Considered/Prepared). Row order = the ordered list. The mis-built gathered-claims+Own UI is fully reverted.
- **Commit**: through the promotion facade (`approvePromotion`) — claims created from rows, description filed with the ordered claim ids, prose stored verbatim with markers; the fork-guard retry (moved page path → file fresh) retained. Render stripping of `::` happens at display (the synthesized/document render strips marker text).
- **Autosave (ADR-0019's first surface)**: prose AND in-flight review rows persist to localStorage continuously per entry (`dm-assistant.descriptionWork.{id}`); reopening shows a Restore/Discard banner ("Working file restored — nothing was lost"); the working file clears on successful commit. The notepad-file distrust condition is addressed.
- **AI drafting**: prose prompt gains rule 7 (place `::` between separate factual assertions; sparingly — connective prose joins the preceding group; rhetoric ends without a marker); prompt version bumped to prose/4.
- **Evidence**: React 144/144 (breakpoint derivation + counter; merge/drop regroup with the merged claim text asserted; revision carrying document_id; fork-guard filing fresh; backend suite 514 passed incl. prose tests on prose/4). Deployed.

Remaining polish (follow-ups): diff-based edit preservation across re-derives; render-strip of `::` verified only in the document render path — authored-page revisions keep markers by design.

### Hotfix (2026-09-24): commit payload carried a non-contract field

`sequence` isn't part of PromotionStatementInput — FastAPI 422'd the whole commit (the error surfaced through the windmill bridge as "Extra inputs are not permitted"). Removed; React 144/144; redeployed.

### Hotfix 2 (2026-09-24): rows sent zero-based spans → overlap rejection

The :: flow's rows had no prose offsets, so every statement sent span (0, len(row)) — all overlapping, rejected by the overlap guard. Fixed: rows now carry their TRUE prose span from the marker split (sequential, non-overlapping by construction); merge takes the union of the two spans; split divides the span proportionally at the caret. The span is the filed candidate's provenance (raw prose text), while the row's edited text remains the canonical assertion — the designed split. React 144/144; redeployed.

### Hotfix 3 (2026-09-24): pre-hotfix restored rows lacked spans

The user's working file was saved before the span-tracking hotfix, so its restored rows had no spanStart/spanEnd — JSON.stringify omitted them and FastAPI required them. Commit now re-derives sequential spans for any row missing them (anchored on the row's first word in the prose) before sending. React 144/144; redeployed.

## Closed 2026-09-28

Delivered 2026-09-24 including all three live-commit hotfixes (contract-only payloads; true prose spans through regroup ops; commit-time span re-derivation for pre-hotfix autosaved rows). `::` marker-only split with NO-BREAKS fallback, regroup ops (edit/merge/split-at-caret/drop/move), prose stored verbatim with markers, and ADR-0019 autosave on its first surface. Follow-up AI breakpoint suggestions were noted as a later date; the duplicate-check assistant landed separately under TKT-0137 (Description dedup, 2026-09-27).