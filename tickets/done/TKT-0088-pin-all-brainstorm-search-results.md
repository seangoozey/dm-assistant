---
id: TKT-0088
title: Pin all Brainstorm search evidence
status: done
priority: P0
depends_on: [TKT-0087]
---

Every content search result must offer an exact evidence pin, including results without an entity. Campaign Core revalidates the search and retrieves the assertion and citation itself. Existing suggested pins and entity dossier pins remain supported.

Acceptance: entity-free search results can be pinned and unpinned, unknown result IDs are rejected, and tests and deployment pass. No migration required.

Validation: repository gate passed (317 backend tests, 69 React tests, strict types, Windmill build, 38 retrieval cases). Service coverage verifies search-only evidence pins and rejection of unknown IDs; React coverage verifies an entity-free result submits the search query and evidence ID. Local test-stack deployment completed successfully.
