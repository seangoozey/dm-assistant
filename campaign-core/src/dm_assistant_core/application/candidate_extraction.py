"""Candidate extraction enrichment service (TKT-0035).

Wires the extraction harness (TKT-0034) into the candidate review pipeline. A candidate
already carries deterministic section text and path-derived classification. This service
runs AI extraction against the candidate's assertion text and persists the extracted,
grounded assertions as a non-canonical enrichment so the human reviewer sees proposed
structured dimensions alongside the original evidence.

Extraction output is never canonical. Promotion remains the existing human-controlled
proposal path. Ungrounded, low-confidence, or failed extraction leaves the candidate with
its deterministic dimensions and optionally opens a review item.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from dm_assistant_core.domain.extraction import (
    DocumentContext,
    ExtractedAssertion,
    ExtractionAttemptFailure,
    ExtractionError,
    ExtractionHarness,
    SegmentCoverage,
    SourceSegment,
    SubjectResolution,
)
from dm_assistant_core.domain.models import ClaimState, Visibility
from dm_assistant_core.importer.models import CandidateAuthority


class ExtractedCandidateDimension(BaseModel):
    """One AI-extracted dimension row, surfaced for human review."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    extraction_id: UUID
    candidate_id: UUID
    subject: str = Field(min_length=1)
    subject_resolution: SubjectResolution = SubjectResolution.NAMED_IDENTITY
    predicate: str | None = Field(default=None, min_length=1)
    object_entity: str | None = None
    assertion_text: str = Field(min_length=1)
    supporting_excerpt: str = Field(min_length=1)
    state: ClaimState
    authority: CandidateAuthority
    visibility: Visibility
    confidence: Decimal = Field(ge=0, le=1)
    extractor_version: str = Field(min_length=1)
    created_at: datetime
    source_segment_ids: tuple[str, ...]


class CandidateExtractionResult(BaseModel):
    """The outcome of running extraction against one candidate."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_id: UUID
    extracted: tuple[ExtractedCandidateDimension, ...]
    extractor_version: str = Field(min_length=1)
    error: str | None = None
    segments: tuple[SourceSegment, ...] = ()
    coverage: tuple[SegmentCoverage, ...] = ()


class CandidateExtractionError(ValueError):
    """A candidate extraction request failed."""


class CandidateExtractionRepository(Protocol):
    """Read candidate evidence and persist extracted dimensions."""

    def load_candidate_context(
        self, candidate_id: UUID
    ) -> tuple[str, DocumentContext | None] | None: ...

    def replace_extractions(
        self,
        candidate_id: UUID,
        extractions: tuple[ExtractedCandidateDimension, ...],
        extractor_version: str,
        segments: tuple[SourceSegment, ...],
        coverage: tuple[SegmentCoverage, ...],
        model_profile_key: str | None = None,
        model_slug: str | None = None,
        prompt_version: str | None = None,
    ) -> tuple[ExtractedCandidateDimension, ...]: ...

    def record_failure(
        self,
        candidate_id: UUID,
        failures: tuple[ExtractionAttemptFailure, ...],
        extractor_version: str,
        model_profile_key: str | None,
        model_slug: str | None,
        prompt_version: str | None,
    ) -> None: ...


class CandidateExtractionService:
    """Run extraction against a candidate's assertion text and persist the results."""

    def __init__(
        self,
        repository: CandidateExtractionRepository,
        harness: ExtractionHarness,
        *,
        model_profile_key: str | None = None,
        model_slug: str | None = None,
        prompt_version: str | None = None,
    ) -> None:
        self._repository = repository
        self._harness = harness
        self._model_profile_key = model_profile_key
        self._model_slug = model_slug
        self._prompt_version = prompt_version

    def extract(self, candidate_id: UUID) -> CandidateExtractionResult:
        context_data = self._repository.load_candidate_context(candidate_id)
        if context_data is None:
            raise CandidateExtractionError("candidate does not exist")
        assertion_text, document_context = context_data
        try:
            result = self._harness.extract(assertion_text, document_context=document_context)
        except ExtractionError as error:
            self._repository.record_failure(
                candidate_id,
                error.failures,
                self._harness.extractor_version,
                self._model_profile_key,
                self._model_slug,
                self._prompt_version,
            )
            return CandidateExtractionResult(
                candidate_id=candidate_id,
                extracted=(),
                extractor_version=self._harness.extractor_version,
                error=str(error),
            )
        dimensions = tuple(
            _to_dimension(candidate_id, assertion, result.extractor_version)
            for assertion in result.assertions
        )
        stored = self._repository.replace_extractions(
            candidate_id,
            dimensions,
            result.extractor_version,
            result.segments,
            result.coverage,
            self._model_profile_key,
            self._model_slug,
            self._prompt_version,
        )
        return CandidateExtractionResult(
            candidate_id=candidate_id,
            extracted=stored,
            extractor_version=result.extractor_version,
            segments=result.segments,
            coverage=result.coverage,
        )


def _to_dimension(
    candidate_id: UUID,
    assertion: ExtractedAssertion,
    extractor_version: str,
) -> ExtractedCandidateDimension:
    from dm_assistant_core.domain.extraction import ExtractionAuthority

    authority_map = {
        ExtractionAuthority.REAL_PLAY: CandidateAuthority.REAL_PLAY,
        ExtractionAuthority.EXPLICIT_LORE: CandidateAuthority.EXPLICIT_LORE,
        ExtractionAuthority.NPC_INTENTION: CandidateAuthority.NPC_INTENTION,
        ExtractionAuthority.PREPARATION: CandidateAuthority.PREPARATION,
        ExtractionAuthority.BRAINSTORM: CandidateAuthority.BRAINSTORM,
        ExtractionAuthority.UNCLASSIFIED: CandidateAuthority.UNCLASSIFIED,
    }
    return ExtractedCandidateDimension(
        extraction_id=uuid4(),
        candidate_id=candidate_id,
        subject=assertion.subject,
        subject_resolution=assertion.subject_resolution,
        predicate=assertion.predicate,
        object_entity=assertion.object,
        assertion_text=assertion.assertion_text,
        supporting_excerpt=assertion.supporting_excerpt,
        state=assertion.state,
        authority=authority_map[assertion.authority],
        visibility=assertion.visibility,
        confidence=assertion.confidence,
        extractor_version=extractor_version,
        created_at=datetime.now(UTC),
        source_segment_ids=assertion.source_segment_ids,
    )
