---
id: TKT-0122
title: Record hygiene — real-world dates inside canonical record text
status: done
priority: P2
milestone: shared-campaign-knowledge
depends_on: []
created: 2026-09-15
updated: 2026-09-15
---

# TKT-0122: Record hygiene — real-world dates inside canonical record text

## Context (Sean, 2026-09-15)

Canonical records leak real-world session dates into their prose — e.g. the 12/6/25 note's claim text begins "12/6/25 Coreferra making a plan for 8 giant badgers to tunnel into the dungeon @ 600' per hour." The real-world date is provenance metadata (when the table played), not campaign truth, and it reads as noise in every display surface: entry pages, retrieval evidence, descriptions' gathered claims. Campaign time (effective_from, 505-11-21) is the record's date; "12/6/25" belongs under the hood with the source, not in the assertion.

## Root cause

Imported session notes use real-world date headers (`10/10/23:`, `12/6/25`) as their internal structure; the candidate extraction carried those headers into assertion text verbatim. Every claim promoted from those notes inherits the prefix. With TKT-0118's walk complete, each such claim now carries BOTH a real-world date in its prose and a correct campaign date in its effective_from — the worst of both.

## Scope when taken up

1. **Detection (deterministic)**: current claims whose assertion_text begins with or embeds a real-world date pattern — leading `\d{1,2}/\d{1,2}/\d{2,4}` / `\d{4}-\d{2}-\d{2}` prefixes matching the claim's own evidence-document session_date (so in-world dates like 505-11-05 never match; the guard is the source document's real session_date, which we have).
2. **Repair through the normal door**: each fix is a claim correction (the 0023 replacement path — audited change set, reason "removed real-world date from record text"), stripping the date prefix from assertion_text. Never a bulk UPDATE; batched review UI or one-by-one through the existing correction flow — decide at pickup based on volume.
3. **Forward prevention**: candidate extraction strips leading real-world date tokens from assertion text at promotion review (the review form already lets the DM edit wording — make the default pre-stripped); direct-input capture doesn't have the problem (notes carry dates in metadata, not prose).
4. **Surface note**: synthesized pages and the gathered-claims panel inherit the fix automatically since they render assertion text.

## Acceptance

- Detection list computed (expect ~40–50 claims from the dated sessions); zero false positives against campaign-year dates.
- Repairs receipted; assertion text reads clean ("Coreferra making a plan for 8 giant badgers…").
- New promotions arrive pre-stripped.
- Real-world dates remain fully available under the hood (source document session_date, provenance).

## Out of scope

- Rewriting source documents (immutable evidence — the notes keep their headers); touching effective_from dates (correct since 0118).

## Delivery (2026-09-15, deployed) — same day as ticketing

- **Detection (deterministic, zero false positives by guard)**: date-prefixed current claims cross-checked against their evidence document's session_date (frontmatter, falling back to path date) — 55 session-evidenced claims scanned, **20 flagged, 0 guard mismatches**; campaign dates (505-11-05) structurally cannot match the real-world pattern.
- **All 20 repaired through the audited door**: each fix a claim correction (snapshot_hash-verified, change set + receipt, reason "record hygiene: removed the real-world session date from record text (TKT-0122); the campaign date remains in effective_from"). Live check: the flagship claim now reads "Coreferra making a plan for 8 giant badgers to tunnel into the dungeon @ 600' per hour." — clean prose, campaign date intact in effective_from; zero date-prefixed current claims remain; the 20 superseded originals keep their prefixes under the hood as history.
- **Forward prevention**: `cleanImportedAssertion` (the promotion review's prefill) strips leading real-world date headers — `12/6/25`, `2/14/26 —`, `2025-08-23:` — so new claims arrive clean by default while the source note keeps the original. React test covers strip cases plus pass-through cases (campaign dates mid-sentence, undated text untouched); 111 passed.
- Batch review UI skipped deliberately: with the guard deterministic and 0 mismatches in 20, the direct audited pass was the honest size; if future imports reintroduce the pattern at volume, the review-queue variant can be added then.
