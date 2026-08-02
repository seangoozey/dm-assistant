"""Strict schema for sanitized interaction acceptance fixtures."""

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
TicketId = Annotated[str, StringConstraints(pattern=r"^TKT-[0-9]{4}[A-Z]?$", strict=True)]
CaseId = Annotated[
    str,
    StringConstraints(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", strict=True),
]


class WorkflowKind(StrEnum):
    ASK = "ask"
    BRAINSTORM = "brainstorm"
    LORE_ENTRY = "lore_entry"
    REAL_PLAY = "real_play"
    AUDIO_BRAINSTORM = "audio_brainstorm"
    SESSION_DEBRIEF = "session_debrief"
    ENCOUNTER_CREATION = "encounter_creation"


class EnforcementOwner(StrEnum):
    CORE = "core"
    MODEL_AND_OUTPUT_VALIDATION = "model_and_output_validation"
    CORE_AND_OUTPUT_VALIDATION = "core_and_output_validation"
    CORE_AND_MODEL = "core_and_model"

    @property
    def includes_core(self) -> bool:
        return self in {
            EnforcementOwner.CORE,
            EnforcementOwner.CORE_AND_OUTPUT_VALIDATION,
            EnforcementOwner.CORE_AND_MODEL,
        }


class DeferredEvaluation(StrEnum):
    MODEL_QUALITY = "model_quality"
    OUTPUT_VALIDATION = "output_validation"


class DeterministicAssertion(StrEnum):
    APPROVAL_SCOPE_IS_EXACT = "approval_scope_is_exact"
    CREATIVE_ARTIFACT_CANNOT_MUTATE_LORE = "creative_artifact_cannot_mutate_lore"
    APPROVAL_BINDS_TO_CURRENT_VERSION = "approval_binds_to_current_version"
    PC_DIRECTION_IS_CONDITIONAL = "pc_direction_is_conditional"
    OBSERVED_SUPERSEDES_PREPARED = "observed_supersedes_prepared"
    EXPLICIT_REVISION_SUPERSEDES_CANDIDATE = "explicit_revision_supersedes_candidate"
    DIRECT_LORE_PRESERVES_PARENT = "direct_lore_preserves_parent"


class SourcePolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source_snapshot: NonEmptyText
    source_files: list[NonEmptyText] = Field(min_length=1)
    sanitization: NonEmptyText


class InteractionCase(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: CaseId
    active_workflow: WorkflowKind
    prior_evidence: list[NonEmptyText] = Field(min_length=1)
    input: NonEmptyText
    expected_output: list[NonEmptyText] = Field(min_length=1)
    forbidden_output: list[NonEmptyText] = Field(min_length=1)
    mutation_effect: NonEmptyText
    enforcement: EnforcementOwner
    deterministic_assertions: list[DeterministicAssertion]
    deferred_evaluations: list[DeferredEvaluation]
    implementation_dependency: TicketId | None = None

    @model_validator(mode="after")
    def validate_enforcement_plan(self) -> "InteractionCase":
        if self.enforcement.includes_core and not (
            self.deterministic_assertions or self.implementation_dependency
        ):
            raise ValueError(
                "Core-owned case requires a deterministic assertion or implementation_dependency"
            )
        if not self.enforcement.includes_core and self.deterministic_assertions:
            raise ValueError("non-Core case cannot declare deterministic Core assertions")
        if len(set(self.deterministic_assertions)) != len(self.deterministic_assertions):
            raise ValueError("deterministic_assertions contains duplicates")
        if len(set(self.deferred_evaluations)) != len(self.deferred_evaluations):
            raise ValueError("deferred_evaluations contains duplicates")

        required_deferred: set[DeferredEvaluation] = set()
        if self.enforcement in {
            EnforcementOwner.MODEL_AND_OUTPUT_VALIDATION,
            EnforcementOwner.CORE_AND_MODEL,
        }:
            required_deferred.add(DeferredEvaluation.MODEL_QUALITY)
        if self.enforcement in {
            EnforcementOwner.MODEL_AND_OUTPUT_VALIDATION,
            EnforcementOwner.CORE_AND_OUTPUT_VALIDATION,
        }:
            required_deferred.add(DeferredEvaluation.OUTPUT_VALIDATION)
        missing = required_deferred - set(self.deferred_evaluations)
        if missing:
            values = ", ".join(sorted(item.value for item in missing))
            raise ValueError(f"enforcement requires deferred evaluations: {values}")
        unexpected = set(self.deferred_evaluations) - required_deferred
        if unexpected:
            values = ", ".join(sorted(item.value for item in unexpected))
            raise ValueError(f"enforcement does not declare deferred evaluations: {values}")
        return self


class InteractionFixture(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[2]
    purpose: NonEmptyText
    source_policy: SourcePolicy
    cases: list[InteractionCase] = Field(min_length=1)

    @model_validator(mode="after")
    def require_unique_case_ids(self) -> "InteractionFixture":
        seen: set[str] = set()
        duplicates: set[str] = set()
        for case in self.cases:
            if case.id in seen:
                duplicates.add(case.id)
            seen.add(case.id)
        if duplicates:
            values = ", ".join(sorted(duplicates))
            raise ValueError(f"duplicate interaction case IDs: {values}")
        return self
