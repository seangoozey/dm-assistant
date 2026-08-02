"""Typed expectations for privacy-safe Markdown importer fixtures."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from dm_assistant_core.importer.models import (
    ImportClassification,
    ImportOutcome,
    ImportWarning,
)

NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class ExpectedImportFile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: NonEmptyText
    classification: ImportClassification
    outcome: ImportOutcome
    candidate_states: list[NonEmptyText]
    claim_candidates: int = Field(ge=0)
    entity_candidates: int = Field(ge=0)
    warnings: list[ImportWarning]

    @model_validator(mode="after")
    def counts_match_states(self) -> "ExpectedImportFile":
        if len(self.candidate_states) != self.claim_candidates:
            raise ValueError("candidate_states count must match claim_candidates")
        return self


class ImportFixtureManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1]
    privacy: NonEmptyText
    expected_files: list[ExpectedImportFile] = Field(min_length=1)
    excluded_paths: list[NonEmptyText] = Field(min_length=1)

    @model_validator(mode="after")
    def paths_are_unique(self) -> "ImportFixtureManifest":
        paths = [item.path for item in self.expected_files] + self.excluded_paths
        if len(paths) != len(set(paths)):
            raise ValueError("import fixture paths must be unique")
        return self


class SyntheticScanFile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: NonEmptyText
    stable_id: NonEmptyText
    content: NonEmptyText


class SyntheticScan(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: NonEmptyText
    files: list[SyntheticScanFile]
    expected_outcomes: list[ImportOutcome] = Field(min_length=1)
    expected_source_documents: int = Field(ge=0)
    expected_source_revisions: int = Field(ge=0)
    expected_candidates: int = Field(ge=0)
    expected_canonical_truth: int = Field(ge=0)


class ReconciliationFixture(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1]
    synthetic: Literal[True]
    description: NonEmptyText
    confirmation_threshold: int = Field(ge=1)
    scans: list[SyntheticScan] = Field(min_length=1)
