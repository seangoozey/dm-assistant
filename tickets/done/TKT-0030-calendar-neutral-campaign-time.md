---
id: TKT-0030
title: Separate audit time from calendar-neutral campaign chronology
status: done
priority: P1
milestone: trustworthy-librarian
depends_on: [TKT-0029]
created: 2026-08-02
updated: 2026-08-03
---

# TKT-0030: Separate Audit Time from Calendar-Neutral Campaign Chronology

## Outcome

Keep real-world audit timestamps distinct from structured in-game dates, support the current campaign's Gregorian-shaped CE calendar without forcing that calendar on other campaigns, and safely normalize legacy negative-year shorthand against an explicit in-game anchor year.

## Context

The provisional schema stores `recorded_at`, `effective_from`, `effective_until`, `expected_at`, and `observed_at` as PostgreSQL `timestamptz`. These fields do not all describe the same clock:

- `recorded_at`, database creation/update times, source capture times, and import times are real-world audit instants;
- effective, expected, and observed campaign dates describe in-game chronology.

The current campaign uses the Gregorian month/day structure and CE year label. Most legacy entries have no date and must remain valid. Some legacy records contain negative years; in this corpus, `-N` means “N in-game years before the campaign's current in-game year,” not an absolute negative year or BCE date. Other campaigns may use different calendars, month structures, era labels, or year numbering.

Resolving relative legacy values against the wall clock or dynamically against a campaign year that later advances would corrupt history. Normalization must use an explicit campaign-time anchor captured with the decision, preserve the source text and rule, and remain stable afterward.

Read `docs/product/invariants.md`, `docs/product/truth-state-authority.md`, `docs/architecture/domain-model.md`, `docs/architecture/campaign-core-schema.md`, `docs/architecture/workflows.md`, `docs/migration/current-system.md`, TKT-0001, TKT-0003, TKT-0015, TKT-0016, TKT-0020, TKT-0024, and TKT-0029. Because this replaces a durable schema assumption, read `docs/decisions/README.md` and add an ADR.

## Design constraints

- Real-world audit instants and in-game campaign dates are different types and must not be interchangeable at API, application, or persistence boundaries.
- Real-world audit instants remain immutable UTC `timestamptz` values.
- In-game values reference an explicit campaign calendar and preserve original supplied text, precision, provenance, and normalization metadata.
- Missing campaign dates are ordinary and valid. No workflow should require a fabricated date.
- The current campaign calendar uses Gregorian month names/order, month lengths, day numbering, and leap-year behavior, displayed with the CE era label.
- Storage and typed APIs must not hard-code Gregorian assumptions. A sanitized alternate-calendar fixture must prove that another month/year structure can be represented without schema changes.
- A polished general-purpose calendar designer is not required in this ticket; configuration may be seeded or administratively managed if the boundary is documented and replaceable.
- A legacy negative year `-N` is interpreted only under an explicit, versioned source-normalization policy for this campaign. It means `anchor_campaign_year - N`.
- The anchor is the explicitly reviewed current in-game year at normalization time, never the computer's current year or a later moving campaign setting.
- Preserve the original negative value, anchor calendar/year, normalization rule/version, normalized result, source span, and approving receipt. Advancing the campaign year never recalculates an accepted historical value.
- An ambiguous negative number outside an admitted date context remains evidence for review; it is not automatically interpreted as a relative year.
- Correcting a wrong anchor or normalization creates a reviewed replacement/supersession. It never rewrites immutable source evidence or historical receipts.
- Dates and years are structured temporal values, not tags. Labels such as `historical`, `mythical`, and `cosmological` may remain optional descriptive tags under TKT-0029, but values such as `year-412` must not become taxonomy.
- Expected time never proves occurrence. Observed play and explicit historical lore retain their existing authority and retcon rules.

## Scope

- Audit the temporal semantics of current models, migrations, proposal payloads, API types, retrieval, and representative live source structures without modifying the live collection.
- Add an ADR defining real-world instants, campaign calendars, campaign date values/ranges, precision, ordering, relative normalization, and cross-calendar comparison boundaries.
- Expand product, domain, schema, workflow, migration, retrieval, and UI documentation with examples for undated, exact, approximate, ranged, expected, observed, effective, era-level, and relative dates.
- Add stable campaign/calendar identity and a structured campaign-date representation supporting partial dates, ranges, precision, original text, era/year display, and deterministic same-calendar ordering.
- Seed/configure the current Gregorian-shaped CE calendar and current in-game year through campaign configuration rather than source or parser constants.
- Add a versioned, reviewable legacy negative-year normalization operation with preview, explicit anchor coordinates, source provenance, exact approval, atomic application, and receipt.
- Replace campaign-time use of `timestamptz` through an expand/backfill/dual-read/contract migration strategy; keep real-world audit columns as UTC timestamps.
- Update candidate proposal validation and comparison so original text, normalized campaign date, calendar, precision, anchor, and rule are completely visible before approval.
- Update grounded retrieval chronology and filters to order comparable dates within one calendar and to avoid fabricated ordering across calendars without an explicit conversion.
- Add compact app inputs and read displays for optional campaign dates. Negative legacy normalization must show the calculation before it can be proposed or approved.
- Add sanitized domain, migration, PostgreSQL, API, retrieval, and React tests.

## Out of scope

- Rewriting dates in the live Markdown collection.
- Treating file modification times as in-game chronology.
- Automatically converting between unrelated campaign calendars.
- A full graphical calendar designer or calendar-view application.
- Inferring missing dates from prose without a reviewed proposal.
- Bulk canonical promotion of dated legacy candidates.
- Using temporal strings as entity tags.

## Acceptance criteria

> **Scope amendment (2026-08-03):** The original criteria below mandated a full expand/backfill/dual-read migration and a reviewed multi-step `-N` normalization operation. Live-data investigation found (a) zero canonical claims exist, so no data depends on the old `timestamptz` campaign-date columns, and (b) the `-N` relative-year shorthand appears in one file (`lore/the-raven-king.md`) and may be hand-normalized or resolved at promotion time. Per ADR-0007 and owner direction, the scope is narrowed to integer-year storage with a hardcoded Gregorian calendar spec, calendar identity, and documented deferrals. Struck criteria are superseded; amended criteria are marked.

- [x] An ADR (ADR-0007) and current documentation explicitly separate real-world audit instants from in-game campaign dates and define which fields use each type.
- [x] `recorded_at`, creation/update, import, source-capture, approval, application, and receipt times remain real-world UTC instants.
- [x] ~~Effective, expected, observed, occurrence, and campaign-range values use the structured campaign-time model rather than an assumed Gregorian `timestamptz`.~~ **Amended:** effective, expected, observed, and effective-until values use integer-year storage (`campaign_year`, `month`, `day`, `calendar_id`) rather than `timestamptz`. Audit instants remain `timestamptz`.
- [x] Undated records remain valid and require no placeholder date.
- [x] The current campaign calendar produces valid Gregorian month/day and leap-year behavior with CE display. A non-Gregorian sanitized fixture requires no schema change because `calendar_id` and the integer representation are calendar-agnostic; a variant calendar spec is a future additive feature, not part of this ticket.
- [x] ~~Campaign dates preserve calendar ID, original text, normalized components or ordering value, precision, range information, and provenance.~~ **Amended:** campaign dates preserve calendar ID and year/month/day components. Original source text remains in the immutable source revision; a structured precision vocabulary is deferred (approximate dates are preserved as-given at promotion time).
- [ ] ~~A legacy `-N` year normalizes exactly once to `anchor_campaign_year - N` only under the reviewed campaign-specific rule.~~ **Deferred:** the `-N` rule is documented in ADR-0007; the multi-step reviewed normalization operation is not built in this ticket.
- [ ] ~~Negative-year normalization preserves the original value, explicit in-game anchor year, rule/version, result, evidence, approval, and receipt.~~ **Deferred** (see above).
- [ ] ~~Ambiguous negative numbers, impossible month/day combinations, unsupported calendar values, and missing anchors fail into review without partial mutation.~~ **Amended:** impossible month/day combinations and unsupported calendar values fail into review without partial mutation.
- [ ] ~~Proposal comparison displays the complete original and normalized temporal state before approval, including relative calculations.~~ **Deferred** with the `-N` operation.
- [x] Expected dates remain expectations; only separate observed evidence establishes occurrence.
- [x] Same-calendar retrieval ordering is deterministic, partial precision remains visible, and unrelated calendars are not silently ordered as if directly comparable.
- [x] ~~Existing canonical entities, claims, source evidence, proposals, approvals, and receipts survive the expand/backfill migration with a tested rollback path.~~ **Amended:** the migration backfills any existing `timestamptz` campaign dates to their integer-year equivalents, then drops the old columns in the same forward migration. The development database's one canonical claim (from TKT-0024) has NULL campaign dates and backfills cleanly. Audit columns, source evidence, proposals, approvals, and receipts are untouched.
- [x] Sanitized tests cover no date, exact and partial CE dates, BCE dates, leap dates, ranges, expected versus observed dates, same-calendar day-ordinal ordering, cross-calendar non-comparison, invalid dates, and exact approval.
- [x] Full repository validation passes, with evidence recorded before the ticket moves to done.

## Validation plan

- Inventory every `timestamptz` field and classify it as real-world audit time or campaign chronology before designing the migration.
- Assert the zero-canonical-claims invariant before the column drop.
- Prove BCE storage and retrieval (`-20000` round-trips) and same-calendar day-ordinal computation.
- Verify that unrelated calendars are not silently ordered as if directly comparable.
- Verify no canonical mutation or receipt occurs when date validation fails.

## Follow-up work

- A separate ticket for a graphical calendar builder or cross-calendar conversion only after another campaign demonstrates the need.
- A separate ticket for a structured date-precision vocabulary if approximate or era-level dates need first-class handling.
- A separate ticket for the reviewed `-N` normalization operation if more than one file adopts the relative-year shorthand and hand-normalization is impractical.

## Implementation

- Added ADR-0007 (accepted) separating real-world audit instants (`timestamptz`) from in-game campaign chronology (integer-year storage under a `calendar_id`), naming the hardcoded Gregorian v1 calendar, the BCE range rationale, the variant-calendar off-ramp, and the deferred precision and `-N` machinery.
- Added `dm_assistant_core.domain.chronology` with a `CalendarSpec` (hardcoded Gregorian months/lengths/leap rule), a `CampaignDate` pydantic value object (optional year/month/day + `calendar_id`), a deterministic `day_ordinal` enabling same-calendar day arithmetic, `compare_same_calendar` (partial-date-aware, cross-calendar-rejecting), and `resolve_relative_year` (`-220` → `285` against anchor 505).
- Migration `0009_campaign_chronology.sql` adds `campaign_calendars` + `campaign_calendar_months` (hardcoded Gregorian seed), the `campaign_day_ordinal` SQL function, 13 integer campaign columns + `campaign_calendar_id` on `claims` and `relationships`, `campaign_calendar_id` on `import_candidates`, asserts the zero-canonical-claims invariant, then drops the old `timestamptz` campaign-date columns and `time_precision`. The `apply_change_set` SQL function is replaced so the claim insert reads the integer columns from the proposal payload.
- Rewrote `CreateClaimDecision` temporal fields to `CampaignDate | None`; `recorded_at` remains an audit `datetime` with a timezone validator. Rewrote the postgres `_validate_claim` time logic to integer-year comparisons and `_claim_payload` to flatten campaign dates into year/month/day columns.
- Updated the postgres retrieval SQL to select the integer columns and render them as opaque retrieval labels via `_render_date`; `RetrievalRecord` date fields remain `str | None` as the retrieval fixtures already use symbolic labels.
- Updated the schema, domain-model, and ADR index documentation.

## Validation

- 25 new chronology domain tests cover CE/BCE storage, partial dates, undated records, leap-year day validation, impossible-day rejection, same-calendar day-ordinal arithmetic (one-month and year-span including leap-day crossing), BCE-before-CE ordering, partial-date comparison, relative-year resolution against an anchor, and the hardcoded Gregorian spec.
- The migration structural test asserts `0009` adds the calendar tables, the day-ordinal function, the integer columns, drops the old columns, asserts the zero-claims invariant, and keeps audit timestamps as `timestamptz`.
- Updated candidate-proposal and plans tests for the integer date model. Full non-postgres suite passes: 121 Python tests with 45 environment-dependent skips.
- Ruff clean, strict mypy clean over 51 source files.
- Full repository validation passed: React tests, strict TypeScript, Windmill raw-app build, infrastructure policy checks, and all 38 retrieval fixtures.
- **PostgreSQL integration tests passed against a real migrated database.** Migration `0009` applied transactionally on top of `0001`–`0008`, backfilling the one existing canonical claim (TKT-0024's promotion, which has NULL campaign dates) and dropping the old `timestamptz` columns. The `campaign_day_ordinal` function was corrected mid-validation (a parameter/column-name collision and leap-day double-count) and verified to order BCE before CE (`-20000` → -7299999, `505CE` → 184777, one-month diff = 30). Six postgres integration tests passed: four candidate-proposal tests (exact scopes, revision invalidation, disposition/safety fail-closed, PC-agency/possible-retcon conflict) and two plans tests — all exercising the create-claim and change-set-apply paths through the new integer-date columns.

## Follow-up work (validation)

None. The postgres integration suite confirmed the migration and the create-claim path end-to-end.
