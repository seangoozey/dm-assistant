---
id: TKT-0079
title: Audit and formally close the live Starfall migration
status: done
priority: P0
milestone: trustworthy-migration
depends_on: [TKT-0075, TKT-0076, TKT-0077, TKT-0078]
created: 2026-08-22
updated: 2026-08-22
---

# TKT-0079: Audit and Formally Close the Live Starfall Migration

## Outcome

Every admitted live source and candidate has an explicit, auditable outcome, remaining source warnings are intentionally acknowledged or left actionable, and a reproducible closure report proves the migration state.

## Acceptance criteria

- [ ] No candidate remains pending, proposed, approved, or ambiguously deferred.
- [ ] The deferred mixed campaign-bible candidate is reconciled against correctly dimensioned canonical claims.
- [ ] Historical missing-frontmatter and unresolved-link warnings are dispositioned without pretending their source condition never existed.
- [ ] The two quarantined session archives have an explicit retained-source/content-consumed decision.
- [ ] Excluded `sessions/prep` and `templates` material is not treated as missing campaign content.
- [ ] A reproducible closure report records source, candidate, review, canonical, and provenance coverage totals.
- [ ] Automated tests and the PostgreSQL integration suite pass.

## Constraints

- Live Markdown remains read-only.
- Acknowledging an importer warning does not repair or erase the original source condition.
- Closure must fail if any admitted active candidate lacks a terminal review status.
- Closure must fail if any applied canonical claim lacks source evidence.

## Closure receipt

- Report ID: `0de641c3-1d8c-4b99-8efd-e142b6d609fc`
- Report hash: `d5413957f63f3f91f83c53e335750cda8ab415d5189348bc4b69b5ad5597eb52`
- Result: closed with zero blockers
