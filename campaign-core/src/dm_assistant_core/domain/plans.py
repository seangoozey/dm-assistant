"""First-class plan vocabulary and knowledge-boundary rules."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class PlanKind(StrEnum):
    CAMPAIGN_DIRECTION = "campaign_direction"
    IN_WORLD_PLAN = "in_world_plan"
    PLAYER_PLAN = "player_plan"


class PlanLifecycle(StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    ABANDONED = "abandoned"
    SUPERSEDED = "superseded"


class PlanKnowledgeBoundary(StrEnum):
    DM_DIRECTION = "dm_direction"
    DM_AUTHORED_ACTOR_INTENTION = "dm_authored_actor_intention"
    PLAYER_COMMUNICATED_NONBINDING = "player_communicated_nonbinding"


class PlanKindGuidance(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: PlanKind
    label: str
    description: str


PLAN_KIND_GUIDANCE = (
    PlanKindGuidance(
        kind=PlanKind.CAMPAIGN_DIRECTION,
        label="Campaign direction",
        description="DM-only guidance for developing pressures, opportunities, or themes.",
    ),
    PlanKindGuidance(
        kind=PlanKind.IN_WORLD_PLAN,
        label="In-world plan",
        description="A DM-authored intention owned by an NPC or faction.",
    ),
    PlanKindGuidance(
        kind=PlanKind.PLAYER_PLAN,
        label="Player plan",
        description="A time-bound, revocable statement communicated by a player.",
    ),
)


def knowledge_boundary_for(kind: PlanKind) -> PlanKnowledgeBoundary:
    return {
        PlanKind.CAMPAIGN_DIRECTION: PlanKnowledgeBoundary.DM_DIRECTION,
        PlanKind.IN_WORLD_PLAN: PlanKnowledgeBoundary.DM_AUTHORED_ACTOR_INTENTION,
        PlanKind.PLAYER_PLAN: PlanKnowledgeBoundary.PLAYER_COMMUNICATED_NONBINDING,
    }[kind]
