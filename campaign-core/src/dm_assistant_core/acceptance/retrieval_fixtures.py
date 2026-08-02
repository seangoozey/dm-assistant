"""Strict schema for the grounded retrieval acceptance corpus."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from dm_assistant_core.domain import (
    AnswerMode,
    RequesterVisibility,
    RetrievalAuthority,
    RetrievalRecordKind,
)
from dm_assistant_core.domain.models import ClaimState

NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
CaseId = Annotated[str, StringConstraints(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")]


class RetrievalCategory(str):
    """Marker type validated against the accepted category set."""


RETRIEVAL_CATEGORIES = {
    "direct_fact",
    "alias",
    "relationship",
    "chronology",
    "contradiction",
    "noncanon_leakage",
    "unknown",
    "character_visibility",
    "recent_update",
}


class FixtureRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    record_id: NonEmptyText
    kind: RetrievalRecordKind
    assertion: NonEmptyText
    state: ClaimState
    authority: RetrievalAuthority
    visibility: NonEmptyText
    source_id: NonEmptyText
    citation: NonEmptyText
    recorded_at: str | None = None
    effective_from: str | None = None
    expected_at: str | None = None
    observed_at: str | None = None


class ExpectedRetrieval(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    answer_mode: AnswerMode
    facts: list[NonEmptyText] = Field(min_length=1)
    required_citations: list[NonEmptyText]
    forbidden_claims: list[NonEmptyText] = Field(min_length=1)


class RetrievalCase(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: CaseId
    category: NonEmptyText
    fixture_origin: Literal["sanitized_starfall_derived", "synthetic_behavioral"]
    question: NonEmptyText
    requester_visibility: RequesterVisibility
    authoritative_inputs: list[FixtureRecord]
    context_inputs: list[FixtureRecord]
    expected: ExpectedRetrieval

    @model_validator(mode="after")
    def validate_category_and_records(self) -> "RetrievalCase":
        if self.category not in RETRIEVAL_CATEGORIES:
            raise ValueError(f"unknown retrieval category: {self.category}")
        record_ids = [
            record.record_id for record in (*self.authoritative_inputs, *self.context_inputs)
        ]
        if len(record_ids) != len(set(record_ids)):
            raise ValueError("retrieval case contains duplicate record IDs")
        return self


class RetrievalSourcePolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    allowed_origins: list[Literal["sanitized_starfall_derived", "synthetic_behavioral"]]
    live_source_accessed: Literal[False]
    sanitization: NonEmptyText


class RetrievalFixture(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1]
    purpose: NonEmptyText
    source_policy: RetrievalSourcePolicy
    answer_modes: list[AnswerMode]
    cases: list[RetrievalCase] = Field(min_length=30, max_length=50)

    @model_validator(mode="after")
    def validate_unique_cases_and_modes(self) -> "RetrievalFixture":
        ids = [case.id for case in self.cases]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate retrieval case IDs")
        if set(self.answer_modes) != set(AnswerMode):
            raise ValueError("answer_modes must list every supported mode")
        return self
