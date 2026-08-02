"""Pure proposal scope and version rules."""

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ApprovalScope(BaseModel):
    model_config = ConfigDict(frozen=True)

    proposal_id: str = Field(min_length=1)
    version: int = Field(gt=0)
    item_ids: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def require_unique_items(self) -> "ApprovalScope":
        if len(set(self.item_ids)) != len(self.item_ids):
            raise ValueError("approval scope contains duplicate item IDs")
        return self


class StaleApprovalError(ValueError):
    """Approval does not bind to the currently reviewed proposal version."""


def create_approval_scope(
    proposal_id: str,
    reviewed_version: int,
    visible_item_ids: tuple[str, ...],
    selected_item_ids: tuple[str, ...],
) -> ApprovalScope:
    """Bind approval only to selected items from the visible reviewed version."""

    visible = set(visible_item_ids)
    selected = set(selected_item_ids)
    if not selected:
        raise ValueError("approval scope cannot be empty")
    unknown = selected - visible
    if unknown:
        raise ValueError(f"approval includes non-visible items: {sorted(unknown)}")
    return ApprovalScope(
        proposal_id=proposal_id,
        version=reviewed_version,
        item_ids=selected_item_ids,
    )


def validate_current_approval(
    approval: ApprovalScope,
    proposal_id: str,
    current_version: int,
) -> None:
    """Reject approval of another proposal or an edited proposal version."""

    if approval.proposal_id != proposal_id or approval.version != current_version:
        raise StaleApprovalError("approval does not match the current proposal ID and version")

