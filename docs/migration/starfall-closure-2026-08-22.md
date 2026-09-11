# Starfall Live Migration Closure

Closed: 2026-08-22T21:02:51.971318Z  
Migration key: `starfall-live-markdown-v0.1`  
Report ID: `0de641c3-1d8c-4b99-8efd-e142b6d609fc`  
Report hash: `d5413957f63f3f91f83c53e335750cda8ab415d5189348bc4b69b5ad5597eb52`

## Result

The admitted Starfall Markdown migration is formally closed. The executable Campaign Core audit reported no nonterminal or deferred candidates, no open source reviews, and no canonical claims without source evidence.

| Measure | Count |
|---|---:|
| Source documents | 143 |
| Source revisions | 153 |
| Applied candidates | 435 |
| Rejected candidates | 64 |
| Current canonical claims | 448 |
| Total canonical claims including superseded history | 454 |
| Audited source-review dispositions | 67 |
| Superseded historical source reviews | 464 |

## Final reconciliation

- 63 historical importer warnings were acknowledged. Their missing-frontmatter or unresolved-link conditions remain in audit history; closure does not claim the source files were changed.
- Two quarantine reviews were resolved as `content_consumed`. The archive files remain quarantined, while their relevant real-play content was manually reviewed during the session-note audit.
- The `sessions/prep` and `templates` warnings were resolved as `excluded_by_scope`, matching the owner-confirmed import policy.
- The deferred mixed `gm/campaign-bible.md` candidate was reconciled. Its coarse Romulus claim was superseded by 13 independently dimensioned claims retaining the original evidence, and the obsolete candidate was rejected to prevent duplicate promotion.

## Reproduction

Run the aggregate check inside the Campaign Core container:

```powershell
docker exec dm-assistant-campaign-core-1 python -m dm_assistant_core.migration_closure
```

Adding `--record` creates the immutable closure report only when every blocker is zero. Re-recording the same migration key succeeds only if the report hash is unchanged.
