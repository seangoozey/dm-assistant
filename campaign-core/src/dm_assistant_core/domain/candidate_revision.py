"""Preserve withdrawn non-canon candidates when explicitly corrected."""

from pydantic import BaseModel, ConfigDict, Field

from dm_assistant_core.domain.models import ClaimState


class CandidateRevisionDecision(BaseModel):
    model_config = ConfigDict(frozen=True)

    earlier_text: str = Field(min_length=1)
    later_text: str = Field(min_length=1)
    earlier_state: ClaimState
    later_state: ClaimState
    canonical_mutation_allowed: bool


def resolve_explicit_candidate_revision(
    earlier_text: str,
    later_text: str,
    *,
    explicit_correction: bool,
) -> CandidateRevisionDecision:
    if not explicit_correction:
        raise ValueError("recency alone cannot supersede a candidate")
    return CandidateRevisionDecision(
        earlier_text=earlier_text.strip(),
        later_text=later_text.strip(),
        earlier_state=ClaimState.SUPERSEDED,
        later_state=ClaimState.PROPOSED,
        canonical_mutation_allowed=False,
    )

