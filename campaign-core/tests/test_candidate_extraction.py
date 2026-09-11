"""Offline unit tests for the candidate extraction enrichment service (TKT-0035).

Uses an in-memory repository and a fixture extraction harness so there is no network
access and no database dependency.
"""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import pytest

from dm_assistant_core.application.candidate_extraction import (
    CandidateExtractionError,
    CandidateExtractionService,
    ExtractedCandidateDimension,
)
from dm_assistant_core.domain.extraction import DocumentContext, ExtractionHarness, segment_source
from dm_assistant_core.domain.models import ClaimState
from dm_assistant_core.importer.models import CandidateAuthority

SOURCE = (
    "The archivist Coreferra tends the eastern ledger. "
    "She founded the order in 505CE to combat corruption."
)


class FixtureClient:
    """Fake provider returning canned JSON."""

    def __init__(self, response_text: str) -> None:
        self._response_text = response_text
        self.system = ""
        self.user = ""

    def quick_complete(self, *, system: str, user: str, **_kwargs: Any) -> str:
        self.system = system
        self.user = user
        return self._response_text


class InMemoryRepository:
    """In-memory candidate extraction repository for testing."""

    def __init__(
        self, assertion_text: str | None, document_context: DocumentContext | None = None
    ) -> None:
        self._assertion_text = assertion_text
        self._document_context = document_context
        self.stored: dict[UUID, tuple[ExtractedCandidateDimension, ...]] = {}
        self.failures = []

    def load_candidate_context(self, candidate_id):
        if self._assertion_text is None:
            return None
        return (self._assertion_text, self._document_context)

    def replace_extractions(
        self,
        candidate_id: UUID,
        extractions: tuple[ExtractedCandidateDimension, ...],
        extractor_version: str,
        segments,
        coverage,
        model_profile_key=None,
        model_slug=None,
        prompt_version=None,
    ) -> tuple[ExtractedCandidateDimension, ...]:
        self.stored[candidate_id] = extractions
        return extractions

    def record_failure(
        self,
        candidate_id,
        failures,
        extractor_version,
        model_profile_key,
        model_slug,
        prompt_version,
    ):
        self.failures.append(
            (
                candidate_id,
                failures,
                extractor_version,
                model_profile_key,
                model_slug,
                prompt_version,
            )
        )


def _extraction_json(assertions: list[dict[str, Any]], source_text: str = SOURCE) -> str:
    segments = segment_source(source_text)
    prepared = []
    for assertion in assertions:
        item = dict(assertion)
        excerpt = " ".join(str(item.pop("_test_excerpt")).split())
        matching = [
            segment.segment_id
            for segment in segments
            if excerpt in " ".join(segment.text.split())
            or " ".join(segment.text.split()) in excerpt
        ]
        item["source_segment_ids"] = matching or [segments[0].segment_id]
        prepared.append(item)
    return json.dumps({"assertions": prepared})


def _assertion(
    *,
    subject: str = "Coreferra",
    predicate: str = "tends",
    obj: str = "the eastern ledger",
    assertion_text: str = "Coreferra tends the eastern ledger.",
    excerpt: str = "The archivist Coreferra tends the eastern ledger.",
    state: str = "established",
    authority: str = "explicit_lore",
) -> dict[str, Any]:
    return {
        "subject": subject,
        "predicate": predicate,
        "object": obj,
        "assertion_text": assertion_text,
        "_test_excerpt": excerpt,
    }


class TestSuccessfulExtraction:
    def test_extracts_and_stores_dimensions(self) -> None:
        client = FixtureClient(_extraction_json([_assertion()]))
        repo = InMemoryRepository(SOURCE)
        service = CandidateExtractionService(repo, ExtractionHarness(client))

        candidate_id = uuid4()
        result = service.extract(candidate_id)

        assert result.candidate_id == candidate_id
        assert len(result.extracted) == 1
        dim = result.extracted[0]
        assert dim.subject == "Coreferra"
        assert dim.state is ClaimState.ESTABLISHED
        assert dim.authority is CandidateAuthority.EXPLICIT_LORE
        assert dim.confidence == Decimal("1")
        assert dim.extractor_version == "extraction/8"
        assert result.error is None

    def test_multiple_assertions_stored(self) -> None:
        assertions = [
            _assertion(),
            _assertion(
                predicate="founded",
                obj="the order",
                assertion_text="She founded the order in 505CE.",
                excerpt="She founded the order in 505CE to combat corruption.",
            ),
        ]
        client = FixtureClient(_extraction_json(assertions))
        repo = InMemoryRepository(SOURCE)
        service = CandidateExtractionService(repo, ExtractionHarness(client))

        result = service.extract(uuid4())

        assert len(result.extracted) == 2

    def test_empty_extraction_stores_nothing(self) -> None:
        client = FixtureClient(_extraction_json([]))
        repo = InMemoryRepository(SOURCE)
        service = CandidateExtractionService(repo, ExtractionHarness(client))

        result = service.extract(uuid4())

        assert result.extracted == ()
        assert result.error is None

    @pytest.mark.parametrize(
        ("source_path", "heading", "record_type", "subject", "excerpt"),
        [
            (
                "pcs/sanitized-hero.md",
                "Sanitized Hero",
                "pc",
                "Sanitized Hero",
                "- **Player:** Example Player",
            ),
            (
                "npcs/sanitized-warden.md",
                "Sanitized Warden",
                "npc",
                "Sanitized Warden",
                "- **Role:** archive warden",
            ),
            (
                "locations/sanitized-vault.md",
                "Sanitized Vault",
                "location",
                "Sanitized Vault",
                "- **Region:** eastern marches",
            ),
        ],
    )
    def test_document_context_frames_pc_npc_and_location_extractions(
        self, source_path: str, heading: str, record_type: str, subject: str, excerpt: str
    ) -> None:
        context = DocumentContext(
            source_path=source_path,
            heading=heading,
            frontmatter={"type": record_type, "canon_status": "established"},
        )
        client = FixtureClient(
            _extraction_json(
                [
                    _assertion(
                        subject=subject,
                        predicate="has metadata",
                        obj=excerpt,
                        assertion_text=f"{subject} has recorded metadata.",
                        excerpt=excerpt,
                        authority="explicit_lore",
                    )
                ],
                excerpt,
            )
        )
        service = CandidateExtractionService(
            InMemoryRepository(excerpt, context), ExtractionHarness(client)
        )
        result = service.extract(uuid4())

        assert result.extracted[0].subject == subject
        assert result.extracted[0].authority is CandidateAuthority.EXPLICIT_LORE
        assert f"Source path: {source_path}" in client.user
        assert f"Document heading: {heading}" in client.user
        assert f'"type": "{record_type}"' in client.user
        assert "proper name from context" in client.system


class TestExtractionFailure:
    def test_contract_violation_returns_error_result(self) -> None:
        client = FixtureClient("not valid json")
        repo = InMemoryRepository(SOURCE)
        service = CandidateExtractionService(repo, ExtractionHarness(client))

        result = service.extract(uuid4())

        assert result.extracted == ()
        assert result.error is not None
        assert "not valid JSON" in result.error
        assert len(repo.failures) == 1
        assert len(repo.failures[0][1]) == 2

    def test_missing_candidate_raises(self) -> None:
        client = FixtureClient(_extraction_json([]))
        repo = InMemoryRepository(None)
        service = CandidateExtractionService(repo, ExtractionHarness(client))

        with pytest.raises(CandidateExtractionError, match="does not exist"):
            service.extract(uuid4())

    def test_provider_excerpt_is_not_part_of_the_wire_contract(self) -> None:
        client = FixtureClient(
            _extraction_json([_assertion(excerpt="This text is not in the source at all.")])
        )
        repo = InMemoryRepository(SOURCE)
        service = CandidateExtractionService(repo, ExtractionHarness(client))

        result = service.extract(uuid4())

        assert len(result.extracted) == 1
        assert result.extracted[0].supporting_excerpt == (
            "The archivist Coreferra tends the eastern ledger."
        )

    def test_evidence_is_copied_from_section_not_document_context(self) -> None:
        context = DocumentContext(
            source_path="locations/sanitized-vault.md",
            heading="Sanitized Vault",
            frontmatter={"type": "location", "secret": "context-only statement"},
        )
        client = FixtureClient(
            _extraction_json(
                [_assertion(subject="Sanitized Vault", excerpt="context-only statement")],
                "The section contains different evidence.",
            )
        )
        service = CandidateExtractionService(
            InMemoryRepository("The section contains different evidence.", context),
            ExtractionHarness(client),
        )

        result = service.extract(uuid4())

        assert len(result.extracted) == 1
        assert result.extracted[0].supporting_excerpt == (
            "The section contains different evidence."
        )


class TestDimensionMapping:
    def test_provider_cannot_override_candidate_authority(self) -> None:
        for extraction_auth in (
            "real_play",
            "explicit_lore",
            "npc_intention",
            "preparation",
            "brainstorm",
        ):
            client = FixtureClient(_extraction_json([_assertion(authority=extraction_auth)]))
            repo = InMemoryRepository(SOURCE)
            service = CandidateExtractionService(repo, ExtractionHarness(client))
            result = service.extract(uuid4())
            assert result.extracted[0].authority is CandidateAuthority.EXPLICIT_LORE

    def test_replaced_extractions_clear_prior(self) -> None:
        # First extraction stores one dimension.
        client = FixtureClient(_extraction_json([_assertion()]))
        repo = InMemoryRepository(SOURCE)
        service = CandidateExtractionService(repo, ExtractionHarness(client))
        candidate_id = uuid4()
        result1 = service.extract(candidate_id)
        assert len(result1.extracted) == 1

        # Second extraction with empty result replaces (clears) prior.
        client2 = FixtureClient(_extraction_json([]))
        service2 = CandidateExtractionService(repo, ExtractionHarness(client2))
        result2 = service2.extract(candidate_id)
        assert result2.extracted == ()
