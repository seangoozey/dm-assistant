# Codex Working Agreement

These instructions apply to the entire repository.

## Mission

Build a trustworthy DM campaign librarian and continuity system. The system organizes Sean's material; it does not become an autonomous co-author.

## Required reading before work

Read, in order:

1. `README.md`
2. `docs/README.md`
3. `docs/product/vision.md`
4. `docs/product/invariants.md`
5. `docs/architecture/overview.md`
6. `docs/architecture/domain-model.md`
7. `docs/plan.md`
8. The selected ticket and every document it references

The Word planning baseline at `docs/reference/DM Assistant App Planning Document.docx` contains the earlier planning conversation synthesized into a readable artifact. Consult it when current Markdown leaves intent unclear. It is reference material, not authority over newer ADRs, specifications, tickets, or tested behavior.

If a task changes a durable architectural decision, read `docs/decisions/README.md` and add or amend an ADR.

## Ticket workflow

- Do not start substantial work without a ticket.
- Tickets are Markdown files under `tickets/`.
- Move a ticket between `backlog`, `ready`, `in-progress`, `blocked`, and `done` as its state changes.
- Update the ticket frontmatter and `tickets/index.md` in the same change.
- Only one ticket should normally be in progress for a single developer.
- Satisfy every acceptance criterion and record validation evidence before moving a ticket to `done`.
- If scope expands materially, create a follow-up ticket instead of silently enlarging the current one.

## Non-negotiable domain rules

- Real-play observations have the highest authority about what occurred.
- Suspected retcons require comparison and explicit resolution.
- Brainstorm content is non-canon until an exact, reviewed proposal is promoted.
- A request to inspect or edit one proposal item never approves the rest.
- Short confirmations bind only to one visible, versioned pending action.
- PC plans are plot pressure, opportunities, or desired arcs—not predictions or prescriptions of player behavior.
- Future dates are expectations until the event actually occurs.
- Failed NPC or faction plans are marked for review; the system does not invent reactions.
- Creative generation is opt-in and normally limited to requested encounter read-alouds.
- Provider transcripts, Cognee, embeddings, Foundry exports, and generated Markdown are derived artifacts, not sources of truth.
- Missing source files never authorize automatic canonical deletion.
- Canonical mutations go through Campaign Core in one auditable, idempotent transaction.

## Source safety

- Treat the previously audited `E:\studio\starfall` snapshot, the live `\\HOMESERVER\projects\projects\starfall` collection, and later legacy snapshots as read-only.
- Treat `\\HOMESERVER\openclaw\.openclaw\dnd-workspace` as historical-system evidence, not current campaign truth. Any nested Starfall copy is a snapshot unless independently verified.
- Never clean up or rewrite the legacy collection as part of importer development.
- Preserve original text, path, hashes, and provenance.
- Templates must not import as live campaign records.
- Unclassified or unrelated content enters quarantine rather than normal retrieval.

## Architecture boundaries

- Campaign Core owns domain rules and canonical mutations.
- Campaign PostgreSQL owns campaign truth, proposals, approvals, and durable receipts.
- Windmill supplies infrastructure for asynchronous, scheduled, retryable, or progress-reporting work.
- Windmill workers must not receive credentials that can directly mutate canonical tables.
- The React UI calls Campaign Core for campaign operations and uses a small adapter for Windmill jobs.
- Cognee and vector indexes must be rebuildable from authoritative records.

## Engineering expectations

- Prefer small, explicit modules and typed boundaries.
- Use Python type hints and Pydantic models at API and persistence boundaries.
- Make writes idempotent and transactionally safe.
- Preserve user changes and unrelated worktree modifications.
- Add tests with every behavior change.
- Use real Starfall-derived fixtures when privacy permits; sanitize before committing if the repository may leave the private environment.
- Do not add a dependency or service without documenting why it is needed.
- Pin production container and dependency versions.
- Never commit secrets, tokens, private audio, raw campaign backups, or production database data.

## Definition of done

A ticket is done only when:

- acceptance criteria are met;
- relevant tests pass;
- documentation reflects the resulting behavior;
- migrations and rollback concerns are addressed;
- no known domain invariant is bypassed;
- the ticket contains validation evidence and follow-up work.
