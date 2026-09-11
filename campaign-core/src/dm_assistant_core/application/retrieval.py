"""Application service for grounded campaign retrieval."""

from dataclasses import dataclass
from typing import Protocol

from dm_assistant_core.domain import (
    RetrievalPolicy,
    RetrievalQuery,
    RetrievalRecord,
    RetrievalResult,
)
from dm_assistant_core.domain.derived_retrieval import IndexSuggestion, evaluate_suggestions
from dm_assistant_core.domain.retrieval import RequesterVisibility
from dm_assistant_core.domain.retrieval_paths import (
    CurrentLink,
    PathSuggestion,
    authorized_targets,
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


class CurrentRecordRepository(Protocol):
    def current_records(
        self, query: RetrievalQuery, record_ids: tuple[str, ...],
    ) -> tuple[RetrievalRecord, ...]: ...


class DerivedRetrievalService:
    """Internal direct-ID suggestion reader; not exposed as a public answer endpoint."""

    def __init__(self, repository: CurrentRecordRepository) -> None:
        self._repository = repository

    def query(
        self, query: RetrievalQuery, suggestions: tuple[IndexSuggestion, ...],
    ) -> RetrievalResult:
        if len(suggestions) > 100:
            raise ValueError("at most 100 direct suggestions allowed")
        ids = tuple(dict.fromkeys(s.record_id for s in suggestions))
        records = self._repository.current_records(query, ids) if ids else ()
        return evaluate_suggestions(query, suggestions, records)


@dataclass(frozen=True)
class ActiveProjection:
    """Core-owned generation selection, not index metadata or client input."""

    scope_id: str
    generation: str
    visibility: RequesterVisibility


class ProjectionRegistry(Protocol):
    def active(self, visibility: RequesterVisibility) -> ActiveProjection | None: ...


class CurrentPathRepository(Protocol):
    def current_paths(
        self, query: RetrievalQuery, record_ids: tuple[str, ...],
    ) -> tuple[tuple[RetrievalRecord, ...], tuple[CurrentLink, ...]]: ...


class PathRetrievalService:
    """Internal path-to-context pipeline; no public route or answer synthesis.

    Caller authenticates requester visibility and supplies explicitly resolved
    seeds. The registry chooses an active visibility-isolated generation. Index
    metadata can match that choice, but cannot choose a scope or activate one.
    """

    def __init__(self, repository: CurrentPathRepository, registry: ProjectionRegistry) -> None:
        self._repository = repository
        self._registry = registry

    def query(
        self, query: RetrievalQuery, paths: tuple[PathSuggestion, ...],
        *, seed_ids: frozenset[str],
    ) -> RetrievalResult:
        if len(paths) > 100 or len(seed_ids) > 100:
            raise ValueError("at most 100 paths and seeds allowed")
        empty = evaluate_suggestions(query, (), ())
        if not paths or not seed_ids:
            return empty
        active = self._registry.active(query.requester_visibility)
        if (active is None or active.visibility != query.requester_visibility
                or not active.scope_id or not active.generation):
            return empty
        scoped = tuple(p for p in paths if p.scope_id == active.scope_id
                       and p.generation == active.generation
                       and p.nodes[0].record_id in seed_ids)
        ids = tuple(dict.fromkeys(n.record_id for p in scoped for n in p.nodes))
        if len(ids) > 100:
            raise ValueError("at most 100 unique path records allowed")
        if not ids:
            return empty
        records, links = self._repository.current_paths(query, ids)
        # A replaced/disabled generation cannot authorize an in-flight result.
        if self._registry.active(query.requester_visibility) != active:
            return empty
        targets = authorized_targets(query, scoped, records, links,
                                     scope_id=active.scope_id, generation=active.generation,
                                     seed_ids=seed_ids)
        return evaluate_suggestions(query, targets, records)
