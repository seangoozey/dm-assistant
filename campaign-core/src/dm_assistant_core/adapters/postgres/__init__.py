"""PostgreSQL persistence and migration adapter."""

from dm_assistant_core.adapters.postgres.candidate_proposals import (
    PostgresCandidateProposalRepository,
)
from dm_assistant_core.adapters.postgres.change_sets import PostgresChangeSetRepository
from dm_assistant_core.adapters.postgres.database import PostgresDatabase
from dm_assistant_core.adapters.postgres.import_reviews import PostgresImportReviewRepository
from dm_assistant_core.adapters.postgres.imports import PostgresMarkdownImportRepository
from dm_assistant_core.adapters.postgres.retrieval import PostgresRetrievalRepository

__all__ = [
    "PostgresCandidateProposalRepository",
    "PostgresChangeSetRepository",
    "PostgresDatabase",
    "PostgresImportReviewRepository",
    "PostgresMarkdownImportRepository",
    "PostgresRetrievalRepository",
]
