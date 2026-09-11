# Separate-source and retirement probe

Latest follow-up: replacement and post-retirement search have now run; see below.
Earlier accounting figures in this document describe historical reservations, not bills.

Cognee 1.5.3, Gemini 3.5 Flash Lite and Gemini embedding-001. Synthetic data only;
separate `cross-document` storage, sharing the existing $2 gateway ledger.

## Input and extraction

Two distinct DataItems, not one concatenated passage:

- `dispatch/r1`: The Regent sent envoy Mara to Frostgate to negotiate a ceasefire.
- `geography/r1`: Frostgate is a port on Northreach Island.

Deterministic data IDs and external source/revision metadata survived ingestion.
The two DocumentChunks retain their document IDs and exact original text. Expected
relationships were not passed in. Graph contains 12 nodes and 16 edges including
infrastructure, with three domain relationships: Regent `sent_envoy` Mara, Mara
`travelled_to` Frostgate, Frostgate `located_on` Northreach Island. Frostgate is shared
across both documents rather than duplicated. This provides a structural two-edge
connection, not a measured successful query or canonical inference.

`travelled_to` overstates the source's dispatch wording; the edge text still says
"was sent to". Do not interpret the generated label as evidence of arrival.

The question "Which island was envoy Mara sent to?" did **not** complete. Extraction
used 16 calls (4 chat, 12 embedding); the next query embedding was blocked by the
reservation cap, then Cognee retried locally until the 90-second timeout. No blocked
query attempts reached OpenRouter or acquired further reservations. This exposes
an integration requirement: budget denial should be a terminal operational status,
not a retryable embedding outage.

The probe now checks available reservations before starting and again before its
post-ingestion search, avoiding this known exhaustion retry loop. The gateway's
atomic reservation remains the authoritative cap under concurrency; a production
adapter still needs explicit terminal handling if a concurrent request consumes it.

## Source retirement

After exporting the graph, removed only the verified `geography/r1` DataItem via
`datasets.delete_data(..., mode="soft")`. Target identity and metadata were checked.
Provider calls were disabled for this phase. Original source text remains in the
probe code and local reports; no campaign source or canonical record was deleted.

The graph changed from 12 nodes / 16 edges to 8 nodes / 10 edges. Geography's
document, chunk, summary, Northreach Island entity and location relationship were
removed. The shared Frostgate entity and dispatch document/relationships survived.
No Northreach text remains in the exported graph. Only dispatch remains in the
dataset listing. Ledger count stayed at 27, so this phase made no paid calls.

This verifies targeted graph retirement, **not** the full correction lifecycle:
replacement revision ingestion, vector-query results, shared-description restoration,
visibility changes, concurrent refresh, and historical retrieval remain unverified.

## Accounting and next work

27 total completed calls across experiments. First eight calls have user-confirmed
cost $0.06; 19 subsequent calls hold $1.90 of reservations. Accounted maximum $1.96,
not actual billed cost. No more $0.10 requests fit the $2 cap until billing is
reconciled. Preserve the ledger; do not reset it to resume.

Nine offline guard/retirement tests pass. Next paid stage needs confirmed cumulative
billing, followed by corrected `geography/r2` ingestion and before/after retrieval.
The full 24-case comparison and production evidence/visibility adapter remain open.

## Corrected revision and cost capture (2026-09-07)

The user withdrew the earlier exact $0.06 report and confirmed that all first 27
calls together cost less than $0.06. An appended checkpoint now treats $0.06 as an
upper bound across those 27 calls, preserving the mistaken earlier checkpoint for
audit. It is not presented as exact billing. Completed new calls record `usage.cost`,
rounded upward to microdollars; absent/invalid cost and uncertain failures retain
their $0.10 safety reservations. No additional spending authorization was needed.

Queried the retired graph, added geography/r2 ("Frostgate is a port on Southreach
Island."), then cognified and queried again with the same question and top_k=5.

- Retired context contains dispatch evidence, but no Northreach Island.
- Replaced context contains Southreach in Frostgate's generated description; no
  Northreach. The graph contains the exact geography/r2 document chunk and ID.
- **The returned context does not include the geography source chunk.** Thus the
  changed answer-bearing detail is present only as generated description. This is
  a source-recall failure for our contract, despite correct correction propagation.
  Do not label it a fully grounded cross-document retrieval success.

Ten new calls completed and all supplied usable costs: rounded-up sum $0.000888.
37 calls total; zero outstanding reservations; conservative cumulative accounting
is $0.060888 (old upper bound plus new reported costs), not an exact total bill.
Eleven offline tests and Ruff pass. No live data transferred or canonical changes.

Next: retrieval expansion must bring the supporting source passages alongside any
answer-bearing generated entity/path, and revalidate their revisions/visibility.
Then compare against the full corpus; toy graph success alone is insufficient.

## Bounded evidence expansion follow-up

Added an evaluator-only expansion using `search(... verbose=True)` returned Edge
endpoint IDs, not generated-name matching. For retrieved entities it follows incoming
DocumentChunk `contains` associations, yielding only exact uniquely located source
text whose document ID belongs to an explicit current-source manifest. Results keep
source ID, revision, start/end offsets and an association path; deduplication and a
ten-passage cap prevent unbounded output. Summaries/descriptions are never promoted
to evidence. Unavailable, excluded or superseded document IDs do not supply passages.

The existing graph query was rerun without extraction. Raw top-five context still
omitted geography, but expansion returned dispatch/r1 (offsets 0–65) and geography/r2
(0–41), including the exact Southreach sentence. No Northreach was returned. This
closes the inspected example's missing-source gap without adding expected edges to
the model input. It does not establish that every generated detail is entailed by
the expanded passages: these are retrieval associations, not semantic verification.

Fifteen offline tests and Ruff pass. One new embedding call; 38 calls total, cumulative
conservative accounting $0.060890 with no outstanding reservations. Raw and expanded
outputs are retained in `evidence-expansion-report.json`.

Limitations: this isolated evaluation exports a small whole graph and uses a synthetic
manifest, not Campaign Core's production policy. It does not verify hidden intermediate
paths, concurrent revision changes, arbitrary chunk overlap or full-corpus ranking.
The production adapter must obtain authorized current IDs/text from Core, scope seeds
and paths before traversal, and revalidate at return. Next is the scored corpus and
projection integration, not deploying this toy adapter unchanged.
