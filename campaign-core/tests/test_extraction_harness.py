"""Offline unit tests for the extraction harness (TKT-0034).

Every test uses a fixture provider client so there is no network access. The fixtures
are sanitized synthetic extractions, not real provider output.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from dm_assistant_core.domain.extraction import (
    EXTRACTION_SYSTEM_PROMPT,
    DocumentContext,
    ExtractionAuthority,
    ExtractionError,
    ExtractionHarness,
    SubjectResolution,
    segment_source,
)
from dm_assistant_core.domain.models import ClaimState, Visibility

SOURCE = (
    "The archivist Coreferra tends the eastern ledger. "
    "She founded the order in 505CE to combat corruption."
)


class FixtureClient:
    """A fake provider client returning a canned JSON response."""

    def __init__(self, response_text: str) -> None:
        self._response_text = response_text
        self.response_schema: dict[str, Any] | None = None

    def quick_complete(self, *, system: str, user: str, **_kwargs: Any) -> str:
        self.response_schema = _kwargs.get("response_schema")
        return self._response_text


class FailingClient:
    def quick_complete(self, *, system: str, user: str, **_kwargs: Any) -> str:
        raise RuntimeError("synthetic provider failure")


class SequenceClient:
    def __init__(self, responses: list[str]) -> None:
        self._responses = iter(responses)
        self.calls = 0
        self.users: list[str] = []

    def quick_complete(self, *, system: str, user: str, **_kwargs: Any) -> str:
        self.calls += 1
        self.users.append(user)
        return next(self._responses)


def _assertion(
    *,
    subject: str = "Coreferra",
    predicate: str = "tends",
    obj: str | None = "the eastern ledger",
    assertion_text: str = "Coreferra tends the eastern ledger.",
    excerpt: str = "The archivist Coreferra tends the eastern ledger.",
    state: str = "established",
    authority: str = "explicit_lore",
    visibility: str = "dm_only",
    confidence: str = "0.9",
) -> dict[str, Any]:
    return {
        "subject": subject,
        "predicate": predicate,
        "object": obj,
        "assertion_text": assertion_text,
        "_test_excerpt": excerpt,
    }


def _response(assertions: list[dict[str, Any]]) -> str:
    segments = segment_source(SOURCE)
    prepared: list[dict[str, Any]] = []
    for assertion in assertions:
        item = dict(assertion)
        excerpt = " ".join(str(item.pop("_test_excerpt", "")).split())
        matching = [
            segment.segment_id
            for segment in segments
            if excerpt in " ".join(segment.text.split())
            or " ".join(segment.text.split()) in excerpt
        ]
        item["source_segment_ids"] = matching or [segments[0].segment_id]
        prepared.append(item)
    return json.dumps({"assertions": prepared})


class TestCleanExtraction:
    def test_supplies_strict_pydantic_wire_schema(self) -> None:
        client = FixtureClient(_response([]))

        ExtractionHarness(client).extract(SOURCE)

        assert client.response_schema is not None
        schema = client.response_schema
        assert schema["additionalProperties"] is False
        assert set(schema["required"]) == {"assertions"}
        assertion_schema = schema["$defs"]["DiscoveredFact"]
        assert assertion_schema["additionalProperties"] is False
        assert set(assertion_schema["required"]) == set(assertion_schema["properties"]) - {
            "predicate"
        }
        assert "supporting_excerpt" not in assertion_schema["properties"]
        assert "coverage" not in schema["properties"]

    def test_one_grounded_assertion_returns_result(self) -> None:
        client = FixtureClient(_response([_assertion()]))
        harness = ExtractionHarness(client)
        result = harness.extract(SOURCE)

        assert not result.is_empty
        assert len(result.assertions) == 1
        assertion = result.assertions[0]
        assert assertion.subject == "Coreferra"
        assert assertion.state.value == "established"
        assert assertion.authority.value == "explicit_lore"
        assert result.extractor_version == "extraction/8"

    def test_retries_one_malformed_structured_response(self) -> None:
        client = SequenceClient(['{"assertions" invalid', _response([_assertion()])])

        result = ExtractionHarness(client).extract(SOURCE)

        assert client.calls == 2
        assert len(result.assertions) == 1
        assert "CORRECTIVE RETRY REQUIRED" in client.users[1]
        assert "not valid JSON" in client.users[1]

    def test_surfaces_final_error_after_bounded_attempts(self) -> None:
        client = SequenceClient(["not json", "still not json"])

        with pytest.raises(ExtractionError, match="not valid JSON") as caught:
            ExtractionHarness(client).extract(SOURCE)

        assert client.calls == 2
        assert len(caught.value.failures) == 2
        assert caught.value.failures[0].raw_response == "not json"
        assert caught.value.failures[1].attempt_number == 2

    def test_attempt_count_must_be_positive(self) -> None:
        with pytest.raises(ValueError, match="max_attempts"):
            ExtractionHarness(FixtureClient(_response([])), max_attempts=0)

    def test_multiple_grounded_assertions(self) -> None:
        assertions = [
            _assertion(),
            _assertion(
                subject="Coreferra",
                predicate="founded",
                obj="the order",
                assertion_text="Coreferra founded the order in 505CE.",
                excerpt="She founded the order in 505CE to combat corruption.",
                state="observed",
                authority="real_play",
            ),
        ]
        client = FixtureClient(_response(assertions))
        result = ExtractionHarness(client).extract(SOURCE)

        assert len(result.assertions) == 2

    def test_empty_assertions_is_valid(self) -> None:
        client = FixtureClient(_response([]))
        result = ExtractionHarness(client).extract(SOURCE)

        assert result.is_empty

    def test_complete_assertion_does_not_require_predicate_index(self) -> None:
        assertion = _assertion()
        assertion.pop("predicate")

        result = ExtractionHarness(FixtureClient(_response([assertion]))).extract(SOURCE)

        assert result.assertions[0].assertion_text == "Coreferra tends the eastern ledger."
        assert result.assertions[0].predicate is None

    def test_whitespace_in_source_and_excerpt_normalized_for_grounding(self) -> None:
        # The excerpt has different whitespace than the source but same words.
        client = FixtureClient(
            _response(
                [
                    _assertion(
                        excerpt="The   archivist   Coreferra   tends   the   eastern   ledger."
                    )
                ]
            )
        )
        result = ExtractionHarness(client).extract(SOURCE)

        assert len(result.assertions) == 1

    def test_markdown_fenced_json_extracted(self) -> None:
        # Models frequently wrap JSON in markdown code fences.
        fenced = "Here are the assertions:\n\n```json\n" + _response([_assertion()]) + "\n```\n"
        client = FixtureClient(fenced)
        result = ExtractionHarness(client).extract(SOURCE)

        assert len(result.assertions) == 1

    def test_json_with_prose_prefix_extracted(self) -> None:
        prose_wrapped = "I found the following assertions in the text.\n\n" + _response(
            [_assertion()]
        )
        client = FixtureClient(prose_wrapped)
        result = ExtractionHarness(client).extract(SOURCE)

        assert len(result.assertions) == 1


class TestContractViolation:
    def test_provider_exception_becomes_extraction_error(self) -> None:
        with pytest.raises(ExtractionError, match="provider request failed"):
            ExtractionHarness(FailingClient()).extract(SOURCE)

    def test_uncited_segment_coverage_is_derived_as_context(self) -> None:
        result = ExtractionHarness(FixtureClient(_response([_assertion()]))).extract(SOURCE)

        assert result.coverage[1].disposition == "context_only"
        assert result.coverage[1].claim_indexes == ()

    def test_model_claim_index_bookkeeping_is_reconciled_from_evidence(self) -> None:
        payload = json.loads(_response([_assertion()]))
        payload["assertions"][0]["source_segment_ids"] = ["s2"]
        client = FixtureClient(json.dumps(payload))

        result = ExtractionHarness(client).extract(SOURCE)

        assert result.assertions[0].source_segment_ids == ("s2",)
        assert result.coverage[1].claim_indexes == (0,)

    def test_invalid_json_raises_extraction_error(self) -> None:
        client = FixtureClient("not json at all")
        with pytest.raises(ExtractionError, match="not valid JSON"):
            ExtractionHarness(client).extract(SOURCE)

    def test_json_array_not_object_raises(self) -> None:
        client = FixtureClient("[]")
        with pytest.raises(ExtractionError, match="not an object"):
            ExtractionHarness(client).extract(SOURCE)

    def test_provider_does_not_own_state(self) -> None:
        client = FixtureClient(_response([_assertion(state="proposed")]))
        assert ExtractionHarness(client).extract(SOURCE).assertions[0].state.value == "established"

    def test_provider_does_not_own_authority(self) -> None:
        client = FixtureClient(_response([_assertion(authority="invalid")]))
        assertion = ExtractionHarness(client).extract(SOURCE).assertions[0]
        assert assertion.authority.value == "explicit_lore"

    def test_provider_does_not_supply_confidence(self) -> None:
        client = FixtureClient(_response([_assertion(confidence="1.5")]))
        assert ExtractionHarness(client).extract(SOURCE).assertions[0].confidence == 1

    def test_missing_required_field_raises(self) -> None:
        broken = _assertion()
        del broken["subject"]
        client = FixtureClient(_response([broken]))
        with pytest.raises(ExtractionError, match="extraction contract"):
            ExtractionHarness(client).extract(SOURCE)

    def test_unknown_field_rejected(self) -> None:
        assertion = _assertion()
        assertion["junk"] = True
        client = FixtureClient(_response([assertion]))
        with pytest.raises(ExtractionError, match="extraction contract"):
            ExtractionHarness(client).extract(SOURCE)


class TestGrounding:
    def test_adjacent_clause_evidence_preserves_source_punctuation(self) -> None:
        source = "After weeks alone, he collapsed near the eastern crossroads."
        assertion = _assertion(excerpt=source)
        assertion.pop("_test_excerpt")
        assertion["source_segment_ids"] = ["s1", "s2"]
        payload = {"assertions": [assertion]}

        result = ExtractionHarness(FixtureClient(json.dumps(payload))).extract(source)

        assert result.assertions[0].supporting_excerpt == source

    def test_close_paraphrase_is_canonicalized_to_exact_source_segment(self) -> None:
        client = FixtureClient(
            _response(
                [
                    _assertion(
                        excerpt="Coreferra, the archivist, tends the eastern ledger.",
                    )
                ]
            )
        )

        result = ExtractionHarness(client).extract(SOURCE)

        assert result.assertions[0].supporting_excerpt == (
            "The archivist Coreferra tends the eastern ledger."
        )

    def test_relevant_paraphrase_is_replaced_from_segment_reference(self) -> None:
        client = FixtureClient(
            _response([_assertion(excerpt="Coreferra manages the eastern records.")])
        )
        result = ExtractionHarness(client).extract(SOURCE)

        assert result.assertions[0].supporting_excerpt == (
            "The archivist Coreferra tends the eastern ledger."
        )

    def test_exact_evidence_is_derived_instead_of_trusting_excerpt(self) -> None:
        client = FixtureClient(_response([_assertion(excerpt="Hi.")]))
        result = ExtractionHarness(client).extract(SOURCE)
        assert result.assertions[0].supporting_excerpt == (
            "The archivist Coreferra tends the eastern ledger."
        )

    def test_weak_paraphrase_uses_explicit_segment_reference(self) -> None:
        client = FixtureClient(
            _response([_assertion(excerpt="Coreferra manages the eastern records.")])
        )
        result = ExtractionHarness(client).extract(SOURCE)

        assert result.assertions[0].source_segment_ids == ("s1",)

    def test_claim_with_unknown_segment_reference_is_rejected(self) -> None:
        payload = json.loads(
            _response(
                [
                    _assertion(excerpt="This text does not appear in the source whatsoever."),
                ]
            )
        )
        payload["assertions"][0]["source_segment_ids"] = ["s999"]

        with pytest.raises(ExtractionError, match="unknown source segment"):
            ExtractionHarness(FixtureClient(json.dumps(payload))).extract(SOURCE)

    def test_workflow_states_cannot_be_supplied_by_provider(self) -> None:
        for state in ("proposed", "disputed", "superseded", "rejected"):
            client = FixtureClient(_response([_assertion(state=state)]))
            assertion = ExtractionHarness(client).extract(SOURCE).assertions[0]
            assert assertion.state.value == "established"


class TestHarnessProperties:
    def test_prompt_forbids_known_backstory_inferences(self) -> None:
        assert "Do not infer" in EXTRACTION_SYSTEM_PROMPT
        assert "deaths" in EXTRACTION_SYSTEM_PROMPT
        assert "witnessed" in EXTRACTION_SYSTEM_PROMPT

    def test_prompt_preserves_independent_subjects_and_named_qualifiers(self) -> None:
        assert "grammatical or stable named subject" in EXTRACTION_SYSTEM_PROMPT
        for qualifier in (
            "ages",
            "durations",
            "destinations",
            "route markers",
            "titles",
            "leaders",
            "locations",
            "motivations",
        ):
            assert qualifier in EXTRACTION_SYSTEM_PROMPT

    def test_prompt_separates_predicate_from_object(self) -> None:
        assert "one short relation that does not repeat the object" in EXTRACTION_SYSTEM_PROMPT

    def test_dense_backstory_is_split_into_auditable_clauses(self) -> None:
        source = (
            "Ruh found him, brought him to Fleurite, trained him, and became his master. "
            "During the mission at The Ocho, Ruh died and Ruhrogue killed Goodman in revenge."
        )

        segments = segment_source(source)

        assert [segment.text for segment in segments] == [
            "Ruh found him",
            "brought him to Fleurite",
            "trained him",
            "became his master.",
            "During the mission at The Ocho",
            "Ruh died",
            "Ruhrogue killed Goodman in revenge.",
        ]

    def test_entity_context_preserves_independent_subject_and_normalizes_truth_dimensions(
        self,
    ) -> None:
        client = FixtureClient(
            _response(
                [
                    _assertion(
                        subject="Coreferra",
                        state="possible",
                        authority="brainstorm",
                        visibility="party",
                    )
                ]
            )
        )
        context = DocumentContext(
            source_path="pcs/sanitized-hero.md",
            heading="Sanitized Hero",
            focal_subject="Sanitized Hero",
            record_type="pc",
            candidate_state=ClaimState.ESTABLISHED,
            candidate_authority=ExtractionAuthority.EXPLICIT_LORE,
            candidate_visibility=Visibility.DM_ONLY,
        )

        result = ExtractionHarness(client).extract(SOURCE, document_context=context)
        assertion = result.assertions[0]

        assert assertion.subject == "Coreferra"
        assert assertion.subject_resolution is SubjectResolution.NAMED_IDENTITY
        assert assertion.state is ClaimState.ESTABLISHED
        assert assertion.authority is ExtractionAuthority.EXPLICIT_LORE
        assert assertion.visibility is Visibility.DM_ONLY

    def test_pronoun_resolves_to_explicit_focal_subject(self) -> None:
        client = FixtureClient(_response([_assertion(subject="She")]))
        context = DocumentContext(
            source_path="npcs/coreferra.md",
            heading="Coreferra",
            focal_subject="Coreferra",
            record_type="npc",
        )

        assertion = ExtractionHarness(client).extract(
            SOURCE, document_context=context
        ).assertions[0]

        assert assertion.subject == "Coreferra"
        assert assertion.subject_resolution is SubjectResolution.FOCAL_ENTITY

    def test_possessive_subject_stays_an_explicit_non_entity_phrase(self) -> None:
        source = "Ruhrogue's village was destroyed by raiders."
        response = json.dumps({"assertions": [{
            "subject": "Ruhrogue's village",
            "predicate": "was destroyed by",
            "object": "raiders",
            "assertion_text": source,
            "source_segment_ids": ["s1"],
        }]})

        assertion = ExtractionHarness(FixtureClient(response)).extract(source).assertions[0]

        assert assertion.subject_resolution is SubjectResolution.NON_ENTITY

    def test_unsupported_subject_remains_unresolved_instead_of_becoming_an_identity(self) -> None:
        client = FixtureClient(_response([_assertion(subject="Invented Stranger")]))
        context = DocumentContext(
            source_path="npcs/coreferra.md", heading="Coreferra", record_type="npc"
        )

        assertion = ExtractionHarness(client, max_attempts=1).extract(
            SOURCE, document_context=context
        ).assertions[0]

        assert assertion.subject_resolution is SubjectResolution.UNRESOLVED

    def test_named_subject_can_be_grounded_elsewhere_in_the_same_section(self) -> None:
        source = "Ruh found Ruhrogue. He brought him to Fleurite."
        response = json.dumps({"assertions": [{
            "subject": "Ruh",
            "predicate": "brought",
            "object": "Ruhrogue",
            "assertion_text": "Ruh brought Ruhrogue to Fleurite.",
            "source_segment_ids": ["s2"],
        }]})

        assertion = ExtractionHarness(FixtureClient(response)).extract(source).assertions[0]

        assert assertion.subject == "Ruh"
        assert assertion.subject_resolution is SubjectResolution.NAMED_IDENTITY
        assert assertion.supporting_excerpt == "He brought him to Fleurite."

    def test_generic_participant_label_is_non_entity_instead_of_failure(self) -> None:
        source = "They waited beside the road."
        response = json.dumps({"assertions": [{
            "subject": "Two individuals",
            "predicate": "waited beside",
            "object": "the road",
            "assertion_text": "Two individuals waited beside the road.",
            "source_segment_ids": ["s1"],
        }]})

        assertion = ExtractionHarness(FixtureClient(response)).extract(source).assertions[0]

        assert assertion.subject_resolution is SubjectResolution.UNRESOLVED

    def test_focal_possessive_can_expand_a_pronoun_as_non_entity(self) -> None:
        source = "His parents bought him time to escape."
        response = json.dumps({"assertions": [{
            "subject": "Ruhrogue's parents",
            "predicate": "bought time for",
            "object": "Ruhrogue",
            "assertion_text": "Ruhrogue's parents bought him time to escape.",
            "source_segment_ids": ["s1"],
        }]})
        context = DocumentContext(
            source_path="pcs/ruhrogue.md",
            heading="Ruhrogue",
            focal_subject="Ruhrogue",
            record_type="pc",
        )

        assertion = ExtractionHarness(FixtureClient(response)).extract(
            source, document_context=context
        ).assertions[0]

        assert assertion.subject_resolution is SubjectResolution.UNRESOLVED

    def test_extractor_version_customizable(self) -> None:
        harness = ExtractionHarness(FixtureClient(_response([])), extractor_version="extraction/2")
        result = harness.extract(SOURCE)
        assert result.extractor_version == "extraction/2"

    def test_no_canonical_mutation_path(self) -> None:
        """The harness returns a result; it has no entity/claim/relationship dependency."""
        client = FixtureClient(_response([_assertion()]))
        harness = ExtractionHarness(client)
        result = harness.extract(SOURCE)
        # The result is a pure value object with no connection to persistence.
        assert result.assertions[0].subject == "Coreferra"
