from __future__ import annotations

import asyncio
import re
from collections import Counter
from copy import deepcopy
from typing import Any

import httpx
import pytest
import yaml
from pydantic import ValidationError

from dm_assistant_core.acceptance import RetrievalFixture
from dm_assistant_core.adapters.memory import InMemoryRetrievalRepository
from dm_assistant_core.api.app import create_app
from dm_assistant_core.application import RetrievalService
from dm_assistant_core.config import Settings
from dm_assistant_core.domain import AnswerMode, EvidenceRole, RetrievalQuery
from tests.support.retrieval_harness import (
    FIXTURE_PATH,
    execute_case,
    load_retrieval_fixture,
    records_for_case,
)

FIXTURE = load_retrieval_fixture()


def test_all_accepted_retrieval_cases_are_strictly_typed() -> None:
    assert len(FIXTURE.cases) == 38
    assert set(FIXTURE.answer_modes) == set(AnswerMode)
    assert Counter(case.category for case in FIXTURE.cases) == {
        "alias": 3,
        "character_visibility": 4,
        "chronology": 5,
        "contradiction": 4,
        "direct_fact": 5,
        "noncanon_leakage": 6,
        "recent_update": 2,
        "relationship": 4,
        "unknown": 5,
    }


@pytest.mark.parametrize("case", FIXTURE.cases, ids=lambda case: case.id)
def test_case_executes_through_isolated_campaign_core_boundary(case: Any) -> None:
    result = execute_case(case)

    assert result.answer_mode is case.expected.answer_mode
    assert set(result.citations) == set(case.expected.required_citations)
    assert len(result.citations) == len(set(result.citations))

    supported = {
        _normalize(evidence.assertion)
        for evidence in result.evidence
        if evidence.role is EvidenceRole.SUPPORT
    }
    for forbidden in case.expected.forbidden_claims:
        assert _normalize(forbidden) not in supported

    if result.answer_mode in {
        AnswerMode.ANSWER,
        AnswerMode.CONFLICT,
        AnswerMode.POSSIBLE_RETCN,
    }:
        evidence_tokens = _tokens(
            " ".join(
                f"{item.assertion} {item.citation}" for item in result.evidence
            )
        )
        for fact in case.expected.facts:
            assert _tokens(fact) & evidence_tokens, (
                f"expected fact has no structured evidence basis: {fact}"
            )


def test_visibility_filter_never_returns_hidden_record_or_hidden_citation() -> None:
    for case in FIXTURE.cases:
        result = execute_case(case)
        returned_ids = {item.record_id for item in result.evidence}
        returned_citations = set(result.citations)
        requester = case.requester_visibility
        for record in (*case.authoritative_inputs, *case.context_inputs):
            visible = requester.role.value == "dm" or record.visibility == "party" or (
                requester.role.value == "character"
                and record.visibility == f"character:{requester.character_id}"
            )
            if not visible:
                assert record.record_id not in returned_ids
                assert record.citation not in returned_citations


def test_noncanonical_inputs_never_become_supported_truth() -> None:
    for case in FIXTURE.cases:
        context_ids = {record.record_id for record in case.context_inputs}
        result = execute_case(case)
        assert not {
            evidence.record_id
            for evidence in result.evidence
            if evidence.role is EvidenceRole.SUPPORT
        } & context_ids


def test_all_cases_are_order_independent() -> None:
    for case in FIXTURE.cases:
        assert execute_case(case) == execute_case(case, reverse_records=True)


def test_retrieval_api_contract_uses_the_same_boundary() -> None:
    case = next(item for item in FIXTURE.cases if item.id == "direct-jace-rebel-role")
    service = RetrievalService(InMemoryRetrievalRepository(records_for_case(case)))
    settings = Settings(
        database_url="postgresql://campaign:secret@localhost:5432/campaign",
        run_migrations=False,
    )
    app = create_app(settings, retrieval=service)
    query = RetrievalQuery(
        question=case.question,
        requester_visibility=case.requester_visibility,
    )

    async def request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post("/retrieval/query", json=query.model_dump(mode="json"))

    response = asyncio.run(request())

    assert response.status_code == 200
    assert response.json()["answer_mode"] == "answer"
    assert response.json()["citations"] == ["npcs/jace.md#role"]


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda raw: raw["cases"][0].pop("question"), "question"),
        (
            lambda raw: raw["cases"].append(deepcopy(raw["cases"][0])),
            "duplicate retrieval case IDs",
        ),
        (
            lambda raw: raw["cases"][0].update({"category": "invented_category"}),
            "unknown retrieval category",
        ),
        (
            lambda raw: raw["cases"][0]["expected"].update({"facts": []}),
            "at least 1 item",
        ),
    ],
    ids=["missing-question", "duplicate-id", "unknown-category", "empty-facts"],
)
def test_invalid_retrieval_fixture_is_rejected(
    mutate: Any,
    message: str,
) -> None:
    raw = yaml.safe_load(FIXTURE_PATH.read_text(encoding="utf-8"))
    mutate(raw)

    with pytest.raises(ValidationError, match=message):
        RetrievalFixture.model_validate(raw)


def _normalize(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", text.casefold()))


def _tokens(text: str) -> set[str]:
    return {
        token
        for token in _normalize(text).split()
        if len(token) >= 3 and token not in {"the", "and", "records", "record"}
    }
