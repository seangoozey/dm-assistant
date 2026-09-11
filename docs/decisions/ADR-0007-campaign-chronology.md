# ADR-0007: Campaign Chronology as Integer-Year Values with a Calendar Spec

- Status: accepted
- Date: 2026-08-03

## Context

The schema stored in-game dates (`effective_from`, `effective_until`, `expected_at`, `observed_at`) as PostgreSQL `timestamptz`, conflating two different clocks that only look alike:

- **Real-world audit instants** — `recorded_at`, created/updated, import, source-capture, approval, application, and receipt times. These are correctly immutable UTC `timestamptz` values and remain so.
- **In-game campaign chronology** — effective, expected, and observed dates that describe events in the fictional world's calendar. These were never real-world moments.

Treating campaign chronology as `timestamptz` is a type error that only appeared to work because the current campaign happens to be Gregorian-shaped. It breaks on real data: `timestamptz` floors at 4713 BC, but `lore/timeline.md` carries canonical player-facing lore at `20,000 BCE` and `15,000 BCE` (the Titans, the Oracle Merghana, the Age of the Golden Dawn). Those values cannot be stored in a `timestamptz` column at all.

The retrieval layer already treats campaign dates as opaque strings (`day-18` in the acceptance fixtures), confirming that the domain model never required timezone-aware instants for in-fiction time. The live import created only non-canonical candidates carrying assertion prose, with zero structured campaign dates and zero canonical claims, so no data depends on the old columns.

The campaign also needs to answer "how many days has it been since X" against a calendar with twelve months of varying day counts. That requires the month structure and leap rule to be defined and queryable, not just a year integer.

## Decision

Separate the two clocks at the persistence boundary.

- **Audit instants** stay immutable UTC `timestamptz`. This is unchanged.
- **Campaign chronology** is stored as integer components: `campaign_year integer`, `month smallint`, `day smallint` (all nullable for partial dates), and `calendar_id text`. A BCE value is a negative integer (`-20000`), with no range cliff.
- A **hardcoded Gregorian calendar spec** defines the twelve-month structure, month lengths, and leap-year rule for the `gregorian-ce` calendar. It is durable enough to compute a deterministic day-ordinal within one calendar, which makes "how many days since X" answerable.
- `calendar_id` is carried on each dated record and defaults to `gregorian-ce` through campaign configuration, never parser constants. A future campaign using a variant calendar is an additive feature — a new spec and a new `calendar_id` — not a rewrite of existing data.
- **Day-arithmetic and ordering are valid only within one `calendar_id`.** Two records under different calendars are never silently ordered or subtracted as if directly comparable; cross-calendar conversion is an explicit future operation.
- Approximate dates (for example `~290CE`) are preserved as given at promotion time. A structured precision vocabulary is a deliberate later version, not part of this decision; nothing is silently flattened in the meantime.
- Legacy relative-year shorthand (for example `-220` in `lore/the-raven-king.md`, meaning "220 in-game years before the current in-game year") resolves once against an explicit anchor year (the campaign's current in-game year, `505CE`) and is stored as the resulting absolute year. The original relative value, anchor, and rule are preserved in source text and receipts, not in the date column.

## Consequences

- BCE and CE years store and order natively; there is no storage cliff.
- "How many days since X" is answerable within the Gregorian campaign via a deterministic day-ordinal backed by the calendar spec.
- Audit time and campaign time are distinct types at the API, application, and persistence boundaries; they cannot be accidentally interchanged.
- Integer-year storage is the most reversible representation for a future variant-calendar version: a migration reads the integers back and reinterprets them under a new calendar model, with no timezone semantics to undo.
- A DM-managed or graphical calendar designer is out of scope for this version; the calendar spec ships hardcoded and is extended by code and forward migrations.

## Alternatives considered

- **Keep `timestamptz`:** rejected. The 4713 BC floor is a hard storage limit that the canonical timeline exceeds, and timezone semantics are meaningless for in-fiction dates.
- **`bigint` epoch (days/seconds since an epoch):** rejected. It loses the year/month/day structure the calendar spec needs for display and day-ordinal computation.
- **JSONB date column plus a generated sort ordinal:** rejected. It weakens type safety at the persistence boundary and pushes calendar correctness onto generated-column logic rather than a named spec.
- **Expand/backfill/dual-read/contract over multiple releases:** narrowed to a single forward migration because zero canonical claims exist, so no data depends on the old columns. The zero-claims invariant is asserted in the migration test.
