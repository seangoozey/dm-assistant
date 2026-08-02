"""Deterministic enforcement of the PC-agency invariant."""

from dm_assistant_core.domain.models import ClaimState, PlanningClaim, Visibility


def represent_pc_campaign_direction(source_text: str) -> PlanningClaim:
    """Represent DM campaign direction without predicting player behavior."""

    normalized = source_text.strip()
    if not normalized:
        raise ValueError("campaign direction cannot be empty")

    return PlanningClaim(
        assertion_text=normalized,
        state=ClaimState.PREPARED,
        visibility=Visibility.DM_ONLY,
        conditional=True,
        predicts_pc_action=False,
    )

