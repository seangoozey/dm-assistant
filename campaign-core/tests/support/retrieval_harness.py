"""Typed loader and isolated-store runner for grounded retrieval cases."""

from pathlib import Path

import yaml

from dm_assistant_core.acceptance import RetrievalCase, RetrievalFixture
from dm_assistant_core.adapters.memory import InMemoryRetrievalRepository
from dm_assistant_core.application import RetrievalService
from dm_assistant_core.domain import RetrievalQuery, RetrievalRecord, RetrievalResult

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_PATH = REPOSITORY_ROOT / "tests" / "fixtures" / "retrieval_cases.yaml"


def load_retrieval_fixture(path: Path = FIXTURE_PATH) -> RetrievalFixture:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return RetrievalFixture.model_validate(raw)


def records_for_case(case: RetrievalCase) -> tuple[RetrievalRecord, ...]:
    authoritative = tuple(
        RetrievalRecord(**record.model_dump(), accepted=True)
        for record in case.authoritative_inputs
    )
    context = tuple(
        RetrievalRecord(**record.model_dump(), accepted=False)
        for record in case.context_inputs
    )
    return (*authoritative, *context)


def execute_case(case: RetrievalCase, *, reverse_records: bool = False) -> RetrievalResult:
    records = records_for_case(case)
    if reverse_records:
        records = tuple(reversed(records))
    service = RetrievalService(InMemoryRetrievalRepository(records))
    return service.query(
        RetrievalQuery(
            question=case.question,
            requester_visibility=case.requester_visibility,
        )
    )
