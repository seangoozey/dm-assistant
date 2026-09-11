"""Adapter contract for independent read-back of a sealed index generation."""

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from dm_assistant_core.domain.retrieval import RetrievalRecord
from dm_assistant_core.domain.retrieval_paths import CurrentLink


@dataclass(frozen=True)
class ProjectionArtifact:
    generation: UUID
    scope_id: str
    records: tuple[RetrievalRecord, ...]
    links: tuple[CurrentLink, ...]


class ProjectionArtifactReader(Protocol):
    def read_generation(self, generation: UUID, scope_id: str) -> ProjectionArtifact:
        """Read the complete sealed stored generation, not the upload buffer.

        Implementations must fail on partial enumeration, cap overruns or missing
        artifacts. A generation is immutable after verification. Extra generated
        associations must be separately namespaced, never hidden in this manifest.
        """
        ...
