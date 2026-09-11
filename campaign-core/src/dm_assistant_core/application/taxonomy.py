"""Read-only controlled taxonomy metadata."""

from typing import Protocol

from pydantic import BaseModel, ConfigDict

from dm_assistant_core.domain import EntityKindGuidance, PlanKindGuidance


class TaxonomySnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    entity_kinds: tuple[EntityKindGuidance, ...]
    tags: tuple[str, ...]
    plan_kinds: tuple[PlanKindGuidance, ...] = ()


class TaxonomyRepository(Protocol):
    def snapshot(self) -> TaxonomySnapshot: ...


class TaxonomyService:
    def __init__(self, repository: TaxonomyRepository) -> None:
        self._repository = repository

    def snapshot(self) -> TaxonomySnapshot:
        return self._repository.snapshot()
