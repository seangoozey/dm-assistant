# Markdown Importer Fixtures

The importer acceptance corpus is a minimal synthetic Starfall-shaped tree under `tests/fixtures/markdown_import`. It is not copied from the live collection and automated tests never access a configured live or historical Starfall path.

## Files

- `tests/fixtures/markdown_import_manifest.yaml` declares typed expected classification, outcome, candidate states, warnings, and candidate counts for every admitted fixture file. It also names excluded sentinel paths.
- `tests/fixtures/markdown_import/` contains the synthetic source tree.
- `tests/fixtures/markdown_import_reconciliation.yaml` contains an explicitly synthetic new, unchanged, changed, moved, and missing sequence because no historical manifest was retained.

The test-only reference scanner remains at `campaign-core/tests/support/importer_harness.py` as an independent expectation oracle. The production connector is `campaign-core/src/dm_assistant_core/importer`; production code does not import the reference harness. Tests require both implementations to match the typed manifest.

## Safety assertions

The fixture suite verifies that excluded roots and the two derived `gm` paths are pruned before descendant reads, hashing, parsing, source revision creation, quarantine, or candidate creation. Admitted files are read exactly once. Templates and navigation indexes retain no live candidates. Missing input never deletes revisions, candidates, path history, or canonical truth.

Campaign-bible-style notes remain `possible` or `prepared`; PC private notes remain conditional DM-only preparation; promoted brainstorm receipts and applied session deltas cannot apply claims again. Invalid or missing frontmatter creates warnings without guessed durable authority.

## Adding a fixture

1. Write the smallest synthetic file that exposes one behavior. Mark it `fixture: synthetic` when valid frontmatter is appropriate, or identify it as synthetic in its body.
2. Add one typed expectation to `markdown_import_manifest.yaml`.
3. Add or extend a focused assertion in `campaign-core/tests/test_importer_fixtures.py`.
4. Never use raw live prose, private backups, production hashes, or copied operational data.
5. Run the standard deterministic validation command from an activated Campaign Core development environment:

```bash
python tests/validate_repository.py
```

The production importer must pass these fixtures without depending on fixture-only path names or test harness code.

PostgreSQL integration tests additionally run the production batch through the real Campaign Core HTTP and persistence layers. They cover exact retries, concurrent retries, unchanged/changed/moved/missing reconciliation, ambiguous possible moves, tampered-hash rollback, raw-byte retention, and proof that no canonical claim or entity is created.

The import-review integration test reads the sanitized persisted corpus through the public Campaign Core endpoints. It verifies deterministic pagination, run/source/classification filters, DM-only receipt and review access, party visibility filtering, exact excerpt offsets and hashes, distinct quarantine results, and an identical database snapshot before and after all reads.

The candidate-proposal integration suite uses the same sanitized persisted corpus. It verifies exact revision and source-span bindings, item-scoped approvals, cumulative completion without sibling promotion, evidence-backed claims, immutable revision invalidation, reject/defer isolation from canon, and fail-closed planning, future-time, PC-agency, and possible-retcon decisions.
