"""Deterministic workflow nesting decisions."""

from pydantic import BaseModel, ConfigDict, Field


class DirectLoreDecision(BaseModel):
    model_config = ConfigDict(frozen=True)

    parent_workflow_id: str = Field(min_length=1)
    target_id: str = Field(min_length=1)
    canonical_mutation_allowed: bool
    return_to_parent: bool
    sibling_proposal_items_authorized: bool


def scope_direct_lore_update(parent_workflow_id: str, target_id: str) -> DirectLoreDecision:
    """Authorize one nested lore target without approving its parent brainstorm."""

    return DirectLoreDecision(
        parent_workflow_id=parent_workflow_id,
        target_id=target_id,
        canonical_mutation_allowed=True,
        return_to_parent=True,
        sibling_proposal_items_authorized=False,
    )
