"""Typed domain values independent of HTTP and persistence adapters."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ClaimState(StrEnum):
    OBSERVED = "observed"
    ESTABLISHED = "established"
    INTENDED = "intended"
    PREPARED = "prepared"
    POSSIBLE = "possible"
    PROPOSED = "proposed"
    DISPUTED = "disputed"
    SUPERSEDED = "superseded"
    REJECTED = "rejected"


class Visibility(StrEnum):
    DM_ONLY = "dm_only"
    PARTY = "party"
    CHARACTER = "character"


class PlanningClaim(BaseModel):
    """A bounded planning representation for campaign-shaping material."""

    model_config = ConfigDict(frozen=True)

    assertion_text: str = Field(min_length=1)
    state: ClaimState
    visibility: Visibility
    conditional: bool
    predicts_pc_action: bool

    @model_validator(mode="after")
    def enforce_pc_agency(self) -> "PlanningClaim":
        if self.predicts_pc_action:
            raise ValueError("campaign planning cannot predict a future PC action")
        if self.state not in {ClaimState.PREPARED, ClaimState.POSSIBLE}:
            raise ValueError("PC campaign direction must remain prepared or possible")
        if self.visibility is not Visibility.DM_ONLY:
            raise ValueError("PC campaign direction must remain DM-only")
        if not self.conditional:
            raise ValueError("PC campaign direction must use conditional planning semantics")
        return self

