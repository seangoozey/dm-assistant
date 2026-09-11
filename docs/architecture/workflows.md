# Deterministic Workflows

## Brainstorm

1. Capture every thought outside canon.
2. Preserve verbatim input and provenance.
3. Resolve `@` mentions to stable canonical identities without changing the thought text.
4. Search canonical names, aliases, tags, and claim content without leaving the workspace.
5. Open reference dossiers and pin relevant entities or exact suggested evidence as durable session context. Evidence pins preserve the assertion and citation, including claims with no entity. Pinning does not change canon.
6. Refresh relevant facts, contradictions, and consequences after each submission.
7. Track tentative, revised, rejected, and unresolved ideas.
8. Synthesize an exact proposal across affected entities and claims.
9. Review and edit the versioned proposal.
10. Apply only the explicitly approved version and scope.
11. Write an atomic receipt and close or retain the brainstorm.

## Direct lore update inside a brainstorm

Brainstorm search cards show a bounded excerpt around the first matching term with query terms highlighted. Clicking the excerpt expands the full assertion; clicking again collapses it. Every content result offers an exact evidence pin, including results without an owning entity. Campaign Core revalidates the search result and supplies its assertion and citation. Suggested and searched evidence pins appear in pinned context and survive refresh.

An active Brainstorm may temporarily invoke a Direct Lore Update targeting one record. Completing that operation returns to the brainstorm and does not approve its remaining proposal.

## Lore Entry

1. Preserve the input.
2. Extract assertions and affected records.
3. Retrieve relevant evidence.
4. Apply unambiguous, non-conflicting lore with a receipt.
5. Stop for identity, timing, contradiction, or retcon ambiguity.

## Real Play

1. Preserve manicured near-verbatim notes.
2. Extract observed events and persistent consequences.
3. Apply unambiguous observations automatically.
4. Resolve conflicts with preparation in favor of play.
5. Stop on possible historical retcons.
6. Mark disrupted plans for later review without inventing reactions.
7. Issue a receipt and refresh retrieval.

## Audio Brainstorm

1. Preserve original audio and metadata.
2. Produce raw timestamped and corrected transcripts.
3. Identify self-posed questions, candidate claims, revisions, withdrawals, conclusions, and unresolved items.
4. Link earlier candidates to later superseding conclusions.
5. Present the final synthesis without requiring full transcript review.
6. Promote only approved conclusions; keep reasoning history outside normal canon retrieval.

## Promotion safety

For imported evidence, the DM first selects exact candidate and revision IDs, supplies target entity decisions, reviews the server-rendered immutable version and hash, and approves explicit proposal item IDs. Reject and defer never enter this promotion path. Editing produces a new version and invalidates an older unapplied approval. Deterministic checks stop on identity ambiguity, conflicts or possible retcons, invalid future time, PC-agency violations, or evidence that is not eligible for promotion.

The final mutation is one Campaign Core transaction:

```text
apply_change_set(change_set_id, reviewed_version, approval_id, reviewed_content_hash)
```

The transaction validates approval, applies all changes or none, writes the receipt, and is safe to retry.
