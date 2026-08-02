"""Deterministic authority outcomes used before persistence."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from dm_assistant_core.domain.models import ClaimState


class ConflictOutcome(StrEnum):
    SUPERSEDE_PREPARATION = "supersede_preparation"
    POSSIBLE_RETCON_REVIEW = "possible_retcon_review"


class AuthorityDecision(BaseModel):
    model_config = ConfigDict(frozen=True)

    outcome: ConflictOutcome
    incoming_state: ClaimState
    prior_state: ClaimState
    retain_prior: bool
    receipt_required: bool
    review_required: bool


def resolve_observed_conflict(prior_state: ClaimState) -> AuthorityDecision:
    """Resolve observed play against preparation or canonical history."""

    if prior_state is ClaimState.PREPARED:
        return AuthorityDecision(
            outcome=ConflictOutcome.SUPERSEDE_PREPARATION,
            incoming_state=ClaimState.OBSERVED,
            prior_state=prior_state,
            retain_prior=True,
            receipt_required=True,
            review_required=False,
        )
    if prior_state in {ClaimState.ESTABLISHED, ClaimState.OBSERVED}:
        return AuthorityDecision(
            outcome=ConflictOutcome.POSSIBLE_RETCON_REVIEW,
            incoming_state=ClaimState.OBSERVED,
            prior_state=prior_state,
            retain_prior=True,
            receipt_required=False,
            review_required=True,
        )
    raise ValueError(f"unsupported observed conflict with {prior_state.value}")

