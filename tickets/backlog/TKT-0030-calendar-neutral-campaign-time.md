---
id: TKT-0030
title: Separate audit time from calendar-neutral campaign chronology
status: backlog
priority: P1
milestone: trustworthy-librarian
depends_on: [TKT-0029]
created: 2026-08-02
updated: 2026-08-02
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

- [ ] An ADR and current documentation explicitly separate real-world audit instants from in-game campaign dates and define which fields use each type.
- [ ] `recorded_at`, creation/update, import, source-capture, approval, application, and receipt times remain real-world UTC instants.
- [ ] Effective, expected, observed, occurrence, and campaign-range values use the structured campaign-time model rather than an assumed Gregorian `timestamptz`.
- [ ] Undated records remain valid and require no placeholder date.
- [ ] The current campaign calendar produces valid Gregorian month/day and leap-year behavior with CE display while a non-Gregorian sanitized fixture requires no schema change.
- [ ] Campaign dates preserve calendar ID, original text, normalized components or ordering value, precision, range information, and provenance.
- [ ] A legacy `-N` year normalizes exactly once to `anchor_campaign_year - N` only under the reviewed campaign-specific rule.
- [ ] Negative-year normalization preserves the original value, explicit in-game anchor year, rule/version, result, evidence, approval, and receipt; later campaign-year changes do not alter the result.
- [ ] Ambiguous negative numbers, impossible month/day combinations, unsupported calendar values, and missing anchors fail into review without partial mutation.
- [ ] Proposal comparison displays the complete original and normalized temporal state before approval, including relative calculations.
- [ ] Expected dates remain expectations; only separate observed evidence establishes occurrence.
- [ ] Same-calendar retrieval ordering is deterministic, partial/approximate precision remains visible, and unrelated calendars are not silently ordered as if directly comparable.
- [ ] Existing canonical entities, claims, source evidence, proposals, approvals, and receipts survive the expand/backfill migration with a tested rollback path.
- [ ] Sanitized tests cover no date, exact and partial CE dates, leap dates, ranges, approximate/era dates, expected versus observed dates, custom calendars, relative negative years, fixed anchors, campaign-year advancement, invalid dates, ambiguity review, exact approval, idempotent retry, and rollback.
- [ ] Full repository validation and isolated PostgreSQL restore/migration tests pass, with evidence recorded before the ticket moves to done.

## Validation plan

- Inventory every current `timestamptz` field and classify it as real-world audit time or campaign chronology before designing the migration.
- Exercise expand/backfill and rollback against a disposable restore of the current campaign database; verify the existing entity, claim, receipt, source evidence, and parser/import ledgers remain intact.
- Use sanitized calculations with a fixed anchor—for example, anchor year `1500 CE` plus source year `-200` yields `1300 CE`—and prove the stored result remains `1300 CE` after the configured current campaign year advances.
- Verify that a negative value in ordinary prose is not normalized unless the source span and parser rule establish it as a date.
- Verify the same API and database structures represent both the current Gregorian-shaped CE calendar and a synthetic non-Gregorian calendar.
- Verify no canonical mutation or receipt occurs when date validation, normalization, comparison, or approval fails.

## Follow-up work

- Create a separate ticket for a graphical calendar builder or cross-calendar conversion only after another campaign demonstrates the need.
