"""PostgreSQL persistence and migration adapter."""

from dm_assistant_core.adapters.postgres.artifact_exports import (
    PostgresArtifactExportRepository,
)
from dm_assistant_core.adapters.postgres.brainstorms import PostgresBrainstormRepository
from dm_assistant_core.adapters.postgres.candidate_extraction import (
    PostgresCandidateExtractionRepository,
)
from dm_assistant_core.adapters.postgres.candidate_proposals import (
    PostgresCandidateProposalRepository,
)
from dm_assistant_core.adapters.postgres.change_sets import PostgresChangeSetRepository
from dm_assistant_core.adapters.postgres.claim_reconciliation import (
    PostgresClaimReconciliationRepository,
)
from dm_assistant_core.adapters.postgres.database import PostgresDatabase
from dm_assistant_core.adapters.postgres.entity_lookup import PostgresEntityLookupRepository
from dm_assistant_core.adapters.postgres.entity_metadata import (
    PostgresEntityMetadataProposalRepository,
)
from dm_assistant_core.adapters.postgres.import_reviews import PostgresImportReviewRepository
from dm_assistant_core.adapters.postgres.imports import PostgresMarkdownImportRepository
from dm_assistant_core.adapters.postgres.library_entries import PostgresLibraryEntryRepository
from dm_assistant_core.adapters.postgres.pc_profiles import PostgresPCProfileRepository
from dm_assistant_core.adapters.postgres.plans import PostgresPlanRepository
from dm_assistant_core.adapters.postgres.retrieval import PostgresRetrievalRepository
from dm_assistant_core.adapters.postgres.session_runs import PostgresSessionRunRepository
from dm_assistant_core.adapters.postgres.taxonomy import PostgresTaxonomyRepository

__all__ = [
    "PostgresArtifactExportRepository",
    "PostgresBrainstormRepository",
    "PostgresCandidateExtractionRepository",
    "PostgresCandidateProposalRepository",
    "PostgresChangeSetRepository",
    "PostgresClaimReconciliationRepository",
    "PostgresDatabase",
    "PostgresEntityLookupRepository",
    "PostgresEntityMetadataProposalRepository",
    "PostgresImportReviewRepository",
    "PostgresLibraryEntryRepository",
    "PostgresMarkdownImportRepository",
    "PostgresPCProfileRepository",
    "PostgresPlanRepository",
    "PostgresRetrievalRepository",
    "PostgresSessionRunRepository",
    "PostgresTaxonomyRepository",
]
