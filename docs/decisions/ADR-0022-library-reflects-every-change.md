# ADR-0022: The Library Reflects Every Change — No Refresh Required

- Status: accepted (user ruling 2026-10-02, from the Ishirala Tower mint: the new encounter entity did not appear in the Library until a site reload)
- Date: 2026-10-02

## Context

Minting an encounter entity (an audited canonical write with a receipt) left the Library's entry list stale — the new record appeared only after a full site refresh. The Library is the app's index of records; a user who just created something and cannot see it has no reason to trust that it happened. Refresh-scavenging is also invisible work the user should never be asked to do.

## Decision

**Every canonical change the UI makes is reflected in the Library (and the affected derived views) in the same interaction — the user is never required to refresh the site.**

1. Every mutating action — entity creation (mints, Lore creation), ownership assignment and re-attribution, dispositions, claim commits, corrections, vocabulary changes — refreshes the library index on success, alongside whatever surface-local lists it already updates.
2. The refresh is part of the action's success path, not a user step: receipts and refreshed state land together; failures surface as errors and never leave a stale success state.
3. New surfaces inherit this by default: a mutation that does not refresh its affected reads is incomplete (the same standing-rule status as ADR-0019's autosave — build it in the first cut, never retrofit).
4. Derived read refreshes are best-effort-after-commit: a refresh failure never rolls back or casts doubt on the canonical write (the receipt remains authoritative), but it MUST surface as an error rather than passing silently.

## Consequences

- The app keeps a single shared library-refresh path; mutating surfaces call it on success (the orphan review's assign/mint/dispose actions, Step 1's Assign Ownership, Lore creation, session-note commits — the latter two already complied).
- Refresh cost is one list read per action; where an action mutates many records (batch assigns), one refresh after the batch, not per claim.
- The rule is about DERIVED views catching up with canonical truth; it does not add subscriptions/websockets — a read-after-write refresh satisfies it. If the app ever grows multi-tab or multi-user use, revisit with a change-notification mechanism.

## Alternatives considered

- **Ask the user to refresh** — rejected: invisible work, erodes trust in receipts.
- **Push-based updates (websockets/event bus)** — rejected for now: single-user app, read-after-write suffices; revisit only if the usage model changes.
