"""Versioned experimental ranking contract; does not assign evidence authority."""
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from dm_assistant_core.domain.models import ClaimState

VERSION = "relevance-v1"


class Purpose(StrEnum):
    FACTUAL = "factual"
    BRAINSTORM = "brainstorm"
    ENCOUNTER = "encounter"
    COMPARISON = "comparison"


class Signals(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    semantic: float = Field(ge=0, le=1, allow_inf_nan=False)
    path_strength: float | None = Field(default=None, ge=0, le=1, allow_inf_nan=False)
    evidence_support: float = Field(ge=0, le=1, allow_inf_nan=False)
    independent_sources: int = Field(default=1, ge=0)
    feedback: float | None = Field(default=None, ge=0, le=1, allow_inf_nan=False)


class PathEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    source_id: str
    state: ClaimState
    visible: bool
    current: bool
    time_eligible: bool
    identity_resolved: bool


def score(signals: Signals, evidence: tuple[PathEvidence, ...], purpose: Purpose) -> dict:
    """Rank only; support/retcon decisions remain with existing Core policy.

    Eligibility booleans must come from Core revalidation, never the provider.
    No scores or path details are returned for an ineligible intermediate.
    """
    if not evidence or any(not (e.visible and e.current and e.time_eligible
                               and e.identity_resolved) for e in evidence):
        return {"version": VERSION, "eligible": False}
    if any(e.state in {ClaimState.SUPERSEDED, ClaimState.REJECTED} for e in evidence):
        return {"version": VERSION, "eligible": False}
    preferred = {
        Purpose.FACTUAL: {ClaimState.OBSERVED, ClaimState.ESTABLISHED},
        Purpose.BRAINSTORM: {ClaimState.OBSERVED, ClaimState.ESTABLISHED,
                            ClaimState.INTENDED, ClaimState.PREPARED, ClaimState.POSSIBLE},
        Purpose.ENCOUNTER: {ClaimState.OBSERVED, ClaimState.ESTABLISHED,
                           ClaimState.INTENDED, ClaimState.PREPARED},
        Purpose.COMPARISON: set(ClaimState),
    }[purpose]
    # Minimum retains the least suitable passage; never average mixed states
    # into apparent factual support. A low suitability is still labeled context.
    truth = min(1.0 if e.state in preferred else 0.25 for e in evidence)
    components = {
        "semantic": signals.semantic,
        "path_strength": signals.path_strength if signals.path_strength is not None else 0.5,
        "evidence_support": signals.evidence_support,
        "source_support": min(signals.independent_sources, 3) / 3,
        "truth_suitability": truth,
        "feedback": signals.feedback if signals.feedback is not None else 0.5,
    }
    weights = {"semantic": .5, "path_strength": .15, "evidence_support": .2,
               "source_support": .05, "truth_suitability": .08, "feedback": .02}
    return {"version": VERSION, "eligible": True, "components": components,
            "missing": [key for key in ("path_strength", "feedback")
                        if getattr(signals, key) is None],
            "score": sum(components[k] * v for k, v in weights.items()),
            "states": [e.state.value for e in evidence],
            "authority": "not_assigned_by_ranking"}
