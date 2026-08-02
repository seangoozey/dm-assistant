"""Application service for grounded campaign retrieval."""

from typing import Protocol

from dm_assistant_core.domain import (
    RetrievalPolicy,
    RetrievalQuery,
    RetrievalRecord,
    RetrievalResult,
)


class RetrievalRepository(Protocol):
    def relevant_records(self, query: RetrievalQuery) -> tuple[RetrievalRecord, ...]: ...


class RetrievalService:
    def __init__(
        self,
        repository: RetrievalRepository,
        policy: RetrievalPolicy | None = None,
    ) -> None:
        self._repository = repository
        self._policy = policy or RetrievalPolicy()

    def query(self, query: RetrievalQuery) -> RetrievalResult:
        return self._policy.evaluate(query, self._repository.relevant_records(query))
