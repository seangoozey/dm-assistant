---
id: TKT-0097
title: Review and repair evidence-linked factual conflicts
status: backlog
priority: P1
milestone: shared-campaign-knowledge
depends_on: [TKT-0091, TKT-0094]
created: 2026-09-06
---

# Outcome

Expose factual contradictions and suspected comparisons in a dedicated review surface
without filling normal campaign pages with provenance controls.

## Scope

- Consume the structured retrieval conflict contract; distinguish verified factual
  conflict, possible retcon, and unverified suspicion.
- Show both full assertions, source revision/span evidence, authority and campaign
  time. Explain the same-subject/property/scope comparison where available.
- Add a persistent, deduplicated review queue with auditable lifecycle; read-time
  issue hashes are not currently durable queue records.
- Offer correction, explicit supersession, or a documented not-conflicting resolution
  through existing exact reviewed mutation commands. No silent winning assertion.
- Revalidate current evidence/visibility before preview and application. Stale issues
  must refresh, not apply an old decision to a changed claim.
- Dismissal is a review disposition, not a canonical deletion or truth change.

## Acceptance

An actual contradiction can be opened with both sources and repaired through one
audited receipt; repeated detection does not duplicate an unresolved issue; stale and
hidden evidence cannot be acted upon or leaked. Compatible claims can be marked as
not conflicting without altering their assertions. Partial coverage and truncated
results must never appear as a clean campaign-wide consistency bill.

## References

- [Comparison contract](../../docs/testing/evidence-comparison.md)
- [Shared knowledge design](../../docs/architecture/shared-campaign-knowledge.md)

## Migration and rollback

Any persistent queue requires its own migration. Preserve claims, sources and prior
receipts. Disable the surface without deleting canonical records or review history.
