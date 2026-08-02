"""Boundaries for explicitly requested creative artifacts."""

from pydantic import BaseModel, ConfigDict, Field


class CreativeArtifactDecision(BaseModel):
    model_config = ConfigDict(frozen=True)

    artifact_kind: str
    source_text: str = Field(min_length=1)
    canonical_mutation_allowed: bool


def create_bounded_read_aloud(source_text: str) -> CreativeArtifactDecision:
    normalized = source_text.strip()
    if not normalized:
        raise ValueError("read-aloud source cannot be empty")
    return CreativeArtifactDecision(
        artifact_kind="read_aloud",
        source_text=normalized,
        canonical_mutation_allowed=False,
    )

