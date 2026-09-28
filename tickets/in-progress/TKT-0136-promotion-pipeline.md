---
id: TKT-0136
title: Promotion Pipeline — reusable Proposal → Candidate → Claim review and commit
status: in-progress
priority: P2
milestone: trustworthy-librarian
depends_on: []
created: 2026-09-20
updated: 2026-09-21
---

# TKT-0136: Promotion Pipeline — reusable Proposal → Candidate → Claim review and commit

## Context

Sean's ruling (2026-09-20): build one reusable progression for turning working material into canon, serving every surface that consumes it — initially Description filing, Lore creation, and Brainstorm promotion, with the surface set expected to grow (new surfaces join by declaring ownership model, defaults row, derivation rule, bundle suffix) — plus a repair intake for in-app material that was written but never promoted correctly. Key constraint: **user ease** (the DM touches only what is wrong). The Migration wizard solved this class for imports with poor results (sequence-as-navigation, structure-as-gate, per-claim form grids, approval ceremony); the direct session reviewer proved the better pattern. Framework: `docs/architecture/promotion-pipeline.md`; decision record: ADR-0018 (proposed). Shaping rulings locked: compact scan-able candidate list, "Approve promotion" commit verb, name "Promotion Pipeline", and the **ownership-model distinction**: Description/Lore are bound-subject (owner implicit — existing for Description, created by the commit for Lore); Brainstorm is free-subject (no owner, many Entities existing or new) and carries machinery intrinsic to it.

## Scope when taken up

- **Backend facade** (`campaign-core/src/dm_assistant_core/application/promotion.py`):
  - `derive(surface, proposal_refs, hints)` → candidate list: assertion text, subject (inherited for bound surfaces, required resolution for free), defaulted Truth State, provenance, mechanical consequence (new / moves from / replaces), conflict flags (current detectors only — verified-death temporal + deterministic checks; free-text semantic contradiction is out of scope), deterministic-check results. A read.
  - `approve_promotion(payload, idempotency_key)` → single-action binding transaction: build immutable proposal version, bind approval to exactly that version + items, apply (entities, claims, re-attributions, supersessions, documents), receipt — reusing change_sets / candidate_proposals internals, no new canonical mutation route.
  - Server-side defaults per the framework's defaults table (authority, visibility, confidence, conditionality, recorded_at, dates). The 20-field `CreateClaimDecision` is assembled server-side.
  - Free-subject support: records created inside a commit are referenced by bundle-local key (`{"new_record": "r1"}`), resolved to UUIDs server-side within the transaction; one commit may create several records.
- **Promotion Review list component**: compact scan-able rows — all approvable elements at a glance (text, subject, state chip, provenance cite, consequence/flag line), inline fixes, one expandable dimensions disclosure per candidate, one "Approve promotion · N claims [+ bundle]" button; receipts and failures into the toast/Log bus. UI tokens per ui-conventions; no wizard chrome. Renders the ownership model: bound surfaces show the owner as page context; free surfaces show a required subject chip per row and NEW RECORD rows grouping claims beneath them.
- **Surface adoption** (each slice adds exactly one mechanism):
  1. Description — bound-subject, existing owner; citation mirrors and novel statements (simplest commit path)
  2. Lore — bound-subject, owner created by the commit; adds re-attribution and new-record bundle
  3. Brainstorm — free-subject; adds per-candidate subject resolution, NEW RECORD rows, multi-record bundles (the machinery intrinsic to Brainstorm; the same machinery later serves session-note statements and the Migration claim step)
- **Repair lane**: standing unpromoted-material audit (entities with zero claims but authored documents; unpromoted brainstorm thoughts; direct captures with pending statements) surfaced as a Tools-panel review that reopens stalled artifacts as proposals; *replaces claim #Z* consequences commit through supersession receipts.
- **Glossary**: "Promotion Pipeline" entry lands with the component (test-enforced registry rule).

## Out of scope

- Migration wizard rework (steps 3–6 collapse into this component under TKT-0131, separately).
- Durable pending-proposal queues for ephemeral surfaces (rejected in ADR-0018).
- Any AI seam beyond the four fixed ones; AI never gates or executes commit.
- General semantic conflict detection — free-text contradiction (e.g. "ugly" vs "cute") is not detected and the flag must never be worded as if it were; widening detection (structured Attribute domains, an optional AI review seam) is future work, tracked separately when ruled in.
- TKT-0040's conflict-gated lore application specifics (the pipeline surfaces conflicts inline; 0040 remains its own track).

## Validation evidence

**Slice 1 delivered 2026-09-21 — backend facade + Promotion Review list + Description adoption.**

Backend (`campaign-core`):
- `application/promotion.py`: `derive` (deterministic statement split, defaults from `SURFACE_REGISTRY`, reference-mirror marking, narrow conflict pre-check) and `approve_promotion` (single-action binding: file description with statement-span candidates → create-or-revise proposal → approve with version-derived idempotency key → apply change set; convergent retry via the stored-change-set replay path).
- `entity_descriptions.py`: `statement_spans` on the command — only approved statements become reviewable candidates (no Migration-queue residue); receipt returns ordered `candidate_ids`.
- Conflict gate shared: `assertions_require_conflict_review` moved from the postgres adapter to `application/candidate_proposals.py` so preview and commit agree.
- **Latent CTS bug fixed on the way**: the Considered truth state could not commit at three layers (missing `ClaimState.CONSIDERED` domain enum member, no `("considered","brainstorm")` coordinate pair, brainstorm UI authority map lacked `considered`) — all fixed; PC-subject check now permits considered as the mildest planning state.
- API: `POST /promotion/derive`, `POST /promotion/approve` (DM-only; readable 422/409 errors).

Tests:
- Unit `tests/test_promotion.py` 12/12 (splitter offsets, mirror-vs-mention, overlap-gate narrowness incl. ugly/cute, derive reference/conflict marking, document-only commit, full-chain commit, revise convergence, state-not-offered, stale-span errors).
- Integration `tests/test_promotion_postgres.py` 2/2 in the docker harness: full derive→approve→apply chain against real Postgres with idempotent replay (2 claims, established/explicit_lore, correct subject) and reference-mirror exclusion.
- Suite: 510 passed (one pre-existing failure unrelated to this ticket: `test_boundaries.py::test_canonical_table_writes_exist_only_in_migrations` — TKT-0099's `claim_reattribution.py` writes canonical tables outside a migration-owned function; flagged to Sean, fix belongs to the 0099 track).
- React 138/138 incl. the new promotion review test (on-demand derive never automatic; locked reference rows; consequence at a glance; commit payload excludes references; receipt toast).

UI:
- `PromotionReviewList` component embedded in the Description composer: scan-able rows (assertion inline-edit, Truth State select for new claims, consequence line, conflict flag with honest "known conflict" wording, provenance), staleness guard (prose changed → review again), one "Approve promotion · N claims + description" button (falls back to "File description" at N=0); plain "File description" path preserved.
- Glossary: "Promotion Pipeline" entry landed (registry rule).
- Live verification on the deployed stack: bridge + Core derive exercised end-to-end in the browser (2 candidates derived from prose on a real entry, Established defaults, consequence lines, commit label); no commit clicked — that would have written real claims.

Remaining slices (not started): **remove the plain "File description" bypass — statement review becomes mandatory** (user ruling 2026-09-21: claims-from-prose opt-in is a compliance violation; every statement gets an explicit include-or-exclude decision, ADR-0018 point 8); Lore adoption (bound-created owner + re-attribution consequences); Brainstorm adoption (free-subject machinery, NEW RECORD rows, multi-record bundles); repair lane + standing unpromoted-material audit; Migration steps 3–6 collapse (TKT-0131).

### Fix: unpaged NPCs had no Write Description button (2026-09-21, deployed)

Sean reported Osirus (NPC, only lore-doc mentions, no sheet and no authored page) lacked the button. Root cause: entries with no matched page render a SYNTHESIZED stand-in document, which carries `type: npc` frontmatter — so the character view branch took over, and that branch never offered the write-description affordance (only "Edit NPC page"). Unpaged characters are exactly the entries that need the affordance. Fix: the synthesized-character branch passes `onWriteDescription` (same unpaged RecordIcon button as the templated view), and the Description composer now renders in that branch with the same save lifecycle (document list refresh before entry reload). Verified live on Osirus: button present, composer opens. React 139/139.

### Known limitation from live use (2026-09-21): paraphrase blindness in mirror + duplicate checks

The Osirus description review showed the reference-mirror detector (term overlap ≥ 0.5) missing every paraphrase of a gathered claim — all six statements derived as "new claim" though most restated the three references. The commit-time same-subject duplicate check shares the blindness (needs matching predicates or near-identical term sets), so approving such a list creates near-duplicate claims against ADR-0015's "one source saying it, never two." Deterministic mitigation is limited by design (per consequence≠conflict); the planned path is TKT-0137's AI restatement suggestions (marked, DM-confirmed). Until then: the review list is the dedup check — scan restatement consequences manually when prose was drafted from gathered claims.

### Slice 2 delivered 2026-09-21 — Lore adoption + mandatory-review cutover

**Lore surface (bound-created owner, no bypass from day one):**
- `SURFACE_REGISTRY` gains LORE (ownership BOUND_CREATED; Established/explicit_lore defaults; evidence-bounded state overrides). Derive needs no entity: statements mirror against the CONSIDERED set (the surface's references), no existing-claims pre-check (the record does not exist); commit-time validation covers the created record.
- `approve_promotion` (lore): mint the owner through the receipted, idempotent identity-queue path (`{key}:entity`; name-collision falls back to the existing record — the partial-prior-attempt case), file the description with statement candidates, propose/approve/apply claims bound to the new entity, then **re-attribute every linked claim** to it (idempotent: already-belongs counts as moved; other move failures collect into `move_errors`, never fatal). One action, one combined receipt (`claims_committed`, `moved_claim_ids`, `move_errors`).
- UI: the Lore working page's Create is now **"Review promotion — create {name}"** — derive, scan the list (Considered = references; linked = moves), commit via **"Approve promotion · N claims + new {kind}"**. Considered/linked ride along as real claim UUIDs (graph prefixes stripped). The direct create/verify/write/re-attribute client path is deleted.
- EntityCreator/reattribution wired into the facade via the identity queue + ClaimReattributionService; reads gain `entity_id_by_canonical_name`.

**Mandatory-review cutover (ADR-0018 pt 8):**
- The Description composer's unreviewed "File description" path is REMOVED — statement review is the only path. The fork-guard (moved page path) moved into the promotion commit: a revision whose path moved retries as a fresh description within the same promotion key. The 0-claim review outcome still files the document through `approve_promotion` (everything excluded by explicit review ≠ bypass).

**Evidence:** unit 12/12 (extended); docker-harness integration 3/3 (new lore test: entity mint + 2 claims + linked claim moved + idempotent replay, all asserted in the DB); React 139/139 (lore create drives derive+approve with correct payloads and NEVER calls the direct write paths; the three description tests rewritten onto the reviewed path incl. revision-with-document_id and fork-guard); live Core endpoint verified (lore derive returns bound_created + candidates). Live UI click-through was blocked by the automation browser's windmill login session after the server restart — covered instead by the React suite.

Remaining: Brainstorm (free-subject machinery, NEW RECORD rows, multi-record bundles); repair lane + standing unpromoted-material audit. "Stable promotion" gates TKT-0140 after Brainstorm lands.

### Slice 3 delivered 2026-09-21 — Brainstorm adoption (free subjects)

- **BRAINSTORM surface** (ownership FREE; Considered/brainstorm defaults; state overrides considered|possible→brainstorm, established→explicit_lore, intended→npc_intention, prepared→preparation): derive needs no entity — candidates read "new claim — subject required".
- **`approve_promotion` (free)**: statements are thought candidates, each carrying its reviewed subject — `{entity_id}` or `{new_record, name, kind}` bundle keys. New records mint once per key through the idempotent identity path (several statements can share one record; per-record mint keys keep retries convergent). The proposal binds to the brainstorm workflow session — required, because state-strengthening beyond brainstorm authority keys on the brainstorm_thoughts exception. No document is filed. Convergence: create-fails → get_for_candidate → revise (covers "brainstorm already has a promotion proposal" on re-prepares).
- **UI**: the drafts panel IS the review (flow-surface idiom stands). Each included thought resolves its subject: the record select now lists existing records, records this promotion will create (shareable across thoughts), and "➕ Create new record…" (name + kind inputs inline, dashed new-record row). "End brainstorm and prepare proposal" is REPLACED by one **"Approve promotion · N claims + M new records"** button committing everything, then closing the session with the applied proposal. The latent Considered-can't-commit UI bug (draft state type + authority map lacked it) is fixed by construction — the facade derives authority from state overrides. Draft seeding now defaults to Considered per the CTS defaults table.
- **Evidence**: unit 15/15 (three new free-surface tests: subject/candidate validation, unoffered state, per-record minting + workflow threading + shared new-record grouping); docker-harness 4/4 (new brainstorm chain: REAL brainstorm session, two thought candidates — one existing-record subject, one new record — claims + minted faction asserted in the DB, proposal bound to the session); React 140/140 (one-action promotion test: per-row subjects, new-record creation + sharing, correct payload incl. candidate bindings, close-with-proposal); live Core derive verified (free ownership, subject-required consequences, Considered defaults).

Remaining: repair lane + standing unpromoted-material audit. After that, stable promotion gates TKT-0140.

### Slice 4 delivered 2026-09-21 — Repair lane + standing unpromoted-material audit

- **Core**: `application/unpromoted_audit.py` + Postgres reads + `GET /campaign/unpromoted-material` — three finding kinds computed live (never stored as truth): `empty_shell` (entity with an authored entities/{slug}.md page and zero current claims — the pre-pipeline descriptions), `pending_capture` (direct-input documents with statements still pending review), `unpromoted_thoughts` (brainstorm sessions with never-promoted thought candidates). Capped at 100 per kind, re-runnable.
- **Tools panel**: "Unpromoted material" section above the link audit, each finding routing to its repair lane through the guarded editor-switch: empty shell → open the entry (revise its description through promotion review), pending capture → open the document (statement review), unpromoted thoughts → open Brainstorm. Correcting already-promoted claims stays in the existing receipted supersession lanes (claim correction / 0097) — the audit finds and routes; every fix is a reviewed door.
- **Evidence**: harness 5/5 (new test seeds a real empty shell — entity + authored page + a filed-but-unpromoted statement — and asserts both the shell and the pending capture surface); React 141/141 (panel renders all three kinds with their routing actions); **live run on the real campaign: 1 empty shell (Nero), 5 pending captures, 1 unpromoted brainstorm** — real findings, first run.

**All four slices delivered.** Description, Lore, Brainstorm adoption; mandatory statement review on every surface; the standing repair lane. "Stable promotion" is now real — TKT-0140's library campaign is unblocked. Ticket left in-progress for Sean's review before closing.

### Description surface redesign: claim composition (Sean's ruling, 2026-09-24, deployed)

Live-use ruling from the Far Realm Entity work: the description is **a special grouping of claims** — the review lists the gathered CLAIMS as an ordered composition, editable inline; the prose is the reading layer and NEVER splits into claims ("a claim for every sentence is wasteful and degeneration prone"; free blobs unsupported, extending the Summary judgment). Delivered:
- `DescriptionClaimReview` replaces the statement review on this surface: rows = the checked gathered claims in gather order (wording editable, Own checkbox, owner labels incl. "no owner" for orphans).
- Commit sequence per row: edited wording → receipted correction (supersession via the existing claim-correction path, the replacement id takes the slot); Own + not-owned → re-attribution/initial attribution to the entry; then `writeEntityDescription` files the doc with the FINAL ORDERED claim list (corrections and moves applied). No derive/approve_promotion calls on this surface; statement-splitting derive remains Lore-only.
- The disabled-button cause was the stale check (prose edited after review disabled the statement flow) — moot under the composition flow, where prose edits don't invalidate the claim list.
- React 144/144 (composition test: own-marking defaults by ownership, edit→correction→replacement-id ordering, unowned→re-attribute, doc files the final ordered ids, derive/approve never called; the three legacy description tests rewritten onto the flow).
