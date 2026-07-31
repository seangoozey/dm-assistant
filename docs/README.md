# Documentation Index

The repository keeps current development guidance in Markdown so decisions can be reviewed and merged through Git. The Word document is retained as the narrative baseline from the initial planning process.

## Authority order

When documents disagree, use this order:

1. Tested application behavior and database migrations
2. Accepted architecture decision records in [decisions](decisions/README.md)
3. Current product and architecture specifications
4. Completed tickets and their recorded validation evidence
5. The maintained [development plan](plan.md)
6. The [Word planning baseline](reference/DM%20Assistant%20App%20Planning%20Document.docx)

An older document can still reveal intent. Do not silently overwrite a newer decision with it; raise the conflict in the active ticket.

## Current specifications

- [Product vision](product/vision.md)
- [Domain invariants](product/invariants.md)
- [Truth states and authority decision table](product/truth-state-authority.md)
- [Architecture overview](architecture/overview.md)
- [Domain model](architecture/domain-model.md)
- [Campaign Core schema](architecture/campaign-core-schema.md)
- [Workflows](architecture/workflows.md)
- [Deployment](architecture/deployment.md)
- [Current-system migration](migration/current-system.md)
- [Incremental Markdown importer](migration/markdown-importer.md)
- [Acceptance strategy](testing/acceptance-strategy.md)
- [Development plan](plan.md)

## Historical baseline

[DM Assistant App Planning Document](reference/DM%20Assistant%20App%20Planning%20Document.docx) preserves the broader product discussion, workflow observations, and tentative platform reasoning that preceded these Markdown specifications. Keep it in Git, but update the focused Markdown documents and tickets for normal development changes.
