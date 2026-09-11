# Evidence comparison contract

TKT-0091 introduces `domain/evidence_comparison.py`, policy version
`evidence-comparison-v1`. Retrieval responses expose its structured conflict contract;
promotion remains unchanged. The production PostgreSQL adapter does not yet supply
validated coordinates, so live verified comparison discovery is not enabled.

The comparison accepts two current, visible, accepted factual records and optional
Core-validated comparison coordinates. Each coordinate binds an exact record ID,
subject, controlled property, value and temporal/event scope. Exclusivity must be
established by the property's rules: different founders, participants or owners are
not inherently contradictory. Missing scope never implies the same instant.

Different exclusive values in the same scope produce conflict; an observed versus
established pair produces possible-retcon review. Without those prerequisites the
result is unknown. Identical values mean only that the supplied coordinate matches,
not that entire prose assertions can be merged. Comparison is read-only and supplies
no application permission. Unknown cannot clear the Lore Entry gate.

Coordinates must not be taken directly from client or model suggestions. Adapter
integration must bind them to reviewed structure and controlled semantics. Existing
optional SPO alone does not establish exclusivity or simultaneity. Unstructured
prose needs a separate comparison-review route; no forced extraction is introduced.

Hidden or ineligible evidence yields an opaque unknown result without IDs, counts
or a hidden-specific reason. Retrieval now bases the entire response on visible
records; PostgreSQL filters visibility before its 100-result limit. Adding a hidden
record must produce the same response as omitting it, including modes and issue IDs.
The legacy claim-count conflict heuristic still needs replacement.

Two original visibility fixture modes were corrected: public duty plus a hidden
reason now behaves like public duty alone (`answer`), while another character's
private knowledge behaves like absent evidence (`insufficient_evidence`). All 38
cases and their source assertions remain. The historical connected baseline is
retained; its two security gold modes are corrected without changing other targets.
The still-imperfect lexical relevance/conflict policy can fail those security answer
targets independently of privacy; identical hidden/absent output is tested separately.

## Future repair surface

`RetrievalResult.conflicts` contains an issue ID, classification, verification level,
policy version, reason, complete evidence snapshots (record/source IDs, assertions,
citations, authority, state and available timestamps), and comparison subject,
property and scope when known. Verified incompatible values are `factual_conflict`;
observed/background contradictions are `possible_retcon`. Both require review.
The ID hashes the sorted evidence snapshot and comparison coordinates, is independent
of query/order, and changes when the compared content changes.

Legacy count-based alerts are exposed only as `suspected_conflict` / `unverified`.
Their old answer modes remain for compatibility until policy migration is completed.
They must not be displayed as proven contradictions. Results always state partial
comparison coverage: no issues does not establish consistency or permit auto-application.
Verified issue output is capped at 50 with an explicit truncation flag.

These are read-time issues, not persisted repair tasks. A future surface must reread
the records and full provenance, recheck visibility/supersession and compare the issue
snapshot before offering an exact reviewed replacement/supersession. A hash is not an
approval token. Source IDs/citations are lookup references, not a substitute for full
revision/span bindings. Neither issue creation nor dismissal may alter canon.

Run the contract tests with:

```powershell
# From campaign-core
.\.venv\Scripts\python.exe -m pytest tests/test_evidence_comparison.py
```
